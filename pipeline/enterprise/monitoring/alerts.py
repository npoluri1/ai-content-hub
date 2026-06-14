import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentItem:
    id: str
    title: str = ""
    content: str = ""
    source: str = ""
    url: str = ""
    published_at: Optional[str] = None
    topics: list[str] = field(default_factory=list)
    sentiment: float = 0.0
    engagement: int = 0


class AlertEngine:
    def __init__(self, sql_store=None, notifiers=None):
        self.sql_store = sql_store
        self.notifiers = notifiers or []
        self._conn = sqlite3.connect(":memory:")
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                keywords TEXT NOT NULL,
                sources TEXT,
                topics TEXT,
                min_relevance REAL DEFAULT 0.0,
                channels TEXT,
                user TEXT,
                enabled INTEGER DEFAULT 1,
                suppressed_until TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS alert_logs (
                id TEXT PRIMARY KEY,
                alert_id TEXT NOT NULL,
                content_id TEXT NOT NULL,
                matched_at TEXT,
                notified INTEGER DEFAULT 0,
                FOREIGN KEY (alert_id) REFERENCES alerts(id)
            )
        """)
        self._conn.commit()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _row_to_alert(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "keywords": json.loads(row[2]),
            "sources": json.loads(row[3]) if row[3] else [],
            "topics": json.loads(row[4]) if row[4] else [],
            "min_relevance": row[5],
            "channels": json.loads(row[6]) if row[6] else [],
            "user": row[7],
            "enabled": bool(row[8]),
            "suppressed_until": row[9],
            "created_at": row[10],
            "updated_at": row[11],
        }

    def create_alert(self, name, keywords, sources=None, topics=None, min_relevance=0.0, channels=None, user=None):
        alert_id = str(uuid.uuid4())
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO alerts (id, name, keywords, sources, topics, min_relevance, channels, user, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (alert_id, name, json.dumps(keywords), json.dumps(sources or []), json.dumps(topics or []), min_relevance, json.dumps(channels or []), user, now, now)
        )
        self._conn.commit()
        return self._get_alert(alert_id)

    def _get_alert(self, alert_id):
        c = self._conn.cursor()
        c.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,))
        row = c.fetchone()
        if row:
            return self._row_to_alert(row)
        return None

    def update_alert(self, alert_id, **kwargs):
        allowed = {"name", "keywords", "sources", "topics", "min_relevance", "channels", "user"}
        updates = []
        values = []
        for k, v in kwargs.items():
            if k in allowed:
                if k in ("keywords", "sources", "topics", "channels"):
                    v = json.dumps(v)
                updates.append(f"{k} = ?")
                values.append(v)
        if not updates:
            return False
        updates.append("updated_at = ?")
        values.append(self._now())
        values.append(alert_id)
        c = self._conn.cursor()
        c.execute(f"UPDATE alerts SET {', '.join(updates)} WHERE id = ?", values)
        self._conn.commit()
        return c.rowcount > 0

    def delete_alert(self, alert_id):
        c = self._conn.cursor()
        c.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        c.execute("DELETE FROM alert_logs WHERE alert_id = ?", (alert_id,))
        self._conn.commit()
        return c.rowcount > 0

    def list_alerts(self, user=None):
        c = self._conn.cursor()
        if user:
            c.execute("SELECT * FROM alerts WHERE user = ? ORDER BY created_at DESC", (user,))
        else:
            c.execute("SELECT * FROM alerts ORDER BY created_at DESC")
        return [self._row_to_alert(row) for row in c.fetchall()]

    def check_item(self, item):
        if not isinstance(item, ContentItem):
            return []
        alerts = self.list_alerts()
        matched = []
        text = f"{item.title} {item.content}".lower()
        now = datetime.utcnow()
        for alert in alerts:
            if not alert["enabled"]:
                continue
            if alert["suppressed_until"]:
                try:
                    sup = datetime.fromisoformat(alert["suppressed_until"])
                    if now < sup:
                        continue
                except (ValueError, TypeError):
                    pass
            keywords = alert["keywords"]
            if not keywords:
                continue
            kw_match = any(kw.lower() in text for kw in keywords)
            if not kw_match:
                continue
            sources = alert["sources"]
            if sources and item.source and item.source not in sources:
                continue
            topics = alert["topics"]
            if topics and not any(t in item.topics for t in topics):
                continue
            if abs(item.sentiment) < alert["min_relevance"]:
                continue
            c = self._conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM alert_logs WHERE alert_id = ? AND content_id = ?",
                (alert["id"], item.id)
            )
            if c.fetchone()[0] > 0:
                continue
            matched.append(alert)
        return matched

    def check_items(self, items):
        results = []
        for item in items:
            matches = self.check_item(item)
            if matches:
                results.append({"item_id": item.id, "alerts": matches})
        return results

    def process_new_items(self, items):
        triggered = 0
        for item in items:
            matches = self.check_item(item)
            for alert in matches:
                now = self._now()
                log_id = str(uuid.uuid4())
                c = self._conn.cursor()
                c.execute(
                    "INSERT INTO alert_logs (id, alert_id, content_id, matched_at) VALUES (?, ?, ?, ?)",
                    (log_id, alert["id"], item.id, now)
                )
                self._conn.commit()
                for notifier in self.notifiers:
                    try:
                        send = getattr(notifier, "send_message", None)
                        if send:
                            send(
                                channel=alert["channels"][0] if alert["channels"] else "default",
                                message=f"Alert '{alert['name']}' matched item: {item.title}",
                                data={"alert": alert, "item": {"id": item.id, "title": item.title, "url": item.url}}
                            )
                    except Exception:
                        pass
                c.execute("UPDATE alert_logs SET notified = 1 WHERE id = ?", (log_id,))
                self._conn.commit()
                triggered += 1
        return triggered

    def get_alert_stats(self, days=7):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(*) FROM alerts")
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM alert_logs WHERE matched_at >= ?", (since,))
        triggered = c.fetchone()[0]
        c.execute("""
            SELECT a.name, COUNT(al.id) as cnt FROM alert_logs al
            JOIN alerts a ON al.alert_id = a.id
            WHERE al.matched_at >= ?
            GROUP BY al.alert_id ORDER BY cnt DESC LIMIT 10
        """, (since,))
        top = [{"name": row[0], "count": row[1]} for row in c.fetchall()]
        c.execute("""
            SELECT DATE(matched_at) as day, COUNT(*) as cnt
            FROM alert_logs WHERE matched_at >= ?
            GROUP BY day ORDER BY day
        """, (since,))
        by_day = {row[0]: row[1] for row in c.fetchall()}
        return {
            "total_alerts": total,
            "triggered_count": triggered,
            "top_alerts": top,
            "alerts_by_day": by_day,
        }

    def suppress(self, alert_id, hours=24):
        until = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
        c = self._conn.cursor()
        c.execute("UPDATE alerts SET suppressed_until = ? WHERE id = ?", (until, alert_id))
        self._conn.commit()
        return c.rowcount > 0

import sqlite3
import json
import uuid
import os
from datetime import datetime, timedelta


class SLAMonitor:
    def __init__(self, sql_store=None, db_path="./data/sla.db"):
        self.sql_store = sql_store
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        c = self._conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS slas (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source TEXT NOT NULL,
                topic TEXT,
                max_age_hours INTEGER DEFAULT 24,
                min_items_per_day INTEGER DEFAULT 5,
                severity TEXT DEFAULT 'warning',
                notify TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sla_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sla_id TEXT NOT NULL,
                check_time TEXT NOT NULL,
                compliant INTEGER NOT NULL,
                current_age_hours REAL,
                items_today INTEGER,
                breaches TEXT,
                details TEXT,
                FOREIGN KEY (sla_id) REFERENCES slas(id)
            )
        """)
        self._conn.commit()
        c.close()

    def _now(self):
        return datetime.utcnow().isoformat()

    def _today(self):
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _row_to_sla(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "source": row[2],
            "topic": row[3],
            "max_age_hours": row[4],
            "min_items_per_day": row[5],
            "severity": row[6],
            "notify": json.loads(row[7]) if row[7] else [],
            "enabled": bool(row[8]),
            "created_at": row[9],
            "updated_at": row[10],
        }

    def define_sla(self, name, source, topic=None, max_age_hours=24, min_items_per_day=5, severity="warning", notify=None):
        sla_id = str(uuid.uuid4())
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO slas (id, name, source, topic, max_age_hours, min_items_per_day, severity, notify, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sla_id, name, source, topic, max_age_hours, min_items_per_day, severity, json.dumps(notify or []), now, now)
        )
        self._conn.commit()
        c.close()
        return sla_id

    def _compute_content_age(self, source, topic=None):
        if not self.sql_store:
            return 0.0
        try:
            items = self.sql_store.get_by_source(source, limit=1)
            if not items:
                return float("inf")
            newest = items[0]
            pub = newest.get("published_at")
            if not pub:
                return float("inf")
            if isinstance(pub, str):
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0])
            else:
                pub_dt = pub
            now = datetime.utcnow()
            age = (now - pub_dt).total_seconds() / 3600
            return max(0, age)
        except Exception:
            return float("inf")

    def _count_items_today(self, source, topic=None):
        if not self.sql_store:
            return 0
        try:
            today = self._today()
            items = self.sql_store.get_by_source(source, limit=1000)
            count = 0
            for item in items:
                pub = item.get("published_at")
                if not pub:
                    continue
                if isinstance(pub, str):
                    pub_date = pub[:10]
                else:
                    pub_date = pub.strftime("%Y-%m-%d")
                if pub_date == today:
                    if topic:
                        topics = item.get("topics", "")
                        if isinstance(topics, str):
                            topics_list = topics.split(",")
                        else:
                            topics_list = topics or []
                        if topic not in topics_list:
                            continue
                    count += 1
            return count
        except Exception:
            return 0

    def check_sla(self, sla_id):
        c = self._conn.cursor()
        c.execute("SELECT * FROM slas WHERE id = ?", (sla_id,))
        row = c.fetchone()
        if not row:
            c.close()
            return {"error": "SLA not found"}
        sla = self._row_to_sla(row)
        c.close()
        current_age = self._compute_content_age(sla["source"], sla["topic"])
        items_today = self._count_items_today(sla["source"], sla["topic"])
        breaches = []
        compliant = True
        if current_age > sla["max_age_hours"]:
            compliant = False
            breaches.append({
                "type": "max_age_exceeded",
                "current": round(current_age, 2),
                "max": sla["max_age_hours"],
                "message": f"Content age {current_age:.1f}h exceeds max {sla['max_age_hours']}h"
            })
        if items_today < sla["min_items_per_day"]:
            compliant = False
            breaches.append({
                "type": "min_items_not_met",
                "current": items_today,
                "min": sla["min_items_per_day"],
                "message": f"Items today ({items_today}) below minimum ({sla['min_items_per_day']})"
            })
        now = self._now()
        c = self._conn.cursor()
        c.execute(
            "INSERT INTO sla_checks (sla_id, check_time, compliant, current_age_hours, items_today, breaches, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sla_id, now, 1 if compliant else 0, round(current_age, 2), items_today, json.dumps(breaches), json.dumps(sla))
        )
        self._conn.commit()
        c.close()
        return {
            "sla_id": sla_id,
            "name": sla["name"],
            "source": sla["source"],
            "topic": sla["topic"],
            "compliant": compliant,
            "current_age_hours": round(current_age, 2),
            "max_age_hours": sla["max_age_hours"],
            "items_today": items_today,
            "min_items_per_day": sla["min_items_per_day"],
            "severity": sla["severity"],
            "breaches": breaches,
            "checked_at": now,
        }

    def check_all_slas(self):
        c = self._conn.cursor()
        c.execute("SELECT id FROM slas WHERE enabled = 1")
        sla_ids = [row[0] for row in c.fetchall()]
        c.close()
        results = []
        for sid in sla_ids:
            result = self.check_sla(sid)
            results.append(result)
        return results

    def get_sla_status(self, sla_id):
        c = self._conn.cursor()
        c.execute("SELECT * FROM slas WHERE id = ?", (sla_id,))
        row = c.fetchone()
        if not row:
            c.close()
            return None
        sla = self._row_to_sla(row)
        c.close()
        current_age = self._compute_content_age(sla["source"], sla["topic"])
        items_today = self._count_items_today(sla["source"], sla["topic"])
        c = self._conn.cursor()
        c.execute("SELECT check_time, compliant FROM sla_checks WHERE sla_id = ? ORDER BY check_time DESC LIMIT 1", (sla_id,))
        last_check = c.fetchone()
        c.close()
        return {
            "id": sla["id"],
            "name": sla["name"],
            "source": sla["source"],
            "topic": sla["topic"],
            "max_age_hours": sla["max_age_hours"],
            "min_items_per_day": sla["min_items_per_day"],
            "current_age_hours": round(current_age, 2),
            "items_today": items_today,
            "severity": sla["severity"],
            "enabled": sla["enabled"],
            "last_checked": last_check[0] if last_check else None,
            "last_compliant": bool(last_check[1]) if last_check else None,
        }

    def list_slas(self, source=None, status=None):
        c = self._conn.cursor()
        query = "SELECT * FROM slas WHERE 1=1"
        params = []
        if source:
            query += " AND source = ?"
            params.append(source)
        rows = c.execute(query, params).fetchall()
        c.close()
        slas = [self._row_to_sla(row) for row in rows]
        if status == "compliant":
            slas = [s for s in slas if self._compute_content_age(s["source"], s["topic"]) <= s["max_age_hours"] and self._count_items_today(s["source"], s["topic"]) >= s["min_items_per_day"]]
        elif status == "breaching":
            slas = [s for s in slas if self._compute_content_age(s["source"], s["topic"]) > s["max_age_hours"] or self._count_items_today(s["source"], s["topic"]) < s["min_items_per_day"]]
        return slas

    def get_sla_history(self, sla_id, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT check_time, compliant, current_age_hours, items_today, breaches FROM sla_checks WHERE sla_id = ? AND check_time >= ? ORDER BY check_time ASC",
            (sla_id, since)
        )
        rows = c.fetchall()
        c.close()
        return [
            {
                "check_time": row[0],
                "compliant": bool(row[1]),
                "current_age_hours": row[2],
                "items_today": row[3],
                "breaches": json.loads(row[4]) if row[4] else [],
            }
            for row in rows
        ]

    def get_sla_summary(self, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(DISTINCT sla_id) FROM sla_checks WHERE check_time >= ?", (since,))
        total_slas_checked = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sla_checks WHERE check_time >= ? AND compliant = 1", (since,))
        checks_compliant = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sla_checks WHERE check_time >= ?", (since,))
        total_checks = c.fetchone()[0]
        compliance_rate = (checks_compliant / total_checks * 100) if total_checks > 0 else 0.0
        c.execute("SELECT sla_id, COUNT(*) as cnt FROM sla_checks WHERE check_time >= ? AND compliant = 0 GROUP BY sla_id ORDER BY cnt DESC", (since,))
        top_breaching_rows = c.fetchall()
        c.close()
        top_breaching = []
        for row in top_breaching_rows:
            c2 = self._conn.cursor()
            c2.execute("SELECT name, source FROM slas WHERE id = ?", (row[0],))
            sla_row = c2.fetchone()
            c2.close()
            if sla_row:
                top_breaching.append({"sla_id": row[0], "name": sla_row[0], "source": sla_row[1], "breach_count": row[1]})
        return {
            "total_slas_checked": total_slas_checked,
            "total_checks": total_checks,
            "checks_compliant": checks_compliant,
            "compliance_rate": round(compliance_rate, 2),
            "top_breaching_slas": top_breaching[:10],
            "period_days": days,
        }

    def get_breach_report(self, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute(
            "SELECT sc.sla_id, s.name, s.source, s.severity, sc.check_time, sc.breaches, sc.current_age_hours, sc.items_today FROM sla_checks sc JOIN slas s ON sc.sla_id = s.id WHERE sc.check_time >= ? AND sc.compliant = 0 ORDER BY sc.check_time DESC",
            (since,)
        )
        rows = c.fetchall()
        c.close()
        return [
            {
                "sla_id": row[0],
                "sla_name": row[1],
                "source": row[2],
                "severity": row[3],
                "breached_at": row[4],
                "breaches": json.loads(row[5]) if row[5] else [],
                "current_age_hours": row[6],
                "items_today": row[7],
            }
            for row in rows
        ]

    def get_source_health(self, source, days=30):
        since = (datetime.utcnow() - timedelta(days=days)).isoformat()
        c = self._conn.cursor()
        c.execute("SELECT COUNT(*) FROM sla_checks sc JOIN slas s ON sc.sla_id = s.id WHERE s.source = ? AND sc.check_time >= ? AND sc.compliant = 1", (source, since))
        compliant_checks = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM sla_checks sc JOIN slas s ON sc.sla_id = s.id WHERE s.source = ? AND sc.check_time >= ?", (source, since))
        total_checks = c.fetchone()[0]
        sla_compliance = (compliant_checks / total_checks * 100) if total_checks > 0 else 0.0
        c.execute("SELECT COUNT(DISTINCT s.id) FROM slas s WHERE s.source = ?", (source,))
        total_slas = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM slas WHERE source = ? AND enabled = 1", (source,))
        active_slas = c.fetchone()[0]
        c.close()
        total_items = 0
        avg_age = 0.0
        if self.sql_store:
            try:
                items = self.sql_store.get_by_source(source, limit=1000)
                total_items = len(items)
                ages = []
                for item in items:
                    pub = item.get("published_at")
                    if pub:
                        if isinstance(pub, str):
                            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split("+")[0])
                        else:
                            pub_dt = pub
                        age_h = (datetime.utcnow() - pub_dt).total_seconds() / 3600
                        ages.append(max(0, age_h))
                if ages:
                    avg_age = sum(ages) / len(ages)
            except Exception:
                pass
        return {
            "source": source,
            "sla_compliance_pct": round(sla_compliance, 2),
            "total_slas": total_slas,
            "active_slas": active_slas,
            "total_items_collected": total_items,
            "avg_content_age_hours": round(avg_age, 2) if avg_age else 0,
            "items_per_day": round(total_items / max(days, 1), 2),
            "uptime_pct": round(sla_compliance, 2),
        }

    def get_all_sources_health(self, days=30):
        c = self._conn.cursor()
        c.execute("SELECT DISTINCT source FROM slas")
        sources = [row[0] for row in c.fetchall()]
        c.close()
        health_data = {}
        for src in sources:
            health_data[src] = self.get_source_health(src, days=days)
        return health_data

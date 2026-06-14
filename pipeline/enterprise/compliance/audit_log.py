import json
import logging
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class AuditLogger:
    def __init__(self, db_path: str = "./data/audit.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                    event TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    ip_address TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_actor
                ON events(actor)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_resource_type
                ON events(resource_type)
            """)

    def log(
        self,
        event: str,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict | None = None,
        ip_address: str | None = None,
    ):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO events (event, actor, action, resource_type, resource_id, details, ip_address)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event,
                    actor,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(details or {}),
                    ip_address,
                ),
            )
        logger.info(f"Audit: {event} | {actor} | {action} | {resource_type}:{resource_id}")

    def query(
        self,
        actor: str | None = None,
        event: str | None = None,
        resource_type: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conditions = []
        params: list[Any] = []
        if actor:
            conditions.append("actor = ?")
            params.append(actor)
        if event:
            conditions.append("event = ?")
            params.append(event)
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        where = " AND ".join(conditions) if conditions else "1=1"
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM events WHERE {where} ORDER BY timestamp DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_user_activity(self, username: str, days: int = 30) -> list[dict]:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        return self.query(actor=username, start_time=cutoff)

    def get_resource_history(self, resource_type: str, resource_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE resource_type = ? AND resource_id = ? ORDER BY timestamp DESC",
                (resource_type, resource_id),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_summary(self, days: int = 7) -> dict:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM events WHERE timestamp >= ?", (cutoff,)
            ).fetchone()[0]
            unique_actors = conn.execute(
                "SELECT COUNT(DISTINCT actor) FROM events WHERE timestamp >= ?", (cutoff,)
            ).fetchone()[0]
            top_actions = [
                dict(r)
                for r in conn.execute(
                    "SELECT action, COUNT(*) as cnt FROM events WHERE timestamp >= ? GROUP BY action ORDER BY cnt DESC LIMIT 10",
                    (cutoff,),
                ).fetchall()
            ]
            events_by_day = [
                dict(r)
                for r in conn.execute(
                    "SELECT DATE(timestamp) as day, COUNT(*) as cnt FROM events WHERE timestamp >= ? GROUP BY DATE(timestamp) ORDER BY day",
                    (cutoff,),
                ).fetchall()
            ]
        return {
            "total_events": total,
            "unique_actors": unique_actors,
            "top_actions": top_actions,
            "events_by_day": {r["day"]: r["cnt"] for r in events_by_day},
        }

    def export_logs(self, format: str = "json", days: int = 30) -> str:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM events WHERE timestamp >= ? ORDER BY timestamp", (cutoff,)
            ).fetchall()
        data = [dict(r) for r in rows]
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        lines = []
        for r in data:
            lines.append(
                f"{r['timestamp']} | {r['actor']} | {r['action']} | {r['resource_type']}:{r['resource_id']} | {r['event']}"
            )
        return "\n".join(lines)

    def get_stats(self) -> dict:
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            oldest = conn.execute(
                "SELECT MIN(timestamp) FROM events"
            ).fetchone()[0]
            newest = conn.execute(
                "SELECT MAX(timestamp) FROM events"
            ).fetchone()[0]
            by_type = [
                dict(r)
                for r in conn.execute(
                    "SELECT event, COUNT(*) as cnt FROM events GROUP BY event ORDER BY cnt DESC"
                ).fetchall()
            ]
            size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
        return {
            "total_events": total,
            "db_size_bytes": size,
            "oldest_entry": oldest,
            "newest_entry": newest,
            "events_by_type": {r["event"]: r["cnt"] for r in by_type},
        }

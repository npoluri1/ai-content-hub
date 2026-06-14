import sqlite3
import os
from datetime import datetime, timedelta, timezone
from typing import Optional


VALID_ACTIONS = {
    "content_added", "content_removed", "comment_added",
    "member_joined", "member_left", "workspace_updated",
    "digest_generated", "alert_triggered",
    "content_approved", "content_rejected"
}


class ActivityFeed:
    def __init__(self, db_path: str = "./data/activity.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workspace_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    target_name TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}',
                    timestamp TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_ws ON activities(workspace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_actor ON activities(actor)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_ts ON activities(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_action ON activities(action)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_act_target ON activities(target_type, target_id)")

    def log(
        self,
        workspace_id: str,
        actor: str,
        action: str,
        target_type: str,
        target_id: str,
        target_name: str = "",
        metadata: dict = None
    ) -> dict:
        if action not in VALID_ACTIONS:
            raise ValueError(f"Invalid action '{action}'. Valid: {', '.join(sorted(VALID_ACTIONS))}")
        meta_json = json.dumps(metadata or {})
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """INSERT INTO activities (workspace_id, actor, action, target_type, target_id, target_name, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (workspace_id, actor, action, target_type, target_id, target_name, meta_json)
            )
            row = conn.execute("SELECT * FROM activities WHERE id = ?", (cur.lastrowid,)).fetchone()
            result = dict(row)
            result["metadata"] = json.loads(result["metadata"])
            return result

    def get_feed(
        self,
        workspace_id: str,
        limit: int = 50,
        offset: int = 0,
        actions: list[str] = None
    ) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if actions:
                placeholders = ",".join("?" for _ in actions)
                params = [workspace_id] + actions + [limit, offset]
                rows = conn.execute(
                    f"""SELECT * FROM activities
                        WHERE workspace_id = ? AND action IN ({placeholders})
                        ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                    params
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM activities
                       WHERE workspace_id = ?
                       ORDER BY timestamp DESC LIMIT ? OFFSET ?""",
                    (workspace_id, limit, offset)
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_global_feed(self, limit: int = 50, offset: int = 0) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activities ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_user_feed(self, user: str, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activities WHERE actor = ? ORDER BY timestamp DESC LIMIT ?",
                (user, limit)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_item_history(self, content_id: str) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM activities WHERE target_id = ? ORDER BY timestamp ASC",
                (content_id,)
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_workspace_summary(self, workspace_id: str, days: int = 7) -> dict:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as total FROM activities WHERE workspace_id = ? AND timestamp >= ?",
                (workspace_id, since)
            ).fetchone()
            total = row[0]

            rows = conn.execute(
                "SELECT action, COUNT(*) as cnt FROM activities WHERE workspace_id = ? AND timestamp >= ? GROUP BY action ORDER BY cnt DESC",
                (workspace_id, since)
            ).fetchall()

            actors = conn.execute(
                "SELECT COUNT(DISTINCT actor) as cnt FROM activities WHERE workspace_id = ? AND timestamp >= ?",
                (workspace_id, since)
            ).fetchone()

            return {
                "workspace_id": workspace_id,
                "period_days": days,
                "total_activities": total,
                "unique_actors": actors[0],
                "action_breakdown": {r[0]: r[1] for r in rows}
            }

    def search_activity(
        self,
        query: str,
        workspace_id: str = None,
        limit: int = 50
    ) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            like = f"%{query}%"
            if workspace_id:
                rows = conn.execute(
                    """SELECT * FROM activities
                       WHERE workspace_id = ?
                         AND (actor LIKE ? OR target_name LIKE ? OR action LIKE ? OR target_type LIKE ?)
                       ORDER BY timestamp DESC LIMIT ?""",
                    (workspace_id, like, like, like, like, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM activities
                       WHERE actor LIKE ? OR target_name LIKE ? OR action LIKE ? OR target_type LIKE ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (like, like, like, like, limit)
                ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_heatmap_data(self, workspace_id: str, days: int = 30) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT timestamp FROM activities
                   WHERE workspace_id = ? AND timestamp >= ?
                   ORDER BY timestamp ASC""",
                (workspace_id, since)
            ).fetchall()

        buckets = {}
        for (ts_str,) in rows:
            try:
                ts = datetime.fromisoformat(ts_str)
            except (ValueError, TypeError):
                continue
            key = ts.strftime("%Y-%m-%d") + ":" + str(ts.hour)
            buckets[key] = buckets.get(key, 0) + 1

        result = []
        for key, count in sorted(buckets.items()):
            date, hour = key.split(":")
            result.append({"date": date, "hour": int(hour), "count": count})
        return result

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"])
        return d


import json

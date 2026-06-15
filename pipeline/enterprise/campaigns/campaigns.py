import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

CAMPAIGN_STAGES = [
    "ideation",
    "planning",
    "in_progress",
    "review",
    "launched",
    "post_launch",
    "completed",
    "cancelled",
]

STAGE_DISPLAY = {
    "ideation": "Ideation",
    "planning": "Planning",
    "in_progress": "In Progress",
    "review": "Review",
    "launched": "Launched",
    "post_launch": "Post-Launch",
    "completed": "Completed",
    "cancelled": "Cancelled",
}

STAGE_ORDER = {s: i for i, s in enumerate(CAMPAIGN_STAGES)}


class CampaignManager:
    def __init__(self, db_path: str = "./data/campaigns.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    stage TEXT NOT NULL DEFAULT 'ideation',
                    owner TEXT NOT NULL,
                    project_id TEXT DEFAULT '',
                    launch_date TEXT,
                    target_audience TEXT DEFAULT '',
                    goals TEXT DEFAULT '[]',
                    budget REAL DEFAULT 0.0,
                    settings TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_tasks (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    assignee TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'todo',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    due_date TEXT,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    completed_at TEXT,
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_members (
                    campaign_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (campaign_id, user),
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_reports (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    report_type TEXT NOT NULL DEFAULT 'analysis',
                    content TEXT DEFAULT '',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_content (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at TEXT NOT NULL DEFAULT (datetime('now')),
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS campaign_metrics (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL DEFAULT 0.0,
                    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                    recorded_by TEXT DEFAULT 'system',
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
                )
            """)

    def create_campaign(
        self,
        name: str,
        description: str = "",
        owner: str = "admin",
        project_id: str = "",
        launch_date: str = "",
        target_audience: str = "",
        goals: list[str] | None = None,
        budget: float = 0.0,
    ) -> dict:
        cid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        goals_json = json.dumps(goals or [])
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO campaigns
                   (id, name, description, stage, owner, project_id, launch_date, target_audience, goals, budget, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (cid, name, description, "ideation", owner, project_id, launch_date, target_audience, goals_json, budget, now, now),
            )
            conn.execute(
                "INSERT INTO campaign_members (campaign_id, user, role) VALUES (?, ?, ?)",
                (cid, owner, "admin"),
            )
        return self.get_campaign(cid)

    def get_campaign(self, cid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
            return self._row_to_dict(row) if row else None

    def list_campaigns(self, user: str | None = None, stage: str | None = None, project_id: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            conditions = []
            params = []
            if user:
                conditions.append("c.id IN (SELECT campaign_id FROM campaign_members WHERE user=?)")
                params.append(user)
            if stage:
                conditions.append("c.stage=?")
                params.append(stage)
            if project_id:
                conditions.append("c.project_id=?")
                params.append(project_id)
            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = conn.execute(
                f"SELECT c.* FROM campaigns c {where} ORDER BY c.updated_at DESC", params
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def update_campaign(self, cid: str, updates: dict) -> dict | None:
        allowed = {"name", "description", "stage", "launch_date", "target_audience", "goals", "budget", "settings"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if "goals" in safe and isinstance(safe["goals"], list):
            safe["goals"] = json.dumps(safe["goals"])
        if not safe:
            return self.get_campaign(cid)
        safe["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k}=?" for k in safe)
        vals = list(safe.values()) + [cid]
        with self._get_conn() as conn:
            conn.execute(f"UPDATE campaigns SET {sets} WHERE id=?", vals)
        return self.get_campaign(cid)

    def delete_campaign(self, cid: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
            return cur.rowcount > 0

    def add_task(self, cid: str, title: str, description: str = "", assignee: str = "", priority: str = "medium", due_date: str = "", created_by: str = "admin") -> dict | None:
        tid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO campaign_tasks (id, campaign_id, title, description, assignee, status, priority, due_date, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (tid, cid, title, description, assignee, "todo", priority, due_date, created_by, now),
            )
        return self.get_task(tid)

    def get_task(self, tid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM campaign_tasks WHERE id=?", (tid,)).fetchone()
            return dict(row) if row else None

    def list_tasks(self, cid: str, status: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM campaign_tasks WHERE campaign_id=? AND status=? ORDER BY created_at", (cid, status)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM campaign_tasks WHERE campaign_id=? ORDER BY created_at", (cid,)
                ).fetchall()
            return [dict(r) for r in rows]

    def update_task(self, tid: str, updates: dict) -> dict | None:
        allowed = {"title", "description", "assignee", "status", "priority", "due_date"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if "status" in safe and safe["status"] == "done":
            safe["completed_at"] = datetime.utcnow().isoformat()
        if not safe:
            return self.get_task(tid)
        sets = ", ".join(f"{k}=?" for k in safe)
        vals = list(safe.values()) + [tid]
        with self._get_conn() as conn:
            conn.execute(f"UPDATE campaign_tasks SET {sets} WHERE id=?", vals)
        return self.get_task(tid)

    def delete_task(self, tid: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM campaign_tasks WHERE id=?", (tid,))
            return cur.rowcount > 0

    def add_member(self, cid: str, user: str, role: str = "viewer") -> dict | None:
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO campaign_members (campaign_id, user, role) VALUES (?, ?, ?)",
                    (cid, user, role),
                )
                return {"campaign_id": cid, "user": user, "role": role}
            except sqlite3.IntegrityError:
                return None

    def remove_member(self, cid: str, user: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM campaign_members WHERE campaign_id=? AND user=?", (cid, user))
            return cur.rowcount > 0

    def get_members(self, cid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_members WHERE campaign_id=? ORDER BY joined_at", (cid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def add_report(self, cid: str, title: str, content: str = "", report_type: str = "analysis", created_by: str = "admin") -> dict | None:
        rid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO campaign_reports (id, campaign_id, title, report_type, content, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, cid, title, report_type, content, created_by, now),
            )
        return self.get_report(rid)

    def get_report(self, rid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM campaign_reports WHERE id=?", (rid,)).fetchone()
            return dict(row) if row else None

    def list_reports(self, cid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_reports WHERE campaign_id=? ORDER BY created_at DESC", (cid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def add_content(self, cid: str, content_id: str, added_by: str = "admin", notes: str = "") -> dict | None:
        cc_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO campaign_content (id, campaign_id, content_id, added_by, added_at, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (cc_id, cid, content_id, added_by, now, notes),
            )
        return {"id": cc_id, "campaign_id": cid, "content_id": content_id, "added_by": added_by, "added_at": now, "notes": notes}

    def list_content(self, cid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_content WHERE campaign_id=? ORDER BY added_at DESC", (cid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def remove_content(self, cid: str, content_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM campaign_content WHERE campaign_id=? AND content_id=?", (cid, content_id)
            )
            return cur.rowcount > 0

    def record_metric(self, cid: str, metric_name: str, metric_value: float, recorded_by: str = "system", notes: str = "") -> dict:
        mid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO campaign_metrics (id, campaign_id, metric_name, metric_value, recorded_at, recorded_by, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (mid, cid, metric_name, metric_value, now, recorded_by, notes),
            )
        return {"id": mid, "campaign_id": cid, "metric_name": metric_name, "metric_value": metric_value, "recorded_at": now}

    def get_metrics(self, cid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM campaign_metrics WHERE campaign_id=? ORDER BY recorded_at DESC", (cid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_campaign_stats(self, cid: str) -> dict:
        with self._get_conn() as conn:
            member_count = conn.execute(
                "SELECT COUNT(*) as c FROM campaign_members WHERE campaign_id=?", (cid,)
            ).fetchone()["c"]
            task_counts = conn.execute(
                "SELECT status, COUNT(*) as c FROM campaign_tasks WHERE campaign_id=? GROUP BY status", (cid,)
            ).fetchall()
            total_tasks = sum(r["c"] for r in task_counts)
            done_tasks = sum(r["c"] for r in task_counts if r["status"] == "done")
            report_count = conn.execute(
                "SELECT COUNT(*) as c FROM campaign_reports WHERE campaign_id=?", (cid,)
            ).fetchone()["c"]
            content_count = conn.execute(
                "SELECT COUNT(*) as c FROM campaign_content WHERE campaign_id=?", (cid,)
            ).fetchone()["c"]
            return {
                "members": member_count,
                "total_tasks": total_tasks,
                "done_tasks": done_tasks,
                "completion_pct": round((done_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
                "reports": report_count,
                "content_items": content_count,
            }

    def get_stage_summary(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT stage, COUNT(*) as count FROM campaigns GROUP BY stage ORDER BY stage"
            ).fetchall()
            return [dict(r) for r in rows]

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        for field in ("settings", "goals"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

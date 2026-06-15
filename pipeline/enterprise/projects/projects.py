import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ProjectManager:
    def __init__(self, db_path: str = "./data/projects.db"):
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
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    owner TEXT NOT NULL,
                    settings TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_members (
                    project_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (project_id, user),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_reports (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    report_type TEXT NOT NULL DEFAULT 'analysis',
                    content TEXT DEFAULT '',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_chats (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    messages TEXT DEFAULT '[]',
                    model_id TEXT DEFAULT '',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    context_type TEXT NOT NULL DEFAULT 'document',
                    content TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_content (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at TEXT NOT NULL DEFAULT (datetime('now')),
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)

    def create_project(self, name: str, description: str = "", owner: str = "admin", settings: dict | None = None) -> dict:
        pid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        settings_json = json.dumps(settings or {})
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO projects (id, name, description, owner, settings, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, name, description, owner, settings_json, now, now),
            )
            conn.execute(
                "INSERT INTO project_members (project_id, user, role) VALUES (?, ?, ?)",
                (pid, owner, "admin"),
            )
        return self.get_project(pid)

    def get_project(self, pid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_projects(self, user: str | None = None, status: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            if user:
                rows = conn.execute(
                    "SELECT p.* FROM projects p JOIN project_members pm ON p.id=pm.project_id WHERE pm.user=? ORDER BY p.updated_at DESC",
                    (user,),
                ).fetchall()
            elif status:
                rows = conn.execute(
                    "SELECT * FROM projects WHERE status=? ORDER BY updated_at DESC", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall()
            return [self._row_to_dict(r) for r in rows]

    def update_project(self, pid: str, updates: dict) -> dict | None:
        allowed = {"name", "description", "status", "settings"}
        safe = {k: v for k, v in updates.items() if k in allowed}
        if not safe:
            return self.get_project(pid)
        safe["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k}=?" for k in safe)
        vals = list(safe.values()) + [pid]
        with self._get_conn() as conn:
            conn.execute(f"UPDATE projects SET {sets} WHERE id=?", vals)
        return self.get_project(pid)

    def delete_project(self, pid: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM projects WHERE id=?", (pid,))
            return cur.rowcount > 0

    def add_member(self, pid: str, user: str, role: str = "viewer") -> dict | None:
        with self._get_conn() as conn:
            try:
                conn.execute(
                    "INSERT INTO project_members (project_id, user, role) VALUES (?, ?, ?)",
                    (pid, user, role),
                )
                return {"project_id": pid, "user": user, "role": role}
            except sqlite3.IntegrityError:
                return None

    def remove_member(self, pid: str, user: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM project_members WHERE project_id=? AND user=?", (pid, user))
            return cur.rowcount > 0

    def get_members(self, pid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM project_members WHERE project_id=? ORDER BY joined_at", (pid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def add_report(self, pid: str, title: str, content: str = "", report_type: str = "analysis", created_by: str = "admin") -> dict | None:
        rid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO project_reports (id, project_id, title, report_type, content, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, pid, title, report_type, content, created_by, now),
            )
        return self.get_report(rid)

    def get_report(self, rid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM project_reports WHERE id=?", (rid,)).fetchone()
            return dict(row) if row else None

    def list_reports(self, pid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM project_reports WHERE project_id=? ORDER BY created_at DESC", (pid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_report(self, rid: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM project_reports WHERE id=?", (rid,))
            return cur.rowcount > 0

    def create_chat(self, pid: str, title: str, created_by: str = "admin", model_id: str = "") -> dict | None:
        cid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO project_chats (id, project_id, title, messages, model_id, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (cid, pid, title, "[]", model_id, created_by, now, now),
            )
        return self.get_chat(cid)

    def get_chat(self, cid: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM project_chats WHERE id=?", (cid,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["messages"] = json.loads(d.get("messages", "[]"))
            return d

    def list_chats(self, pid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM project_chats WHERE project_id=? ORDER BY updated_at DESC", (pid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def update_chat(self, cid: str, messages: list[dict]) -> dict | None:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE project_chats SET messages=?, updated_at=? WHERE id=?",
                (json.dumps(messages), now, cid),
            )
        return self.get_chat(cid)

    def add_context(self, pid: str, title: str, content: str = "", context_type: str = "document", url: str = "", tags: list[str] | None = None, created_by: str = "admin") -> dict | None:
        ctx_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        tags_json = json.dumps(tags or [])
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO project_context (id, project_id, title, context_type, content, url, tags, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (ctx_id, pid, title, context_type, content, url, tags_json, created_by, now),
            )
        return self.get_context(ctx_id)

    def get_context(self, ctx_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM project_context WHERE id=?", (ctx_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["tags"] = json.loads(d.get("tags", "[]"))
            return d

    def list_context(self, pid: str, context_type: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            if context_type:
                rows = conn.execute(
                    "SELECT * FROM project_context WHERE project_id=? AND context_type=? ORDER BY created_at DESC",
                    (pid, context_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM project_context WHERE project_id=? ORDER BY created_at DESC", (pid,)
                ).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["tags"] = json.loads(d.get("tags", "[]"))
                results.append(d)
            return results

    def delete_context(self, ctx_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute("DELETE FROM project_context WHERE id=?", (ctx_id,))
            return cur.rowcount > 0

    def add_content(self, pid: str, content_id: str, added_by: str = "admin", notes: str = "") -> dict | None:
        cid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO project_content (id, project_id, content_id, added_by, added_at, notes) VALUES (?, ?, ?, ?, ?, ?)",
                (cid, pid, content_id, added_by, now, notes),
            )
        return {"id": cid, "project_id": pid, "content_id": content_id, "added_by": added_by, "added_at": now, "notes": notes}

    def list_content(self, pid: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM project_content WHERE project_id=? ORDER BY added_at DESC", (pid,)
            ).fetchall()
            return [dict(r) for r in rows]

    def remove_content(self, pid: str, content_id: str) -> bool:
        with self._get_conn() as conn:
            cur = conn.execute(
                "DELETE FROM project_content WHERE project_id=? AND content_id=?", (pid, content_id)
            )
            return cur.rowcount > 0

    def get_project_stats(self, pid: str) -> dict:
        with self._get_conn() as conn:
            member_count = conn.execute(
                "SELECT COUNT(*) as c FROM project_members WHERE project_id=?", (pid,)
            ).fetchone()["c"]
            report_count = conn.execute(
                "SELECT COUNT(*) as c FROM project_reports WHERE project_id=?", (pid,)
            ).fetchone()["c"]
            chat_count = conn.execute(
                "SELECT COUNT(*) as c FROM project_chats WHERE project_id=?", (pid,)
            ).fetchone()["c"]
            context_count = conn.execute(
                "SELECT COUNT(*) as c FROM project_context WHERE project_id=?", (pid,)
            ).fetchone()["c"]
            content_count = conn.execute(
                "SELECT COUNT(*) as c FROM project_content WHERE project_id=?", (pid,)
            ).fetchone()["c"]
            return {
                "members": member_count,
                "reports": report_count,
                "chats": chat_count,
                "context_items": context_count,
                "content_items": content_count,
            }

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        for field in ("settings",):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

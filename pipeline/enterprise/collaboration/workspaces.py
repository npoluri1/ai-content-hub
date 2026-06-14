import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from pipeline.core.models import ContentItem

logger = logging.getLogger(__name__)


class WorkspaceManager:
    def __init__(self, db_path: str = "./data/workspaces.db"):
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
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    owner TEXT NOT NULL,
                    settings TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspace_members (
                    workspace_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'viewer',
                    joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (workspace_id, user),
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspace_content (
                    id TEXT PRIMARY KEY,
                    workspace_id TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    added_at TEXT NOT NULL DEFAULT (datetime('now')),
                    title TEXT DEFAULT '',
                    content TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    author_name TEXT DEFAULT '',
                    topics TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
                )
            """)

    def create_workspace(
        self,
        name: str,
        description: str,
        owner: str,
        settings: dict | None = None,
    ) -> dict:
        ws_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        settings_json = json.dumps(settings or {})
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO workspaces (id, name, description, owner, settings, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (ws_id, name, description, owner, settings_json, now, now),
            )
            conn.execute(
                "INSERT INTO workspace_members (workspace_id, user, role) VALUES (?, ?, ?)",
                (ws_id, owner, "admin"),
            )
            conn.commit()
        logger.info(f"Workspace created: {ws_id} ({name}) by {owner}")
        return {
            "id": ws_id,
            "name": name,
            "description": description,
            "owner": owner,
            "settings": settings or {},
            "created_at": now,
            "updated_at": now,
        }

    def get_workspace(self, workspace_id: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM workspaces WHERE id = ?", (workspace_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["settings"] = json.loads(result.get("settings", "{}"))
        return result

    def list_workspaces(self, user: str | None = None) -> list[dict]:
        with self._get_conn() as conn:
            if user:
                rows = conn.execute(
                    """SELECT w.* FROM workspaces w
                       JOIN workspace_members m ON w.id = m.workspace_id
                       WHERE m.user = ?
                       ORDER BY w.updated_at DESC""",
                    (user,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM workspaces ORDER BY updated_at DESC"
                ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["settings"] = json.loads(d.get("settings", "{}"))
            results.append(d)
        return results

    def delete_workspace(self, workspace_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM workspaces WHERE id = ?", (workspace_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_member(self, workspace_id: str, user: str, role: str = "viewer") -> bool:
        valid_roles = {"admin", "editor", "viewer", "scraper"}
        if role not in valid_roles:
            logger.warning(f"Invalid role '{role}', using 'viewer'")
            role = "viewer"
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO workspace_members (workspace_id, user, role) VALUES (?, ?, ?)",
                    (workspace_id, user, role),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            return False

    def remove_member(self, workspace_id: str, user: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM workspace_members WHERE workspace_id = ? AND user = ?",
                (workspace_id, user),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_members(self, workspace_id: str) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM workspace_members WHERE workspace_id = ? ORDER BY joined_at",
                (workspace_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_content(self, workspace_id: str, item: ContentItem, added_by: str) -> bool:
        content_id = item.id or str(uuid.uuid4())
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO workspace_content
                       (id, workspace_id, added_by, title, content, url, source, author_name, topics, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        content_id,
                        workspace_id,
                        added_by,
                        item.title,
                        item.content,
                        item.url,
                        item.source,
                        item.author_name,
                        json.dumps(item.topics),
                        json.dumps(item.metadata),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add content: {e}")
            return False

    def remove_content(self, workspace_id: str, content_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM workspace_content WHERE id = ? AND workspace_id = ?",
                (content_id, workspace_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_content(
        self,
        workspace_id: str,
        topic: str | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conditions = ["workspace_id = ?"]
        params: list[Any] = [workspace_id]
        if topic:
            conditions.append("topics LIKE ?")
            params.append(f"%{topic}%")
        if source:
            conditions.append("source = ?")
            params.append(source)
        where = " AND ".join(conditions)
        with self._get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM workspace_content WHERE {where} ORDER BY added_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["topics"] = json.loads(d.get("topics", "[]"))
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            results.append(d)
        return results

    def update_settings(self, workspace_id: str, settings: dict) -> bool:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE workspaces SET settings = ?, updated_at = ? WHERE id = ?",
                (json.dumps(settings), now, workspace_id),
            )
            conn.commit()
            return cursor.rowcount > 0

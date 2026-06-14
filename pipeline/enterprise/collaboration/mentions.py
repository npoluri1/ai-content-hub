import sqlite3
import os
import re
import json
from datetime import datetime, timezone
from typing import Optional


class MentionSystem:
    def __init__(self, db_path: str = "./data/mentions.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'mention',
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    content_id TEXT,
                    workspace_id TEXT,
                    source TEXT DEFAULT 'mention',
                    is_read INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_prefs (
                    user TEXT PRIMARY KEY,
                    email INTEGER DEFAULT 1,
                    slack INTEGER DEFAULT 0,
                    telegram INTEGER DEFAULT 0,
                    in_app INTEGER DEFAULT 1,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_user
                ON notifications(user)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notifications_unread
                ON notifications(user, is_read)
            """)

    def parse_mentions(self, text: str) -> list[str]:
        if not text:
            return []
        matches = re.findall(r'@(\w[\w.-]*)', text)
        return list(set(matches))

    def notify_mentioned(
        self,
        content_id: str,
        text: str,
        mentioned_by: str,
        workspace_id: str = None
    ) -> list[dict]:
        mentions = self.parse_mentions(text)
        results = []
        for user in mentions:
            if user == mentioned_by:
                continue
            notif = self.create_notification(
                user=user,
                type="mention",
                title=f"You were mentioned by {mentioned_by}",
                message=f"{mentioned_by} mentioned you in {'workspace ' + workspace_id if workspace_id else 'a post'}",
                content_id=content_id,
                workspace_id=workspace_id,
                source="mention"
            )
            results.append(notif)
            self.send_push_notification(user, notif["title"], notif["message"])
        return results

    def create_notification(
        self,
        user: str,
        type: str,
        title: str,
        message: str,
        content_id: str = None,
        workspace_id: str = None,
        source: str = "mention"
    ) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """INSERT INTO notifications (user, type, title, message, content_id, workspace_id, source)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user, type, title, message, content_id, workspace_id, source)
            )
            notif_id = cur.lastrowid
            row = conn.execute("SELECT * FROM notifications WHERE id = ?", (notif_id,)).fetchone()
            return dict(row)

    def get_notifications(self, user: str, unread_only: bool = True, limit: int = 50) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if unread_only:
                rows = conn.execute(
                    "SELECT * FROM notifications WHERE user = ? AND is_read = 0 ORDER BY created_at DESC LIMIT ?",
                    (user, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM notifications WHERE user = ? ORDER BY created_at DESC LIMIT ?",
                    (user, limit)
                ).fetchall()
            return [dict(r) for r in rows]

    def mark_read(self, notification_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE id = ?",
                (notification_id,)
            )
            return cur.rowcount > 0

    def mark_all_read(self, user: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE user = ? AND is_read = 0",
                (user,)
            )
            return cur.rowcount

    def get_unread_count(self, user: str) -> int:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user = ? AND is_read = 0",
                (user,)
            ).fetchone()
            return row[0]

    def delete_notification(self, notification_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            return cur.rowcount > 0

    def get_notification_preferences(self, user: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM notification_prefs WHERE user = ?", (user,)
            ).fetchone()
            if row:
                return dict(row)
            return {
                "user": user,
                "email": True,
                "slack": False,
                "telegram": False,
                "in_app": True
            }

    def set_notification_preferences(self, user: str, prefs: dict) -> bool:
        email = int(prefs.get("email", True))
        slack = int(prefs.get("slack", False))
        telegram = int(prefs.get("telegram", False))
        in_app = int(prefs.get("in_app", True))
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO notification_prefs (user, email, slack, telegram, in_app, updated_at)
                   VALUES (?, ?, ?, ?, ?, datetime('now'))
                   ON CONFLICT(user) DO UPDATE SET
                       email = excluded.email,
                       slack = excluded.slack,
                       telegram = excluded.telegram,
                       in_app = excluded.in_app,
                       updated_at = datetime('now')""",
                (user, email, slack, telegram, in_app)
            )
            return True

    def send_push_notification(self, user: str, title: str, message: str) -> bool:
        prefs = self.get_notification_preferences(user)
        sent = False
        if prefs.get("in_app"):
            sent = True
        return sent

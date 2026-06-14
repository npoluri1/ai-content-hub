import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

VALID_REACTIONS = {"👍", "❤️", "🎯", "💡", "🤔", "🔥"}


class CommentSystem:
    def __init__(self, db_path: str = "./data/comments.db"):
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
                CREATE TABLE IF NOT EXISTS comments (
                    id TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    text TEXT NOT NULL,
                    parent_id TEXT,
                    is_pinned INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (parent_id) REFERENCES comments(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comment_reactions (
                    comment_id TEXT NOT NULL,
                    user TEXT NOT NULL,
                    reaction TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (comment_id, user, reaction),
                    FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_comments_content
                ON comments(content_id)
            """)

    def add_comment(
        self,
        content_id: str,
        user: str,
        text: str,
        parent_id: str | None = None,
    ) -> dict:
        comment_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO comments (id, content_id, user, text, parent_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (comment_id, content_id, user, text, parent_id, now, now),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            return {}
        return {
            "id": comment_id,
            "content_id": content_id,
            "user": user,
            "text": text,
            "parent_id": parent_id,
            "is_pinned": False,
            "created_at": now,
            "updated_at": now,
        }

    def get_comments(self, content_id: str, include_replies: bool = True) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE content_id = ? ORDER BY is_pinned DESC, created_at ASC",
                (content_id,),
            ).fetchall()
        comments = [dict(r) for r in rows]
        for c in comments:
            c["reactions"] = self.get_reactions(c["id"])
        if not include_replies:
            return [c for c in comments if c["parent_id"] is None]
        return self._build_thread(comments)

    def _build_thread(self, comments: list[dict]) -> list[dict]:
        comment_map: dict[str, dict] = {}
        roots: list[dict] = []
        for c in comments:
            c["replies"] = []
            comment_map[c["id"]] = c
        for c in comments:
            if c["parent_id"] and c["parent_id"] in comment_map:
                comment_map[c["parent_id"]]["replies"].append(c)
            else:
                roots.append(c)
        return roots

    def update_comment(self, comment_id: str, text: str) -> bool:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE comments SET text = ?, updated_at = ? WHERE id = ?",
                (text, now, comment_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_comment(self, comment_id: str) -> bool:
        with self._get_conn() as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            cursor = conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
            conn.commit()
            return cursor.rowcount > 0

    def add_reaction(self, comment_id: str, user: str, reaction: str) -> bool:
        if reaction not in VALID_REACTIONS:
            logger.warning(f"Invalid reaction: {reaction}")
            return False
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO comment_reactions (comment_id, user, reaction) VALUES (?, ?, ?)",
                    (comment_id, user, reaction),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to add reaction: {e}")
            return False

    def remove_reaction(self, comment_id: str, user: str, reaction: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "DELETE FROM comment_reactions WHERE comment_id = ? AND user = ? AND reaction = ?",
                (comment_id, user, reaction),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_reactions(self, comment_id: str) -> dict[str, int]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT reaction, COUNT(*) as cnt FROM comment_reactions WHERE comment_id = ? GROUP BY reaction",
                (comment_id,),
            ).fetchall()
        return {r["reaction"]: r["cnt"] for r in rows}

    def pin_comment(self, comment_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "UPDATE comments SET is_pinned = 1 WHERE id = ?",
                (comment_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_user_comments(self, user: str, limit: int = 20) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM comments WHERE user = ? ORDER BY created_at DESC LIMIT ?",
                (user, limit),
            ).fetchall()
        comments = [dict(r) for r in rows]
        for c in comments:
            c["reactions"] = self.get_reactions(c["id"])
        return comments

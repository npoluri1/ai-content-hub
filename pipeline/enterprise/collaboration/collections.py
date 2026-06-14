import sqlite3
import os
import json
import secrets
import string
from datetime import datetime, timedelta, timezone


def _generate_id(length: int = 16) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class CollectionManager:
    def __init__(self, db_path: str = "./data/collections.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    workspace_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    cover_image TEXT,
                    tags TEXT DEFAULT '[]',
                    item_count INTEGER DEFAULT 0,
                    view_count INTEGER DEFAULT 0,
                    share_code TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS collection_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_id TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    added_by TEXT NOT NULL,
                    note TEXT,
                    item_order INTEGER DEFAULT 0,
                    added_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE,
                    UNIQUE(collection_id, content_id)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coll_ws ON collections(workspace_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coll_creator ON collections(created_by)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coll_items_cid ON collection_items(collection_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_coll_items_content ON collection_items(content_id)")

    def create_collection(
        self,
        name: str,
        description: str,
        workspace_id: str,
        created_by: str,
        cover_image: str = None,
        tags: list[str] = None
    ) -> str:
        cid = _generate_id()
        tags_json = json.dumps(tags or [])
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO collections (id, name, description, workspace_id, created_by, cover_image, tags)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (cid, name, description, workspace_id, created_by, cover_image, tags_json)
            )
        return cid

    def get_collection(self, collection_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM collections WHERE id = ?", (collection_id,)
            ).fetchone()
            if not row:
                return None
            coll = dict(row)
            coll["tags"] = json.loads(coll["tags"])

            items = conn.execute(
                "SELECT * FROM collection_items WHERE collection_id = ? ORDER BY item_order ASC, added_at ASC",
                (collection_id,)
            ).fetchall()
            coll["items"] = [dict(i) for i in items]

            conn.execute(
                "UPDATE collections SET view_count = view_count + 1 WHERE id = ?",
                (collection_id,)
            )
            return coll

    def update_collection(self, collection_id: str, **kwargs) -> bool:
        allowed = {"name", "description", "cover_image", "tags"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "tags" in updates:
            updates["tags"] = json.dumps(updates["tags"])

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [datetime.now(timezone.utc).isoformat(), collection_id]

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE collections SET {set_clause}, updated_at = ? WHERE id = ?",
                values
            )
            return True

    def delete_collection(self, collection_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM collection_items WHERE collection_id = ?", (collection_id,))
            cur = conn.execute("DELETE FROM collections WHERE id = ?", (collection_id,))
            return cur.rowcount > 0

    def list_collections(
        self,
        workspace_id: str = None,
        created_by: str = None,
        tag: str = None
    ) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            conditions = []
            params = []

            if workspace_id:
                conditions.append("workspace_id = ?")
                params.append(workspace_id)
            if created_by:
                conditions.append("created_by = ?")
                params.append(created_by)
            if tag:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

            where = ""
            if conditions:
                where = "WHERE " + " AND ".join(conditions)

            rows = conn.execute(
                f"SELECT * FROM collections {where} ORDER BY updated_at DESC",
                params
            ).fetchall()

            result = []
            for r in rows:
                d = dict(r)
                d["tags"] = json.loads(d["tags"])
                result.append(d)
            return result

    def add_item(
        self,
        collection_id: str,
        content_id: str,
        added_by: str,
        note: str = None,
        order: int = None
    ) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            if order is None:
                row = conn.execute(
                    "SELECT COALESCE(MAX(item_order), -1) + 1 as nxt FROM collection_items WHERE collection_id = ?",
                    (collection_id,)
                ).fetchone()
                order = row[0]

            try:
                conn.execute(
                    "INSERT INTO collection_items (collection_id, content_id, added_by, note, item_order) VALUES (?, ?, ?, ?, ?)",
                    (collection_id, content_id, added_by, note, order)
                )
                conn.execute(
                    "UPDATE collections SET item_count = (SELECT COUNT(*) FROM collection_items WHERE collection_id = ?), updated_at = ? WHERE id = ?",
                    (collection_id, datetime.now(timezone.utc).isoformat(), collection_id)
                )
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_item(self, collection_id: str, content_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM collection_items WHERE collection_id = ? AND content_id = ?",
                (collection_id, content_id)
            )
            if cur.rowcount > 0:
                conn.execute(
                    "UPDATE collections SET item_count = (SELECT COUNT(*) FROM collection_items WHERE collection_id = ?), updated_at = ? WHERE id = ?",
                    (collection_id, datetime.now(timezone.utc).isoformat(), collection_id)
                )
                return True
            return False

    def reorder_items(self, collection_id: str, content_ids: list[str]) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            for idx, cid in enumerate(content_ids):
                conn.execute(
                    "UPDATE collection_items SET item_order = ? WHERE collection_id = ? AND content_id = ?",
                    (idx, collection_id, cid)
                )
            conn.execute(
                "UPDATE collections SET updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), collection_id)
            )
            return True

    def get_collection_items(self, collection_id: str, page: int = 1, page_size: int = 20) -> dict:
        offset = (page - 1) * page_size
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM collection_items WHERE collection_id = ? ORDER BY item_order ASC, added_at ASC LIMIT ? OFFSET ?",
                (collection_id, page_size, offset)
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM collection_items WHERE collection_id = ?",
                (collection_id,)
            ).fetchone()[0]

            return {
                "items": [dict(r) for r in rows],
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": max(1, (total + page_size - 1) // page_size)
            }

    def search_collections(self, query: str, workspace_id: str = None, limit: int = 10) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            like = f"%{query}%"
            if workspace_id:
                rows = conn.execute(
                    """SELECT * FROM collections
                       WHERE workspace_id = ? AND (name LIKE ? OR description LIKE ?)
                       ORDER BY updated_at DESC LIMIT ?""",
                    (workspace_id, like, like, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM collections WHERE name LIKE ? OR description LIKE ? ORDER BY updated_at DESC LIMIT ?",
                    (like, like, limit)
                ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d["tags"] = json.loads(d["tags"])
                result.append(d)
            return result

    def share_collection(self, collection_id: str, expires_in_hours: int = 168) -> str:
        share_code = _generate_id(20)
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE collections SET share_code = ? WHERE id = ?",
                (share_code, collection_id)
            )
        return share_code

    def get_collection_stats(self, collection_id: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM collections WHERE id = ?", (collection_id,)).fetchone()
            if not row:
                return None

            unique_sources = conn.execute(
                "SELECT COUNT(DISTINCT content_id) as cnt FROM collection_items WHERE collection_id = ?",
                (collection_id,)
            ).fetchone()[0]

            return {
                "collection_id": collection_id,
                "name": row[1],
                "item_count": row[7],
                "view_count": row[8],
                "unique_content_sources": unique_sources,
                "last_updated": row[11]
            }

"""Saved search alerts and monitoring."""

from __future__ import annotations

from ..core.models import ContentItem
from ..storage.sql_store import SQLStore
from .faceted_search import FacetedSearch
from datetime import datetime, timedelta
import json
import os
import uuid


class SavedSearch:
    def __init__(self, db_path: str = None, sql_store=None):
        self.sql_store = sql_store or SQLStore()
        self.faceted_search = FacetedSearch(sql_store=self.sql_store)
        self.db_path = db_path or getattr(self.sql_store, "db_path", "./data/search.db")
        self._init_tables()

    def _init_tables(self):
        with self.sql_store._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS saved_searches (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    query TEXT DEFAULT '',
                    facets TEXT DEFAULT '{}',
                    user TEXT DEFAULT '',
                    notify_on_new INTEGER DEFAULT 1,
                    frequency TEXT DEFAULT 'daily',
                    active INTEGER DEFAULT 1,
                    last_run_at TEXT,
                    last_check_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS search_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id TEXT,
                    item_id TEXT,
                    matched_at TEXT,
                    notified INTEGER DEFAULT 0,
                    FOREIGN KEY (search_id) REFERENCES saved_searches(id)
                );
                CREATE INDEX IF NOT EXISTS idx_search_results_search_id ON search_results(search_id);
                CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user);
            """)

    def create(self, name: str, query: str = "", facets: dict = None, user: str = None,
               notify_on_new: bool = True, frequency: str = "daily") -> dict:
        search_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self.sql_store._conn() as conn:
            conn.execute("""
                INSERT INTO saved_searches (id, name, query, facets, user, notify_on_new, frequency, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (search_id, name, query, json.dumps(facets or {}), user or "",
                  int(notify_on_new), frequency, now, now))
        return self._get_by_id(search_id)

    def update(self, search_id: str, **kwargs) -> bool:
        allowed = {"name", "query", "facets", "user", "notify_on_new", "frequency", "active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return False

        if "facets" in updates and isinstance(updates["facets"], dict):
            updates["facets"] = json.dumps(updates["facets"])
        if "notify_on_new" in updates:
            updates["notify_on_new"] = int(updates["notify_on_new"])

        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [search_id]

        with self.sql_store._conn() as conn:
            conn.execute(f"UPDATE saved_searches SET {set_clause} WHERE id = ?", values)
            return conn.rowcount > 0

    def delete(self, search_id: str) -> bool:
        with self.sql_store._conn() as conn:
            conn.execute("DELETE FROM saved_searches WHERE id = ?", (search_id,))
            conn.execute("DELETE FROM search_results WHERE search_id = ?", (search_id,))
            return conn.rowcount > 0

    def list(self, user: str = None) -> list[dict]:
        with self.sql_store._conn() as conn:
            if user:
                rows = conn.execute("SELECT * FROM saved_searches WHERE user = ? ORDER BY created_at DESC", (user,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM saved_searches ORDER BY created_at DESC").fetchall()
        return [self._row_to_dict(r) for r in rows]

    def execute(self, search_id: str) -> dict:
        saved = self._get_by_id(search_id)
        if not saved:
            return {"error": "Saved search not found", "results": []}

        facets = json.loads(saved["facets"]) if isinstance(saved["facets"], str) else (saved.get("facets") or {})
        results = self.faceted_search.search(
            query=saved["query"],
            facets=facets,
            page=1,
            page_size=100,
        )

        now = datetime.now().isoformat()
        with self.sql_store._conn() as conn:
            conn.execute("UPDATE saved_searches SET last_run_at = ? WHERE id = ?", (now, search_id))

        results["saved_search_id"] = search_id
        results["saved_search_name"] = saved["name"]
        return results

    def execute_all(self) -> dict[str, dict]:
        all_searches = self.list()
        results = {}
        for s in all_searches:
            if s.get("active", 1):
                results[s["id"]] = self.execute(s["id"])
        return results

    def check_for_new(self, search_id: str, since: datetime = None) -> list[dict]:
        saved = self._get_by_id(search_id)
        if not saved:
            return []

        if since is None:
            since_str = saved.get("last_check_at") or saved.get("last_run_at") or (datetime.now() - timedelta(days=1)).isoformat()
        else:
            since_str = since.isoformat()

        facets = json.loads(saved["facets"]) if isinstance(saved["facets"], str) else (saved.get("facets") or {})
        full_results = self.faceted_search.search(
            query=saved["query"],
            facets=facets,
            page=1,
            page_size=200,
        )

        new_items = []
        existing_ids = set()
        with self.sql_store._conn() as conn:
            existing = conn.execute("SELECT item_id FROM search_results WHERE search_id = ?", (search_id,)).fetchall()
            existing_ids = {r[0] for r in existing}

        for item in full_results.get("results", []):
            item_id = item.get("id", "")
            if item_id and item_id not in existing_ids:
                published = item.get("published_at", "")
                if published and since_str and published >= since_str[:10]:
                    new_items.append(item)

        now = datetime.now().isoformat()
        with self.sql_store._conn() as conn:
            for item in new_items:
                conn.execute("""
                    INSERT OR IGNORE INTO search_results (search_id, item_id, matched_at)
                    VALUES (?, ?, ?)
                """, (search_id, item.get("id", ""), now))
            conn.execute("UPDATE saved_searches SET last_check_at = ? WHERE id = ?", (now, search_id))

        return new_items

    def get_new_items_count(self, search_id: str) -> int:
        saved = self._get_by_id(search_id)
        if not saved:
            return 0
        since = saved.get("last_check_at") or saved.get("last_run_at") or (datetime.now() - timedelta(days=1)).isoformat()
        count = 0
        with self.sql_store._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM search_results WHERE search_id = ? AND matched_at >= ?",
                (search_id, since)
            ).fetchone()[0]
        return count + len(self.check_for_new(search_id))

    def run_and_notify(self, search_id: str, notifiers: list = None):
        new_items = self.check_for_new(search_id)
        if not new_items:
            return {"notified": False, "new_count": 0}

        saved = self._get_by_id(search_id)
        if not saved or not saved.get("notify_on_new", 1):
            return {"notified": False, "new_count": len(new_items)}

        if notifiers:
            from ..notifications.base import NotificationManager
            manager = NotificationManager(notifiers)
            message = f"New results for saved search '{saved['name']}': {len(new_items)} new item(s)"
            manager.send(message)

        with self.sql_store._conn() as conn:
            for item in new_items:
                conn.execute(
                    "UPDATE search_results SET notified = 1 WHERE search_id = ? AND item_id = ?",
                    (search_id, item.get("id", ""))
                )

        return {"notified": True, "new_count": len(new_items), "items": new_items}

    def get_stats(self) -> dict:
        with self.sql_store._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM saved_searches").fetchone()[0]
            active = conn.execute("SELECT COUNT(*) FROM saved_searches WHERE active = 1").fetchone()[0]
            last_run = conn.execute("SELECT MAX(last_run_at) FROM saved_searches").fetchone()[0]
            total_matches = conn.execute("SELECT COUNT(*) FROM search_results").fetchone()[0]
        return {
            "total": total,
            "active": active,
            "last_run": last_run or "never",
            "total_matches": total_matches,
        }

    def _get_by_id(self, search_id: str) -> dict:
        with self.sql_store._conn() as conn:
            row = conn.execute("SELECT * FROM saved_searches WHERE id = ?", (search_id,)).fetchone()
        return self._row_to_dict(row) if row else None

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        keys = ["id", "name", "query", "facets", "user", "notify_on_new", "frequency",
                "active", "last_run_at", "last_check_at", "created_at", "updated_at"]
        d = {}
        for i, k in enumerate(keys):
            d[k] = row[i] if i < len(row) else None
        if isinstance(d.get("facets"), str):
            try:
                d["facets"] = json.loads(d["facets"])
            except json.JSONDecodeError:
                pass
        d["notify_on_new"] = bool(d.get("notify_on_new", 1))
        d["active"] = bool(d.get("active", 1))
        return d

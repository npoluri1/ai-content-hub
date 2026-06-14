import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from pipeline.core.models import ContentItem

logger = logging.getLogger(__name__)


class LegalHoldManager:
    def __init__(self, db_path: str = "./data/legal_holds.db"):
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS legal_holds (
                    id TEXT PRIMARY KEY,
                    matter_name TEXT NOT NULL,
                    description TEXT,
                    custodian TEXT NOT NULL,
                    criteria TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    released_at TEXT,
                    release_reason TEXT
                );
                CREATE TABLE IF NOT EXISTS preserved_content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hold_id TEXT NOT NULL,
                    content_item_id TEXT NOT NULL,
                    content_snapshot TEXT NOT NULL,
                    preserved_at TEXT NOT NULL,
                    FOREIGN KEY (hold_id) REFERENCES legal_holds(id)
                );
                CREATE INDEX IF NOT EXISTS idx_preserved_hold ON preserved_content(hold_id);
                CREATE INDEX IF NOT EXISTS idx_legal_holds_status ON legal_holds(status);
            """)

    def place_hold(self, matter_name: str, description: str, custodian: str, criteria: dict, created_by: str) -> str:
        hold_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO legal_holds (id, matter_name, description, custodian, criteria, status, created_by, created_at)
                       VALUES (?, ?, ?, ?, ?, 'active', ?, ?)""",
                    (hold_id, matter_name, description, custodian, json.dumps(criteria), created_by, now),
                )
            logger.info(f"Legal hold placed: {hold_id} for matter '{matter_name}'")
            return hold_id
        except Exception as e:
            logger.error(f"Failed to place legal hold: {e}")
            raise

    def release_hold(self, hold_id: str, reason: str) -> bool:
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            cur = conn.execute(
                "UPDATE legal_holds SET status = 'released', released_at = ?, release_reason = ? WHERE id = ? AND status = 'active'",
                (now, reason, hold_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                logger.warning(f"Hold {hold_id} not found or already released")
                return False
        logger.info(f"Legal hold released: {hold_id} reason: {reason}")
        return True

    def get_hold(self, hold_id: str) -> dict:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM legal_holds WHERE id = ?", (hold_id,)).fetchone()
        if not row:
            return {}
        result = dict(row)
        result["criteria"] = json.loads(result["criteria"])
        return result

    def list_holds(self, status: str = None) -> list[dict]:
        with self._get_conn() as conn:
            if status:
                rows = conn.execute("SELECT * FROM legal_holds WHERE status = ? ORDER BY created_at DESC", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM legal_holds ORDER BY created_at DESC").fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["criteria"] = json.loads(d["criteria"])
            results.append(d)
        return results

    def check_content(self, hold_id: str, items: list[ContentItem]) -> list[str]:
        hold = self.get_hold(hold_id)
        if not hold or hold["status"] != "active":
            return []

        criteria = hold["criteria"]
        matching_ids = []

        for item in items:
            if self._matches_criteria(item, criteria):
                matching_ids.append(item.id)

        return matching_ids

    @staticmethod
    def _matches_criteria(item: ContentItem, criteria: dict) -> bool:
        keywords = criteria.get("keywords", [])
        sources = criteria.get("sources", [])
        topics = criteria.get("topics", [])
        authors = criteria.get("authors", [])
        domains = criteria.get("domains", [])
        date_from = criteria.get("date_from")
        date_to = criteria.get("date_to")

        text = f"{item.title} {item.content} {item.source}".lower()

        if keywords:
            if not any(kw.lower() in text for kw in keywords):
                return False

        if sources:
            if item.source not in sources:
                return False

        if topics:
            item_topics_lower = [t.lower() for t in item.topics]
            if not any(t.lower() in item_topics_lower for t in topics):
                return False

        if authors:
            if item.author_name not in authors:
                return False

        if domains:
            if not any(d in item.url for d in domains):
                return False

        if date_from or date_to:
            if item.published_at:
                if date_from and item.published_at.isoformat() < date_from:
                    return False
                if date_to and item.published_at.isoformat() > date_to:
                    return False

        return True

    def preserve_content(self, hold_id: str, items: list[ContentItem]) -> int:
        hold = self.get_hold(hold_id)
        if not hold or hold["status"] != "active":
            logger.warning(f"Cannot preserve: hold {hold_id} not active")
            return 0

        now = datetime.utcnow().isoformat()
        preserved_count = 0

        with self._get_conn() as conn:
            for item in items:
                snapshot = json.dumps(item.model_dump() if hasattr(item, "model_dump") else item.__dict__, default=str)
                try:
                    conn.execute(
                        "INSERT OR IGNORE INTO preserved_content (hold_id, content_item_id, content_snapshot, preserved_at) VALUES (?, ?, ?, ?)",
                        (hold_id, item.id, snapshot, now),
                    )
                    preserved_count += 1
                except Exception:
                    continue
            conn.commit()

        logger.info(f"Preserved {preserved_count} items for hold {hold_id}")
        return preserved_count

    def export_for_ediscovery(self, hold_id: str, format: str = "json") -> str:
        hold = self.get_hold(hold_id)
        if not hold:
            return json.dumps({"error": "Hold not found"})

        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM preserved_content WHERE hold_id = ?", (hold_id,)
            ).fetchall()

        preserved = []
        for r in rows:
            d = dict(r)
            d["content_snapshot"] = json.loads(d["content_snapshot"])
            preserved.append(d)

        export = {
            "exported_at": datetime.utcnow().isoformat(),
            "hold": hold,
            "preserved_count": len(preserved),
            "preserved_items": preserved,
        }

        if format == "json":
            return json.dumps(export, indent=2, default=str)
        return json.dumps(export, indent=2, default=str)

    def get_preserved_count(self, hold_id: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM preserved_content WHERE hold_id = ?", (hold_id,)
            ).fetchone()
        return row["cnt"] if row else 0

    def generate_hold_report(self, hold_id: str) -> str:
        hold = self.get_hold(hold_id)
        if not hold:
            return json.dumps({"error": "Hold not found"})

        preserved_count = self.get_preserved_count(hold_id)

        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "hold_id": hold_id,
            "matter_name": hold["matter_name"],
            "status": hold["status"],
            "custodian": hold["custodian"],
            "created_by": hold["created_by"],
            "created_at": hold["created_at"],
            "released_at": hold.get("released_at"),
            "release_reason": hold.get("release_reason"),
            "criteria": hold["criteria"],
            "preserved_item_count": preserved_count,
            "compliance_status": "active" if hold["status"] == "active" else "released",
        }

        return json.dumps(report, indent=2, default=str)

"""Search result boosting rules — temporal, source authority, engagement, freshness."""

import json
import math
import os
import sqlite3
import uuid
from datetime import datetime, timedelta


class SearchBoosting:
    def __init__(self, db_path: str = "./data/boosting.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()
        self._source_authority_defaults = {
            "arxiv.org": 1.5, "arxiv": 1.5,
            "techcrunch": 1.3, "techcrunch.com": 1.3,
            "linkedin": 1.1, "linkedin.com": 1.1,
            "github": 1.2, "github.com": 1.2,
            "reddit": 0.9, "reddit.com": 0.9,
            "medium": 1.0, "medium.com": 1.0,
            "twitter": 0.9, "x.com": 0.9,
            "youtube": 1.0, "youtube.com": 1.0,
        }

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS boost_rules (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    field TEXT NOT NULL,
                    value TEXT NOT NULL,
                    boost_factor REAL NOT NULL,
                    scope TEXT DEFAULT 'global',
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS boost_impact_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT,
                    query TEXT,
                    position_change REAL,
                    items_affected INTEGER,
                    applied_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_boost_rules_scope ON boost_rules(scope);
                CREATE INDEX IF NOT EXISTS idx_boost_rules_field ON boost_rules(field);
                CREATE INDEX IF NOT EXISTS idx_boost_impact_rule ON boost_impact_log(rule_id);
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def add_boost_rule(self, name: str, field: str, value: str,
                       boost_factor: float, scope: str = "global") -> str:
        rule_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO boost_rules (id, name, field, value, boost_factor, scope, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (rule_id, name, field, value, boost_factor, scope, now, now))
        return rule_id

    def remove_boost_rule(self, rule_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM boost_rules WHERE id = ?", (rule_id,))
            return conn.rowcount > 0

    def list_rules(self, scope: str = None) -> list[dict]:
        with self._conn() as conn:
            if scope:
                rows = conn.execute(
                    "SELECT * FROM boost_rules WHERE scope = ? ORDER BY created_at DESC",
                    (scope,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM boost_rules ORDER BY created_at DESC"
                ).fetchall()
        return [dict(zip(["id", "name", "field", "value", "boost_factor", "scope", "created_at", "updated_at"], r)) for r in rows]

    def apply_boosts(self, query: str, results: list[dict], context: dict = None) -> list[dict]:
        if not results:
            return results

        rules = self.list_rules()
        context = context or {}
        max_score = max((r.get("_score", r.get("relevance_score", 0)) for r in results), default=1)
        if max_score <= 0:
            max_score = 1

        for item in results:
            base_score = item.get("_score", item.get("relevance_score", 0))
            boosted = base_score
            for rule in rules:
                field_val = str(item.get(rule["field"], "")).lower()
                if rule["value"].lower() in field_val:
                    if rule["scope"] == "global" or rule["scope"] == context.get("scope", "global"):
                        boosted *= rule["boost_factor"]
            item["_boosted_score"] = boosted
            item["_score"] = boosted

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results

    def apply_temporal_boost(self, results: list[dict]) -> list[dict]:
        now = datetime.now()
        for item in results:
            pub = item.get("published_at", "")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split(".")[0].replace("T", " "))
                    hours_ago = (now - dt).total_seconds() / 3600
                    decay = max(0.1, 1.0 - (hours_ago / 720))
                    item["_score"] = item.get("_score", 0) * decay
                except (ValueError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results

    def apply_source_authority(self, results: list[dict]) -> list[dict]:
        for item in results:
            source = str(item.get("source", "")).lower()
            url = str(item.get("url", "")).lower()
            authority = 1.0
            for key, factor in self._source_authority_defaults.items():
                if key in source or key in url:
                    authority = max(authority, factor)
            item["_score"] = item.get("_score", 0) * authority
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results

    def apply_engagement_boost(self, results: list[dict]) -> list[dict]:
        for item in results:
            engagement = int(item.get("engagement", 0) or 0)
            boost = math.log(engagement + 1) * 0.1
            item["_score"] = item.get("_score", 0) + boost
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results

    def apply_freshness_boost(self, results: list[dict], max_hours: int = 72) -> list[dict]:
        now = datetime.now()
        for item in results:
            pub = item.get("published_at", "")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split(".")[0].replace("T", " "))
                    hours_ago = (now - dt).total_seconds() / 3600
                    if hours_ago <= 24:
                        freshness = 1.0
                    elif hours_ago >= max_hours:
                        freshness = 0.0
                    else:
                        freshness = 1.0 - ((hours_ago - 24) / (max_hours - 24))
                    item["_score"] = item.get("_score", 0) * (1 + freshness * 0.5)
                except (ValueError, TypeError):
                    pass
        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return results

    def create_decay_function(self, field: str, max_value: float, decay_rate: float):
        def decay(item: dict) -> float:
            val = float(item.get(field, 0) or 0)
            return max_value * math.exp(-decay_rate * val)
        return decay

    def get_active_boost_count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM boost_rules").fetchone()[0]

    def get_boost_impact(self, rule_id: str, days: int = 7) -> dict:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT COUNT(*) as times_applied,
                       AVG(position_change) as avg_pos_change,
                       SUM(items_affected) as total_items
                FROM boost_impact_log
                WHERE rule_id = ? AND applied_at >= ?
            """, (rule_id, since)).fetchone()
            recent = conn.execute("""
                SELECT query, position_change, items_affected, applied_at
                FROM boost_impact_log
                WHERE rule_id = ?
                ORDER BY applied_at DESC
                LIMIT 10
            """, (rule_id,)).fetchall()
        return {
            "rule_id": rule_id,
            "times_applied": rows[0] or 0,
            "avg_position_change": round(rows[1], 2) if rows[1] else 0.0,
            "total_items_affected": rows[2] or 0,
            "recent_applications": [
                {"query": r[0], "position_change": r[1], "items_affected": r[2], "applied_at": r[3]}
                for r in recent
            ],
        }

    def _log_impact(self, rule_id: str, query: str, position_change: float, items_affected: int):
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO boost_impact_log (rule_id, query, position_change, items_affected, applied_at)
                VALUES (?, ?, ?, ?, ?)
            """, (rule_id, query, position_change, items_affected, datetime.now().isoformat()))

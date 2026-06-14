import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 90


class DataRetention:
    def __init__(self, sql_store=None, vector_store=None, db_path: str = "./data/retention.db"):
        self.db_path = db_path
        self.sql_store = sql_store
        self.vector_store = vector_store
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS policies (
                    source TEXT PRIMARY KEY,
                    retention_days INTEGER NOT NULL DEFAULT 90,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)

    def set_policy(self, source: str, retention_days: int):
        now = datetime.utcnow().isoformat()
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO policies (source, retention_days, created_at, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(source) DO UPDATE SET
                       retention_days = excluded.retention_days,
                       updated_at = excluded.updated_at""",
                (source, retention_days, now, now),
            )
        logger.info(f"Retention policy set: {source} = {retention_days} days")

    def get_policy(self, source: str) -> int:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT retention_days FROM policies WHERE source = ?", (source,)
            ).fetchone()
        return row["retention_days"] if row else DEFAULT_RETENTION_DAYS

    def list_policies(self) -> dict[str, int]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT source, retention_days FROM policies").fetchall()
        return {r["source"]: r["retention_days"] for r in rows}

    def _get_all_sources(self) -> list[str]:
        policies = self.list_policies()
        sources = list(policies.keys())
        return sources if sources else ["default"]

    def enforce_policies(self, dry_run: bool = False) -> dict:
        policies = self.list_policies()
        if not policies:
            policies = {"default": DEFAULT_RETENTION_DAYS}

        cutoff = datetime.utcnow()
        per_source: dict[str, int] = {}
        total_deleted = 0

        for source, days in policies.items():
            threshold = cutoff - timedelta(days=days)
            threshold_str = threshold.isoformat()
            deleted_count = 0

            if self.sql_store:
                table_map = {
                    "linkedin": "linkedin_posts",
                    "reddit": "reddit_posts",
                    "news": "news_articles",
                    "default": "processed_items",
                }
                table = table_map.get(source, "processed_items")
                count_sql = f"SELECT COUNT(*) FROM {table} WHERE crawled_at < ?"
                del_sql = f"DELETE FROM {table} WHERE crawled_at < ?"
                try:
                    with self.sql_store._get_conn() as conn:
                        if dry_run:
                            deleted_count = conn.execute(count_sql, (threshold_str,)).fetchone()[0]
                        else:
                            deleted_count = conn.execute(del_sql, (threshold_str,)).rowcount
                            conn.commit()
                except Exception as e:
                    logger.warning(f"Could not enforce on sql_store.{table}: {e}")

            if self.vector_store:
                try:
                    ids_to_delete = self.vector_store.list_ids_before(threshold)
                    if not dry_run:
                        for vid in ids_to_delete:
                            self.vector_store.delete(vid)
                    deleted_count += len(ids_to_delete)
                except Exception as e:
                    logger.warning(f"Could not enforce on vector_store: {e}")

            per_source[source] = deleted_count
            total_deleted += deleted_count

        result = {
            "deleted": total_deleted,
            "dry_run": dry_run,
            "per_source": per_source,
        }
        if not dry_run:
            logger.info(f"Retention enforced: deleted {total_deleted} items")
        return result

    def archive_before(self, days: int, archive_dir: str = "./data/archive") -> dict:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        os.makedirs(archive_dir, exist_ok=True)
        archived_count = 0
        archive_files = []

        if self.sql_store:
            table_map = {
                "linkedin": "linkedin_posts",
                "reddit": "reddit_posts",
                "news": "news_articles",
            }
            for source, table in table_map.items():
                try:
                    with self.sql_store._get_conn() as conn:
                        conn.row_factory = sqlite3.Row
                        rows = conn.execute(
                            f"SELECT * FROM {table} WHERE crawled_at < ?", (cutoff,)
                        ).fetchall()
                        if rows:
                            data = [dict(r) for r in rows]
                            archive_file = os.path.join(archive_dir, f"{source}_{days}d_{datetime.utcnow().strftime('%Y%m%d')}.json")
                            with open(archive_file, "w") as f:
                                json.dump(data, f, indent=2, default=str)
                            conn.execute(f"DELETE FROM {table} WHERE crawled_at < ?", (cutoff,))
                            conn.commit()
                            archived_count += len(data)
                            archive_files.append(archive_file)
                except Exception as e:
                    logger.warning(f"Archive failed for {table}: {e}")

        return {
            "archived_count": archived_count,
            "archive_files": archive_files,
            "archive_dir": archive_dir,
        }

    def restore_archive(self, archive_file: str) -> int:
        if not os.path.exists(archive_file):
            logger.error(f"Archive file not found: {archive_file}")
            return 0
        with open(archive_file, "r") as f:
            items = json.load(f)
        if not items or not self.sql_store:
            return 0

        table_map = {"linkedin": "linkedin_posts", "reddit": "reddit_posts", "news": "news_articles"}
        source_from_file = os.path.basename(archive_file).split("_")[0]
        table = table_map.get(source_from_file, "processed_items")

        restored = 0
        try:
            with self.sql_store._get_conn() as conn:
                for item in items:
                    placeholders = ", ".join(["?"] * len(item))
                    columns = ", ".join(item.keys())
                    try:
                        conn.execute(
                            f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})",
                            list(item.values()),
                        )
                        restored += 1
                    except Exception:
                        pass
                conn.commit()
        except Exception as e:
            logger.error(f"Restore failed: {e}")
        return restored

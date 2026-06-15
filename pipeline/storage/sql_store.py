"""SQLite store — metadata, search, dedup, and scheduling state."""

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem
import sqlite3
import os
from datetime import datetime


class SQLStore:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQL_DB_PATH
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    content_cleaned TEXT,
                    url TEXT,
                    source TEXT,
                    source_type TEXT,
                    author_name TEXT,
                    author_url TEXT,
                    published_at TEXT,
                    crawled_at TEXT,
                    hashtags TEXT,
                    topics TEXT,
                    relevance_score REAL,
                    engagement INTEGER,
                    image_urls TEXT,
                    video_url TEXT,
                    is_relevant INTEGER DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS sources (
                    name TEXT PRIMARY KEY,
                    last_crawl_at TEXT,
                    items_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'idle'
                );
                CREATE INDEX IF NOT EXISTS idx_items_source ON items(source);
                CREATE INDEX IF NOT EXISTS idx_items_topics ON items(topics);
                CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at);
                CREATE INDEX IF NOT EXISTS idx_items_relevance ON items(relevance_score);
                CREATE TABLE IF NOT EXISTS schedule_config (
                    source TEXT PRIMARY KEY,
                    interval_minutes INTEGER,
                    enabled INTEGER DEFAULT 1,
                    last_run_at TEXT
                );
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def store_items(self, items: list[ContentItem | ClassifiedItem]):
        with self._conn() as conn:
            for item in items:
                try:
                    conn.execute("""
                        INSERT OR IGNORE INTO items
                        (id, title, content, content_cleaned, url, source, source_type,
                         author_name, author_url, published_at, crawled_at,
                         hashtags, topics, relevance_score, engagement,
                         image_urls, video_url, is_relevant)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        item.id, item.title, item.content, item.content_cleaned,
                        item.url, item.source, item.source_type,
                        item.author_name, item.author_url,
                        item.published_at.isoformat() if item.published_at else None,
                        item.crawled_at.isoformat(),
                        ",".join(item.hashtags), ",".join(item.topics),
                        item.relevance_score, item.engagement,
                        ",".join(item.image_urls), item.video_url,
                        1 if isinstance(item, ClassifiedItem) and item.is_relevant else 1,
                    ))
                except Exception as e:
                    print(f"  [SQL] Error storing {item.id}: {e}")

    def search(self, query: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT title, content_cleaned, url, source, topics, author_name,
                       published_at, engagement, relevance_score
                FROM items
                WHERE content_cleaned LIKE ? OR title LIKE ? OR topics LIKE ?
                ORDER BY relevance_score DESC, engagement DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
        return [dict(zip(["title", "content", "url", "source", "topics", "author", "published_at", "engagement", "relevance"], r)) for r in rows]

    def get_by_source(self, source: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT title, content_cleaned, url, source, topics, author_name,
                       published_at, engagement, relevance_score
                FROM items WHERE source = ?
                ORDER BY published_at DESC
                LIMIT ?
            """, (source, limit)).fetchall()
        return [dict(zip(["title", "content", "url", "source", "topics", "author", "published_at", "engagement", "relevance"], r)) for r in rows]

    def get_by_topic(self, topic: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT title, content_cleaned, url, source, topics, author_name,
                       published_at, engagement, relevance_score
                FROM items WHERE topics LIKE ?
                ORDER BY relevance_score DESC
                LIMIT ?
            """, (f"%{topic}%", limit)).fetchall()
        return [dict(zip(["title", "content", "url", "source", "topics", "author", "published_at", "engagement", "relevance"], r)) for r in rows]

    def get_stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
            by_source = conn.execute("SELECT source, COUNT(*) FROM items GROUP BY source").fetchall()
            topics_raw = conn.execute("SELECT topics FROM items WHERE topics IS NOT NULL AND topics != ''").fetchall()
        by_topic: dict[str, int] = {}
        for (row,) in topics_raw:
            for t in row.split(","):
                t = t.strip()
                if t:
                    by_topic[t] = by_topic.get(t, 0) + 1
        return {
            "total": total,
            "by_source": dict(by_source),
            "by_topic": by_topic,
        }

    def update_source_crawl(self, source: str, count: int):
        with self._conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sources (name, last_crawl_at, items_count, status)
                VALUES (?, ?, ?, 'success')
            """, (source, datetime.now().isoformat(), count))

    def count(self) -> int:
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]

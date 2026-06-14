from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem
from typing import Optional
from datetime import datetime, timedelta
from ..storage.sql_store import SQLStore
import json
import os
import csv


class TrendAnalyzer:
    def __init__(self, sql_store=None):
        self.store = sql_store or SQLStore()

    def _fetchall(self, query, params=None):
        with self.store._conn() as conn:
            return conn.execute(query, params or []).fetchall()

    def topic_trend(self, topic: str, days: int = 30) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._fetchall("""
            SELECT DATE(published_at) as d, COUNT(*) as c
            FROM items
            WHERE topics LIKE ? AND published_at >= ?
            GROUP BY d ORDER BY d
        """, (f"%{topic}%", cutoff))
        return [{"date": r[0], "count": r[1]} for r in rows]

    def source_trend(self, source: str, days: int = 30) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._fetchall("""
            SELECT DATE(published_at) as d, COUNT(*) as c
            FROM items
            WHERE source = ? AND published_at >= ?
            GROUP BY d ORDER BY d
        """, (source, cutoff))
        return [{"date": r[0], "count": r[1]} for r in rows]

    def all_topics_trend(self, days: int = 30) -> dict[str, list[dict]]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._fetchall("""
            SELECT topics, DATE(published_at) as d, COUNT(*) as c
            FROM items
            WHERE published_at >= ?
            GROUP BY topics, d ORDER BY topics, d
        """, (cutoff,))
        result = {}
        for topic_str, date, count in rows:
            for t in topic_str.split(","):
                t = t.strip()
                if not t:
                    continue
                if t not in result:
                    result[t] = []
                result[t].append({"date": date, "count": count})
        return result

    def top_movers(self, days: int = 7) -> list[dict]:
        now = datetime.now()
        current_start = (now - timedelta(days=days)).isoformat()
        previous_start = (now - timedelta(days=2 * days)).isoformat()
        current_rows = self._fetchall("""
            SELECT topics, COUNT(*) as c
            FROM items
            WHERE published_at >= ? AND published_at < ?
            GROUP BY topics
        """, (current_start, now.isoformat()))
        previous_rows = self._fetchall("""
            SELECT topics, COUNT(*) as c
            FROM items
            WHERE published_at >= ? AND published_at < ?
            GROUP BY topics
        """, (previous_start, current_start))
        current_counts = {}
        for topics_str, count in current_rows:
            for t in topics_str.split(","):
                t = t.strip()
                if t:
                    current_counts[t] = current_counts.get(t, 0) + count
        previous_counts = {}
        for topics_str, count in previous_rows:
            for t in topics_str.split(","):
                t = t.strip()
                if t:
                    previous_counts[t] = previous_counts.get(t, 0) + count
        all_topics = set(current_counts.keys()) | set(previous_counts.keys())
        movers = []
        for topic in all_topics:
            curr = current_counts.get(topic, 0)
            prev = previous_counts.get(topic, 0)
            if prev == 0 and curr > 0:
                change_pct = 100.0
            elif prev == 0:
                change_pct = 0.0
            else:
                change_pct = round(((curr - prev) / prev) * 100, 1)
            movers.append({
                "topic": topic,
                "change_pct": change_pct,
                "current": curr,
                "previous": prev,
            })
        movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        return movers

    def peak_hours(self, source: str = None, days: int = 30) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        if source:
            rows = self._fetchall("""
                SELECT CAST(strftime('%H', published_at) AS INTEGER) as h, COUNT(*) as c
                FROM items
                WHERE source = ? AND published_at >= ?
                GROUP BY h ORDER BY h
            """, (source, cutoff))
        else:
            rows = self._fetchall("""
                SELECT CAST(strftime('%H', published_at) AS INTEGER) as h, COUNT(*) as c
                FROM items
                WHERE published_at >= ?
                GROUP BY h ORDER BY h
            """, (cutoff,))
        return [{"hour": r[0], "count": r[1]} for r in rows]

    def top_authors(self, topic: str = None, limit: int = 10, days: int = 30) -> list[dict]:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        if topic:
            rows = self._fetchall("""
                SELECT author_name, COUNT(*) as c, SUM(engagement) as total_eng
                FROM items
                WHERE topics LIKE ? AND published_at >= ? AND author_name != ''
                GROUP BY author_name
                ORDER BY c DESC LIMIT ?
            """, (f"%{topic}%", cutoff, limit))
        else:
            rows = self._fetchall("""
                SELECT author_name, COUNT(*) as c, SUM(engagement) as total_eng
                FROM items
                WHERE published_at >= ? AND author_name != ''
                GROUP BY author_name
                ORDER BY c DESC LIMIT ?
            """, (cutoff, limit))
        return [{"author": r[0], "count": r[1], "total_engagement": r[2] or 0} for r in rows]

    def engagement_analysis(self, days: int = 30) -> dict:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        by_source = self._fetchall("""
            SELECT source, AVG(engagement) as avg_eng, SUM(engagement) as total_eng, COUNT(*) as c
            FROM items WHERE published_at >= ?
            GROUP BY source ORDER BY avg_eng DESC
        """, (cutoff,))
        by_topic_raw = self._fetchall("""
            SELECT topics, AVG(engagement) as avg_eng, SUM(engagement) as total_eng, COUNT(*) as c
            FROM items WHERE published_at >= ?
            GROUP BY topics ORDER BY avg_eng DESC
        """, (cutoff,))
        by_topic = {}
        for topics_str, avg_eng, total_eng, c in by_topic_raw:
            for t in topics_str.split(","):
                t = t.strip()
                if t:
                    if t not in by_topic:
                        by_topic[t] = {"avg_engagement": 0.0, "total_engagement": 0, "count": 0}
                    existing = by_topic[t]
                    existing["avg_engagement"] = round(
                        (existing["avg_engagement"] * existing["count"] + avg_eng * c) / (existing["count"] + c), 1
                    ) if (existing["count"] + c) > 0 else 0.0
                    existing["total_engagement"] += total_eng
                    existing["count"] += c
        trend_rows = self._fetchall("""
            SELECT DATE(published_at) as d, AVG(engagement) as avg_eng, SUM(engagement) as total_eng
            FROM items WHERE published_at >= ?
            GROUP BY d ORDER BY d
        """, (cutoff,))
        return {
            "by_source": [
                {"source": r[0], "avg_engagement": round(r[1], 1), "total_engagement": r[2], "count": r[3]}
                for r in by_source
            ],
            "by_topic": by_topic,
            "trend": [{"date": r[0], "avg_engagement": round(r[1], 1), "total_engagement": r[2]} for r in trend_rows],
        }

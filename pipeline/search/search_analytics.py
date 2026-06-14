"""Search usage analytics — log queries, clicks, and generate reports."""

from datetime import datetime, timedelta
import json
import os
import sqlite3
import uuid


class SearchAnalytics:
    def __init__(self, db_path: str = "./data/search_analytics.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS search_logs (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    user TEXT,
                    results_count INTEGER DEFAULT 0,
                    facets TEXT DEFAULT '{}',
                    response_time_ms INTEGER DEFAULT 0,
                    timestamp TEXT
                );
                CREATE TABLE IF NOT EXISTS click_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_id TEXT,
                    result_id TEXT,
                    position INTEGER,
                    timestamp TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_search_logs_query ON search_logs(query);
                CREATE INDEX IF NOT EXISTS idx_search_logs_timestamp ON search_logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_search_logs_user ON search_logs(user);
                CREATE INDEX IF NOT EXISTS idx_click_logs_search_id ON click_logs(search_id);
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def log_search(self, query: str, user: str = None, results_count: int = 0,
                   facets: dict = None, response_time_ms: int = 0) -> None:
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO search_logs (id, query, user, results_count, facets, response_time_ms, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (log_id, query, user or "", results_count, json.dumps(facets or {}), response_time_ms, now))

    def log_click(self, search_id: str, result_id: str, position: int) -> None:
        now = datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute("""
                INSERT INTO click_logs (search_id, result_id, position, timestamp)
                VALUES (?, ?, ?, ?)
            """, (search_id, result_id, position, now))

    def get_popular_searches(self, limit: int = 20, days: int = 30) -> list[dict]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT query, COUNT(*) as search_count, AVG(results_count) as avg_results,
                       COUNT(CASE WHEN results_count = 0 THEN 1 END) as zero_result_count
                FROM search_logs
                WHERE timestamp >= ? AND query != ''
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT ?
            """, (since, limit)).fetchall()
        return [dict(zip(["query", "search_count", "avg_results", "zero_result_count"], r)) for r in rows]

    def get_zero_result_searches(self, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT query, COUNT(*) as search_count, MAX(timestamp) as last_searched
                FROM search_logs
                WHERE results_count = 0 AND query != ''
                GROUP BY query
                ORDER BY search_count DESC
                LIMIT ?
            """, (limit,)).fetchall()
        return [dict(zip(["query", "search_count", "last_searched"], r)) for r in rows]

    def get_search_trends(self, days: int = 30) -> list[dict]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as search_count,
                       AVG(results_count) as avg_results,
                       AVG(response_time_ms) as avg_response_time
                FROM search_logs
                WHERE timestamp >= ?
                GROUP BY DATE(timestamp)
                ORDER BY date ASC
            """, (since,)).fetchall()
        return [dict(zip(["date", "search_count", "avg_results", "avg_response_time"], r)) for r in rows]

    def get_user_search_activity(self, user: str, days: int = 30) -> dict:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM search_logs WHERE user = ? AND timestamp >= ?",
                (user, since)
            ).fetchone()[0]
            unique = conn.execute(
                "SELECT COUNT(DISTINCT query) FROM search_logs WHERE user = ? AND timestamp >= ? AND query != ''",
                (user, since)
            ).fetchone()[0]
            avg = conn.execute(
                "SELECT AVG(results_count) FROM search_logs WHERE user = ? AND timestamp >= ?",
                (user, since)
            ).fetchone()[0]
            top = conn.execute("""
                SELECT query, COUNT(*) as cnt FROM search_logs
                WHERE user = ? AND timestamp >= ? AND query != ''
                GROUP BY query ORDER BY cnt DESC LIMIT 10
            """, (user, since)).fetchall()
        return {
            "total_searches": total,
            "unique_queries": unique,
            "avg_results": round(avg, 1) if avg else 0,
            "top_searches": [dict(zip(["query", "count"], r)) for r in top],
        }

    def get_click_through_rate(self, days: int = 30) -> float:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            searches = conn.execute(
                "SELECT COUNT(*) FROM search_logs WHERE timestamp >= ? AND results_count > 0",
                (since,)
            ).fetchone()[0]
            clicks = conn.execute("""
                SELECT COUNT(*) FROM click_logs cl
                JOIN search_logs sl ON cl.search_id = sl.id
                WHERE sl.timestamp >= ?
            """, (since,)).fetchone()[0]
        if searches == 0:
            return 0.0
        return round(clicks / searches, 4)

    def get_top_facets_used(self, days: int = 30, limit: int = 10) -> list[dict]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        facet_counter = {}
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT facets FROM search_logs WHERE timestamp >= ? AND facets != '{}' AND facets != ''",
                (since,)
            ).fetchall()
        for row in rows:
            try:
                facets = json.loads(row[0])
                for key, values in facets.items():
                    if isinstance(values, list):
                        for v in values:
                            fkey = f"{key}:{v}"
                            facet_counter[fkey] = facet_counter.get(fkey, 0) + 1
                    else:
                        fkey = f"{key}:{values}"
                        facet_counter[fkey] = facet_counter.get(fkey, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        sorted_facets = sorted(facet_counter.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [{"facet": k, "count": v} for k, v in sorted_facets]

    def generate_report(self, days: int = 30, fmt: str = "json") -> str:
        report = {
            "report_period_days": days,
            "generated_at": datetime.now().isoformat(),
            "total_searches": 0,
            "unique_queries": 0,
            "zero_result_searches": 0,
            "avg_response_time_ms": 0,
            "click_through_rate": self.get_click_through_rate(days),
            "popular_searches": self.get_popular_searches(days=days),
            "zero_result_queries": self.get_zero_result_searches(),
            "search_trends": self.get_search_trends(days=days),
            "top_facets": self.get_top_facets_used(days=days),
        }

        since = (datetime.now() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            report["total_searches"] = conn.execute(
                "SELECT COUNT(*) FROM search_logs WHERE timestamp >= ?", (since,)
            ).fetchone()[0]
            report["unique_queries"] = conn.execute(
                "SELECT COUNT(DISTINCT query) FROM search_logs WHERE timestamp >= ? AND query != ''", (since,)
            ).fetchone()[0]
            report["zero_result_searches"] = conn.execute(
                "SELECT COUNT(*) FROM search_logs WHERE timestamp >= ? AND results_count = 0", (since,)
            ).fetchone()[0]
            avg_rt = conn.execute(
                "SELECT AVG(response_time_ms) FROM search_logs WHERE timestamp >= ?", (since,)
            ).fetchone()[0]
            report["avg_response_time_ms"] = round(avg_rt, 1) if avg_rt else 0

        if fmt == "json":
            return json.dumps(report, indent=2, default=str)
        else:
            lines = [
                f"Search Analytics Report ({days} days)",
                f"{'=' * 50}",
                f"Total Searches: {report['total_searches']}",
                f"Unique Queries: {report['unique_queries']}",
                f"Zero-Result Searches: {report['zero_result_searches']}",
                f"Avg Response Time: {report['avg_response_time_ms']}ms",
                f"Click-Through Rate: {report['click_through_rate'] * 100:.2f}%",
                "",
                "Popular Searches:",
            ]
            for s in report["popular_searches"][:10]:
                lines.append(f"  {s['query']} ({s['search_count']} searches)")
            lines.append("")
            lines.append("Search Trends:")
            for t in report["search_trends"][-7:]:
                lines.append(f"  {t['date']}: {t['search_count']} searches")
            return "\n".join(lines)

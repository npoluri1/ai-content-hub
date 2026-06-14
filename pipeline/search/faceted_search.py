"""Enterprise faceted search engine combining SQLite FTS + ChromaDB vector search."""

from ..core.models import ContentItem
from ..storage.sql_store import SQLStore
from ..storage.vector_store import VectorStore
from datetime import datetime, timedelta
import re


class FacetedSearch:
    def __init__(self, sql_store=None, vector_store=None):
        self.sql = sql_store or SQLStore()
        self.vector = vector_store or VectorStore()

    def search(self, query: str = "", facets: dict = None, page: int = 1, page_size: int = 20, sort: str = "relevance") -> dict:
        facets = facets or {}
        offset = (page - 1) * page_size

        sql_results = self._sql_search(query, facets, sort, offset, page_size)
        vector_results = self._vector_search(query, facets, page_size)

        merged = self._merge_results(sql_results, vector_results, query, facets, sort)
        total = self._count_results(query, facets)
        applied_facets = {k: v for k, v in facets.items() if v}

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": merged[offset:offset + page_size],
            "facets": self._compute_facets(query, facets),
            "applied_facets": applied_facets,
        }

    def search_sources(self, source_names: list[str], query: str = "", limit: int = 50) -> list[dict]:
        facets = {"source": source_names}
        result = self.search(query, facets=facets, page=1, page_size=limit)
        return result["results"]

    def search_topics(self, topic_names: list[str], query: str = "", limit: int = 50) -> list[dict]:
        facets = {"topics": topic_names}
        result = self.search(query, facets=facets, page=1, page_size=limit)
        return result["results"]

    def search_date_range(self, from_date: str, to_date: str, query: str = "", limit: int = 50) -> list[dict]:
        facets = {"date_from": from_date, "date_to": to_date}
        result = self.search(query, facets=facets, page=1, page_size=limit)
        return result["results"]

    def get_facet_options(self) -> dict:
        return self._compute_facets("", {})

    def autocomplete(self, partial: str, field: str = "title", limit: int = 10) -> list[str]:
        if not partial or len(partial) < 2:
            return []
        suggestions = set()
        with self.sql._conn() as conn:
            rows = conn.execute(f"""
                SELECT DISTINCT {field} FROM items
                WHERE {field} LIKE ? ORDER BY engagement DESC LIMIT ?
            """, (f"%{partial}%", limit * 3)).fetchall()
            for row in rows:
                text = row[0]
                for match in re.finditer(re.escape(partial), text, re.IGNORECASE):
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 30)
                    snippet = text[start:end].strip()
                    suggestions.add(snippet)
                    if len(suggestions) >= limit:
                        break
                if len(suggestions) >= limit:
                    break
        return list(suggestions)[:limit]

    def _sql_search(self, query: str, facets: dict, sort: str, offset: int, limit: int) -> list[dict]:
        where_clauses = []
        params = []

        if query:
            where_clauses.append("(content_cleaned LIKE ? OR title LIKE ? OR topics LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        if facets.get("source"):
            placeholders = ",".join("?" for _ in facets["source"])
            where_clauses.append(f"source IN ({placeholders})")
            params.extend(facets["source"])

        if facets.get("topics"):
            topic_clauses = []
            for t in facets["topics"]:
                topic_clauses.append("topics LIKE ?")
                params.append(f"%{t}%")
            where_clauses.append(f"({' OR '.join(topic_clauses)})")

        if facets.get("source_type"):
            if isinstance(facets["source_type"], list):
                placeholders = ",".join("?" for _ in facets["source_type"])
                where_clauses.append(f"source_type IN ({placeholders})")
                params.extend(facets["source_type"])
            else:
                where_clauses.append("source_type = ?")
                params.append(facets["source_type"])

        if facets.get("author"):
            where_clauses.append("author_name LIKE ?")
            params.append(f"%{facets['author']}%")

        if facets.get("date_from"):
            where_clauses.append("published_at >= ?")
            params.append(facets["date_from"])
        if facets.get("date_to"):
            where_clauses.append("published_at <= ?")
            params.append(facets["date_to"])

        order_map = {
            "relevance": "relevance_score DESC, engagement DESC",
            "date_desc": "published_at DESC",
            "date_asc": "published_at ASC",
            "engagement": "engagement DESC",
            "source": "source ASC, published_at DESC",
        }
        order_by = order_map.get(sort, "relevance_score DESC, engagement DESC")

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        with self.sql._conn() as conn:
            rows = conn.execute(f"""
                SELECT id, title, content_cleaned, url, source, source_type, topics, author_name,
                       published_at, engagement, relevance_score, hashtags, image_urls
                FROM items WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """, params + [limit, offset]).fetchall()
        return [dict(zip(
            ["id", "title", "content", "url", "source", "source_type", "topics", "author",
             "published_at", "engagement", "relevance_score", "hashtags", "image_urls"], r
        )) for r in rows]

    def _vector_search(self, query: str, facets: dict, limit: int) -> list[dict]:
        if not query:
            return []
        filter_source = None
        if facets.get("source") and len(facets["source"]) == 1:
            filter_source = facets["source"][0]
        return self.vector.search(query, n_results=limit, filter_source=filter_source)

    def _merge_results(self, sql_results: list, vector_results: list, query: str, facets: dict, sort: str) -> list[dict]:
        seen_ids = set()
        merged = []

        vector_ids = {r.get("id", r.get("url", "")) for r in vector_results}

        for r in sql_results:
            rid = r.get("id", r.get("url", ""))
            r["_match_type"] = "fts"
            r["_vector_score"] = 1.0 if rid in vector_ids else 0.0
            seen_ids.add(rid)
            merged.append(r)

        for r in vector_results:
            rid = r.get("id", "")
            if rid and rid not in seen_ids:
                seen_ids.add(rid)
                merged.append({
                    "id": rid,
                    "title": r.get("metadata", {}).get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("metadata", {}).get("url", ""),
                    "source": r.get("metadata", {}).get("source", ""),
                    "source_type": r.get("metadata", {}).get("source_type", ""),
                    "topics": r.get("metadata", {}).get("topics", "").split(",") if r.get("metadata", {}).get("topics") else [],
                    "author": r.get("metadata", {}).get("author", ""),
                    "published_at": r.get("metadata", {}).get("published_at", ""),
                    "engagement": int(r.get("metadata", {}).get("engagement", 0) or 0),
                    "relevance_score": 1.0 - float(r.get("distance", 0)),
                    "hashtags": [],
                    "image_urls": [],
                    "_match_type": "vector",
                    "_vector_score": 1.0 - float(r.get("distance", 0)),
                })

        if sort == "relevance":
            merged.sort(key=lambda x: (x.get("relevance_score", 0) + x.get("_vector_score", 0)) / 2, reverse=True)
        elif sort == "date_desc":
            merged.sort(key=lambda x: x.get("published_at", "") or "", reverse=True)
        elif sort == "date_asc":
            merged.sort(key=lambda x: x.get("published_at", "") or "")
        elif sort == "engagement":
            merged.sort(key=lambda x: x.get("engagement", 0) or 0, reverse=True)
        return merged

    def _count_results(self, query: str, facets: dict) -> int:
        where_clauses = []
        params = []

        if query:
            where_clauses.append("(content_cleaned LIKE ? OR title LIKE ? OR topics LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        if facets.get("source"):
            placeholders = ",".join("?" for _ in facets["source"])
            where_clauses.append(f"source IN ({placeholders})")
            params.extend(facets["source"])

        if facets.get("topics"):
            topic_clauses = []
            for t in facets["topics"]:
                topic_clauses.append("topics LIKE ?")
                params.append(f"%{t}%")
            where_clauses.append(f"({' OR '.join(topic_clauses)})")

        if facets.get("source_type"):
            if isinstance(facets["source_type"], list):
                placeholders = ",".join("?" for _ in facets["source_type"])
                where_clauses.append(f"source_type IN ({placeholders})")
                params.extend(facets["source_type"])
            else:
                where_clauses.append("source_type = ?")
                params.append(facets["source_type"])

        if facets.get("date_from"):
            where_clauses.append("published_at >= ?")
            params.append(facets["date_from"])
        if facets.get("date_to"):
            where_clauses.append("published_at <= ?")
            params.append(facets["date_to"])

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        with self.sql._conn() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM items WHERE {where_sql}", params).fetchone()[0]

    def _compute_facets(self, query: str, applied: dict) -> dict:
        base_clauses = []
        base_params = []

        if query:
            base_clauses.append("(content_cleaned LIKE ? OR title LIKE ? OR topics LIKE ?)")
            base_params.extend([f"%{query}%", f"%{query}%", f"%{query}%"])

        where_sql = " AND ".join(base_clauses) if base_clauses else "1=1"

        facets = {
            "sources": {},
            "topics": {},
            "date_ranges": {},
            "source_types": {},
            "authors": {},
        }

        with self.sql._conn() as conn:
            for row in conn.execute(f"SELECT source, COUNT(*) as cnt FROM items WHERE {where_sql} GROUP BY source ORDER BY cnt DESC LIMIT 20", base_params).fetchall():
                facets["sources"][row[0]] = row[1]

            types = conn.execute(f"SELECT source_type, COUNT(*) as cnt FROM items WHERE {where_sql} GROUP BY source_type ORDER BY cnt DESC", base_params).fetchall()
            for row in types:
                facets["source_types"][row[0]] = row[1]

            now = datetime.now()
            today_start = now.strftime("%Y-%m-%d")
            week_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            month_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")

            today_count = conn.execute(f"SELECT COUNT(*) FROM items WHERE {where_sql} AND published_at >= ?", base_params + [today_start]).fetchone()[0]
            week_count = conn.execute(f"SELECT COUNT(*) FROM items WHERE {where_sql} AND published_at >= ?", base_params + [week_start]).fetchone()[0]
            month_count = conn.execute(f"SELECT COUNT(*) FROM items WHERE {where_sql} AND published_at >= ?", base_params + [month_start]).fetchone()[0]

            facets["date_ranges"] = {"today": today_count, "this_week": week_count, "this_month": month_count}

            author_rows = conn.execute(f"SELECT author_name, COUNT(*) as cnt FROM items WHERE {where_sql} AND author_name != '' GROUP BY author_name ORDER BY cnt DESC LIMIT 20", base_params).fetchall()
            for row in author_rows:
                facets["authors"][row[0]] = row[1]

        return facets

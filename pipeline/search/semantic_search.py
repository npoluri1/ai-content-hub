"""Enhanced semantic search with tunable parameters — MMR, hybrid, boosting, reranking."""

from ..core.models import ContentItem
from ..storage.vector_store import VectorStore
from ..storage.sql_store import SQLStore
from datetime import datetime
import numpy as np
import re


class SemanticSearch:
    def __init__(self, vector_store=None, embedding_model: str = None):
        self.vector = vector_store or VectorStore()
        self.sql = SQLStore()
        self.embedding_model = embedding_model or "all-MiniLM-L6-v2"

    def search(self, query: str, n_results: int = 20, diversity: float = 0.0,
               threshold: float = 0.0, boost_factors: dict = None) -> list[dict]:
        results = self.vector.search(query, n_results=n_results * 2)
        parsed = []
        for r in results:
            score = 1.0 - float(r.get("distance", 0))
            if threshold > 0 and score < threshold:
                continue
            item = self._parse_result(r, score)
            parsed.append(item)

        if boost_factors:
            parsed = self._apply_boost_factors(parsed, boost_factors)

        if diversity > 0 and parsed:
            query_emb = self._get_embedding(query)
            parsed = self.max_marginal_relevance(query_emb, parsed, lambda_param=1.0 - diversity, n=n_results)

        parsed.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return parsed[:n_results]

    def hybrid_search(self, query: str, keywords: list[str] = None,
                      n_results: int = 20, alpha: float = 0.7) -> list[dict]:
        vector_results = self.vector.search(query, n_results=n_results * 2)
        parsed_vector = []
        for r in vector_results:
            score = 1.0 - float(r.get("distance", 0))
            item = self._parse_result(r, score)
            item["_vector_score"] = score
            parsed_vector.append(item)

        kw_terms = keywords or query.lower().split()
        keyword_results = self._keyword_search(kw_terms, limit=n_results * 3)
        kw_max = max((k.get("_keyword_score", 0) for k in keyword_results), default=1)
        if kw_max > 0:
            for k in keyword_results:
                k["_keyword_score"] = k["_keyword_score"] / kw_max

        seen = {}
        for item in parsed_vector + keyword_results:
            rid = item.get("id", "")
            if rid in seen:
                seen[rid]["_vector_score"] = max(seen[rid].get("_vector_score", 0), item.get("_vector_score", 0))
                seen[rid]["_keyword_score"] = max(seen[rid].get("_keyword_score", 0), item.get("_keyword_score", 0))
            else:
                seen[rid] = dict(item)

        for item in seen.values():
            vs = item.get("_vector_score", 0)
            ks = item.get("_keyword_score", 0)
            item["_score"] = alpha * vs + (1 - alpha) * ks

        merged = sorted(seen.values(), key=lambda x: x.get("_score", 0), reverse=True)
        return merged[:n_results]

    def search_with_filters(self, query: str, must: dict = None, should: dict = None,
                            must_not: dict = None, n_results: int = 20) -> list[dict]:
        results = self.vector.search(query, n_results=n_results * 3)
        parsed = []
        for r in results:
            score = 1.0 - float(r.get("distance", 0))
            item = self._parse_result(r, score)
            meta = r.get("metadata", {})

            if must:
                if not self._match_must(meta, must):
                    continue
            if must_not:
                if self._match_any(meta, must_not):
                    continue
            if should:
                should_score = self._compute_should_score(meta, should)
                item["_score"] = score * (1 + should_score * 0.2)

            parsed.append(item)

        parsed.sort(key=lambda x: x.get("_score", 0), reverse=True)
        return parsed[:n_results]

    def expand_query(self, query: str, expansion_terms: list[str] = None) -> str:
        if not expansion_terms:
            return query
        expanded = query
        for term in expansion_terms:
            expanded = f"{expanded} {term}"
        return expanded.strip()

    def rerank(self, query: str, results: list[dict], method: str = "cross_encoder") -> list[dict]:
        if not results:
            return results

        if method == "recency":
            return self._rerank_by_recency(results)
        elif method == "cross_encoder":
            return self._rerank_by_cross_encoder(query, results)
        return results

    def max_marginal_relevance(self, query_emb: list[float], results: list[dict],
                               lambda_param: float = 0.5, n: int = 20) -> list[dict]:
        if not results:
            return []

        if not query_emb or all(v == 0 for v in query_emb):
            return results[:n]

        for r in results:
            if "_embedding" not in r:
                text = f"{r.get('title', '')} {r.get('content', '')}"
                r["_embedding"] = self._get_embedding(text)

        selected = []
        remaining = list(results)

        query_vec = np.array(query_emb)
        first = remaining.pop(0)
        selected.append(first)

        while len(selected) < n and remaining:
            similarities = []
            for r in remaining:
                doc_vec = np.array(r["_embedding"])
                sim_to_query = float(np.dot(query_vec, doc_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-10))
                max_sim_to_selected = max(
                    [float(np.dot(np.array(s["_embedding"]), doc_vec) /
                     (np.linalg.norm(np.array(s["_embedding"])) * np.linalg.norm(doc_vec) + 1e-10))
                     for s in selected],
                    default=0
                )
                mmr_score = lambda_param * sim_to_query - (1 - lambda_param) * max_sim_to_selected
                similarities.append((mmr_score, r))

            similarities.sort(key=lambda x: x[0], reverse=True)
            next_item = similarities[0][1]
            selected.append(next_item)
            remaining.remove(next_item)

        return selected

    def get_query_expansion_suggestions(self, query: str) -> list[str]:
        words = query.lower().split()
        suggestions = []
        expansion_map = {
            "ai": ["artificial intelligence", "machine learning", "deep learning"],
            "ml": ["machine learning", "deep learning", "neural networks"],
            "rag": ["retrieval augmented generation", "vector search", "knowledge retrieval"],
            "llm": ["large language model", "gpt", "foundation model"],
            "agent": ["multi-agent", "autonomous agent", "agentic"],
            "nlp": ["natural language processing", "text analytics", "language model"],
            "robot": ["robotics", "humanoid", "automation"],
            "quantum": ["quantum computing", "qubit", "quantum algorithm"],
        }
        for w in words:
            if w in expansion_map:
                suggestions.extend(expansion_map[w])
        return list(set(suggestions))[:10]

    def _parse_result(self, result: dict, score: float) -> dict:
        meta = result.get("metadata", {})
        return {
            "id": result.get("id", ""),
            "title": meta.get("title", ""),
            "content": result.get("content", ""),
            "url": meta.get("url", ""),
            "source": meta.get("source", ""),
            "source_type": meta.get("source_type", ""),
            "topics": meta.get("topics", "").split(",") if meta.get("topics") else [],
            "author": meta.get("author", ""),
            "published_at": meta.get("published_at", ""),
            "engagement": int(meta.get("engagement", 0) or 0),
            "_score": score,
            "_distance": float(result.get("distance", 0)),
        }

    def _apply_boost_factors(self, results: list[dict], factors: dict) -> list[dict]:
        for item in results:
            boost = 1.0
            for field, factor in factors.items():
                val = str(item.get(field, "")).lower()
                if isinstance(factor, dict):
                    for term_val, term_boost in factor.items():
                        if term_val.lower() in val:
                            boost *= term_boost
                elif val:
                    boost *= factor
            item["_score"] = item.get("_score", 0) * boost
        return results

    def _match_must(self, meta: dict, must: dict) -> bool:
        for field, values in must.items():
            if not isinstance(values, list):
                values = [values]
            meta_val = str(meta.get(field, "")).lower()
            if not any(str(v).lower() in meta_val for v in values):
                return False
        return True

    def _match_any(self, meta: dict, conditions: dict) -> bool:
        for field, values in conditions.items():
            if not isinstance(values, list):
                values = [values]
            meta_val = str(meta.get(field, "")).lower()
            if any(str(v).lower() in meta_val for v in values):
                return True
        return False

    def _compute_should_score(self, meta: dict, should: dict) -> float:
        score = 0.0
        total = 0
        for field, values in should.items():
            if not isinstance(values, list):
                values = [values]
            meta_val = str(meta.get(field, "")).lower()
            for v in values:
                total += 1
                if str(v).lower() in meta_val:
                    score += 1
        return score / total if total > 0 else 0

    def _keyword_search(self, terms: list[str], limit: int = 50) -> list[dict]:
        results = []
        seen_ids = set()
        with self.sql._conn() as conn:
            for term in terms[:5]:
                rows = conn.execute("""
                    SELECT id, title, content, content_cleaned, url, source, source_type,
                           topics, author_name, published_at, engagement
                    FROM items
                    WHERE content_cleaned LIKE ? OR title LIKE ?
                    ORDER BY engagement DESC
                    LIMIT ?
                """, (f"%{term}%", f"%{term}%", limit)).fetchall()
                for r in rows:
                    rid = r[0]
                    if rid in seen_ids:
                        continue
                    seen_ids.add(rid)
                    kw_score = sum(1 for t in terms if t.lower() in (r[1] or "").lower() or t.lower() in (r[2] or "").lower())
                    topics_str = r[7] or ""
                    results.append({
                        "id": rid,
                        "title": r[1],
                        "content": r[3] or r[2] or "",
                        "url": r[4],
                        "source": r[5],
                        "source_type": r[6],
                        "topics": topics_str.split(",") if topics_str else [],
                        "author": r[8],
                        "published_at": r[9],
                        "engagement": r[10] or 0,
                        "_keyword_score": kw_score,
                        "_vector_score": 0,
                    })
        return results

    def _rerank_by_recency(self, results: list[dict]) -> list[dict]:
        now = datetime.now()
        for item in results:
            pub = item.get("published_at", "")
            if pub:
                try:
                    dt = datetime.fromisoformat(pub.replace("Z", "+00:00").split(".")[0])
                    hours_ago = (now - dt).total_seconds() / 3600
                    recency_boost = max(0, 1.0 - (hours_ago / 720))
                    item["_score"] = item.get("_score", 0) * (1 + recency_boost * 0.5)
                except (ValueError, TypeError):
                    pass
        return sorted(results, key=lambda x: x.get("_score", 0), reverse=True)

    def _rerank_by_cross_encoder(self, query: str, results: list[dict]) -> list[dict]:
        try:
            from sentence_transformers import CrossEncoder
            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query, r.get("title", "") + " " + r.get("content", "")[:512]) for r in results]
            scores = model.predict(pairs)
            for i, r in enumerate(results):
                r["_score"] = float(scores[i])
            return sorted(results, key=lambda x: x["_score"], reverse=True)
        except ImportError:
            return self._rerank_by_recency(results)

    def _get_embedding(self, text: str) -> list[float]:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(self.embedding_model)
            return model.encode(text).tolist()
        except ImportError:
            return []

from ..core.config import settings
from ..core.models import ContentItem
from ..storage.vector_store import VectorStore


def _get_store() -> VectorStore:
    return VectorStore(db_path=settings.CHROMA_DB_PATH)


def recommend_similar(item: ContentItem, n: int = 5) -> list[dict]:
    store = _get_store()
    query_text = f"{item.title}\n{item.content_cleaned or item.content}"
    results = store.search(query_text, n_results=n + 1)
    return [r for r in results if r["id"] != item.id][:n]


def recommend_for_query(query: str, n: int = 10) -> list[dict]:
    store = _get_store()
    return store.search(query, n_results=n)


def recommend_by_topic(topic: str, exclude_ids: list[str] = None, n: int = 10) -> list[dict]:
    store = _get_store()
    exclude_ids = set(exclude_ids or [])
    results = store.search_by_topic(topic, n_results=n * 2)
    filtered = [r for r in results if r["id"] not in exclude_ids]
    return filtered[:n]


def get_personalized_feed(user_topics: list[str], user_sources: list[str] = None, n: int = 20) -> list[dict]:
    store = _get_store()
    all_results = []
    seen_ids = set()

    if user_sources:
        for source in user_sources:
            results = store.search(source, n_results=n)
            for r in results:
                if r["id"] not in seen_ids:
                    r["match_reason"] = f"source:{source}"
                    all_results.append(r)
                    seen_ids.add(r["id"])

    for topic in user_topics:
        results = store.search_by_topic(topic, n_results=n)
        for r in results:
            if r["id"] not in seen_ids:
                r["match_reason"] = f"topic:{topic}"
                all_results.append(r)
                seen_ids.add(r["id"])

    all_results.sort(key=lambda x: x.get("distance", 0) if "distance" in x else x.get("metadata", {}).get("engagement", 0), reverse=True)
    return all_results[:n]

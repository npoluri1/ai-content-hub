"""NewsAPI collector — fetches news via NewsAPI.org (free tier: 100 req/day)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime, timedelta


class NewsAPICollector(BaseCollector):
    name = "newsapi"
    source_type = "news"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        if not settings.NEWSAPI_API_KEY:
            return self._collect_demo_fallback(max_items)

        import httpx
        results = []
        queries = [q.strip() for q in settings.NEWSAPI_QUERIES.split(",")]

        with httpx.Client(timeout=15) as client:
            for query in queries[:3]:
                try:
                    resp = client.get(
                        "https://newsapi.org/v2/everything",
                        params={
                            "q": query,
                            "language": "en",
                            "sortBy": "publishedAt",
                            "pageSize": min(20, max_items // len(queries)),
                            "from": (datetime.now() - timedelta(days=7)).date().isoformat(),
                            "apiKey": settings.NEWSAPI_API_KEY,
                        },
                    )
                    if resp.status_code == 200:
                        for article in resp.json().get("articles", []):
                            results.append(self._parse_article(article))
                except Exception as e:
                    print(f"  [NewsAPI] Error on {query}: {e}")

        return results[:max_items]

    def _parse_article(self, article: dict) -> ContentItem:
        return self.make_item(
            title=article.get("title", ""),
            content=article.get("description", "") or article.get("content", "") or "",
            url=article.get("url", ""),
            author_name=article.get("author", ""),
            hashtags=["News"],
            image_urls=[article.get("urlToImage", "")] if article.get("urlToImage") else [],
            published_at=self._parse_date(article.get("publishedAt", "")),
        )

    def _parse_date(self, s: str):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return None

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        return [
            self.make_item(title="New AI Framework Revolutionizes Agent Development", content="A new open-source framework for building AI agents claims 10x productivity improvement over existing tools.", url="https://example.com/ai-framework", hashtags=["AI", "AgenticAI"], engagement=450),
            self.make_item(title="Quantum Computing Breakthrough: 1000 Stable Qubits Achieved", content="Research team demonstrates 1000 stable qubits using topological error correction.", url="https://example.com/quantum", hashtags=["Quantum_Computing"], engagement=890),
        ][:max_items]

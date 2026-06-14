"""dev.to collector — fetches articles via dev.to API (free, no key)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime


class DevToCollector(BaseCollector):
    name = "devto"
    source_type = "post"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        tags = [t.strip() for t in settings.DEVTO_TAGS.split(",")]

        with httpx.Client(timeout=15) as client:
            for tag in tags[:5]:
                try:
                    resp = client.get(
                        "https://dev.to/api/articles",
                        params={
                            "tag": tag,
                            "per_page": min(20, max_items // len(tags)),
                            "state": "fresh",
                        },
                        headers={"User-Agent": "AI-Content-Hub/1.0"},
                    )
                    if resp.status_code == 200:
                        for article in resp.json():
                            results.append(self._parse_article(article))
                except Exception as e:
                    print(f"  [DevTo] Error on {tag}: {e}")

        return results[:max_items]

    def _parse_article(self, article: dict) -> ContentItem:
        tags = [article.get("tag_list", [])] if isinstance(article.get("tag_list"), list) else []
        return self.make_item(
            title=article.get("title", ""),
            content=article.get("description", ""),
            url=article.get("url", ""),
            author_name=article.get("user", {}).get("name", ""),
            author_url=article.get("user", {}).get("website_url") or "",
            hashtags=article.get("tag_list", []),
            image_urls=[article.get("social_image", "")] if article.get("social_image") else [],
            engagement=article.get("positive_reactions_count", 0),
            published_at=self._parse_date(article.get("published_at", "")),
        )

    def _parse_date(self, s: str):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return None

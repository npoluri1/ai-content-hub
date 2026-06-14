"""ArXiv collector — fetches research papers via ArXiv API."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime
import re


class ArXivCollector(BaseCollector):
    name = "arxiv"
    source_type = "paper"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        import xml.etree.ElementTree as ET
        results = []
        categories = [c.strip() for c in settings.ARXIV_CATEGORIES.split(",")]

        with httpx.Client(timeout=30) as client:
            for cat in categories[:3]:
                try:
                    resp = client.get(
                        "http://export.arxiv.org/api/query",
                        params={
                            "search_query": f"cat:{cat}",
                            "sortBy": "submittedDate",
                            "sortOrder": "descending",
                            "max_results": min(20, max_items // len(categories)),
                        },
                    )
                    if resp.status_code == 200:
                        root = ET.fromstring(resp.text)
                        ns = {
                            "atom": "http://www.w3.org/2005/Atom",
                            "arxiv": "http://arxiv.org/schemas/atom",
                        }
                        for entry in root.findall("atom:entry", ns):
                            results.append(self._parse_entry(entry, ns))
                except Exception as e:
                    print(f"  [ArXiv] Error on {cat}: {e}")

        return results[:max_items] or self._collect_demo_fallback(max_items)

    def _parse_entry(self, entry, ns: dict) -> ContentItem:
        title = entry.findtext("atom:title", "", ns).replace("\n", " ").strip()
        summary = entry.findtext("atom:summary", "", ns).replace("\n", " ").strip()
        link_el = entry.find("atom:id", ns)
        url = link_el.text if link_el is not None else ""
        published = entry.findtext("atom:published", "", ns)
        authors = [a.findtext("atom:name", "", ns) for a in entry.findall("atom:author", ns)]
        categories = [c.get("term", "") for c in entry.findall("atom:category", ns)]

        hashtags = ["ArXiv"] + categories
        return self.make_item(
            title=title[:300],
            content=summary[:2000],
            url=url,
            author_name=", ".join(authors[:3]),
            hashtags=hashtags,
            published_at=self._parse_date(published),
        )

    def _parse_date(self, s: str):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return None

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("arxiv", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

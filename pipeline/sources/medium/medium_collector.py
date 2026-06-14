"""Medium collector — fetches via RSS feeds (free, no key)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
import re
from datetime import datetime


class MediumCollector(BaseCollector):
    name = "medium"
    source_type = "post"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        tags = [t.strip() for t in settings.MEDIUM_TAGS.split(",")]

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for tag in tags[:5]:
                try:
                    resp = client.get(
                        f"https://medium.com/feed/tag/{tag}",
                        headers={"User-Agent": "Mozilla/5.0"},
                    )
                    if resp.status_code == 200:
                        items = self._parse_rss(resp.text, tag, max_items // len(tags))
                        results.extend(items)
                except Exception as e:
                    print(f"  [Medium] Error on tag {tag}: {e}")

        return results[:max_items]

    def _parse_rss(self, xml_text: str, tag: str, max_items: int) -> list[ContentItem]:
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return []
        items = []
        root = ET.fromstring(xml_text)
        for entry in list(root.iter("item"))[:max_items]:
            title = entry.findtext("title", "")
            link = entry.findtext("link", "")
            creator = entry.findtext("{http://purl.org/dc/elements/1.1/}creator", "")
            pub_date = entry.findtext("pubDate", "")
            desc = entry.findtext("description", "")
            content_encoded = entry.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
            text = content_encoded or desc
            text_clean = re.sub(r"<[^>]+>", "", text)[:2000]

            items.append(self.make_item(
                title=title,
                content=text_clean,
                url=link,
                author_name=creator,
                hashtags=[tag],
                published_at=self._parse_date(pub_date),
            ))
        return items

    def _parse_date(self, s: str):
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(s)
        except:
            return None

"""TechCrunch collector — uses RSS feed (no API key required)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
import re
from datetime import datetime


class TechCrunchCollector(BaseCollector):
    name = "techcrunch"
    source_type = "news"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        feed_urls = [
            "https://techcrunch.com/feed/",
            "https://techcrunch.com/category/artificial-intelligence/feed/",
        ]

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for feed_url in feed_urls:
                try:
                    resp = client.get(feed_url)
                    if resp.status_code == 200:
                        items = self._parse_rss(resp.text, max_items // len(feed_urls))
                        results.extend(items)
                except Exception as e:
                    print(f"  [TechCrunch] Error: {e}")

        return results[:max_items] or self._collect_demo_fallback(max_items)

    def _parse_rss(self, xml_text: str, max_items: int) -> list[ContentItem]:
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return []
        items = []
        root = ET.fromstring(xml_text)
        ns = {"": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/"}

        for entry in list(root.iter("{http://www.w3.org/2005/Atom}entry"))[:max_items]:
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            content_el = entry.find("{http://www.w3.org/2005/Atom}content")
            content = content_el.text if content_el is not None else ""
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            url = link_el.get("href", "") if link_el is not None else ""
            published = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
            author_el = entry.find("{http://www.w3.org/2005/Atom}author")
            author = author_el.findtext("{http://www.w3.org/2005/Atom}name", "") if author_el is not None else ""

            hashtags = re.findall(r"#(\w+)", title + " " + content)
            text_clean = re.sub(r"<[^>]+>", "", content)
            items.append(self.make_item(
                title=title,
                content=text_clean,
                url=url,
                author_name=author,
                hashtags=hashtags,
                published_at=self._parse_date(published),
            ))
        return items

    def _parse_rss2(self, xml_text: str, max_items: int) -> list[ContentItem]:
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return []
        items = []
        root = ET.fromstring(xml_text)
        for item in list(root.iter("item"))[:max_items]:
            title = item.findtext("title", "")
            desc = item.findtext("description", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            author = item.findtext("dc:creator", "")
            text_clean = re.sub(r"<[^>]+>", "", desc)
            hashtags = re.findall(r"#(\w+)", title + " " + text_clean)
            items.append(self.make_item(
                title=title,
                content=text_clean,
                url=link,
                author_name=author,
                hashtags=hashtags,
                published_at=self._parse_rss2_date(pub_date),
            ))
        return items

    def _parse_date(self, s: str):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return None

    def _parse_rss2_date(self, s: str):
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(s)
        except:
            return None

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("techcrunch", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

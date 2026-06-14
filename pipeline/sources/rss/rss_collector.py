"""Generic RSS collector — fetches any RSS/Atom feed."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
import re
from datetime import datetime


class RSSCollector(BaseCollector):
    name = "rss"
    source_type = "news"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        urls = [u.strip() for u in settings.RSS_FEED_URLS.split(",") if u.strip()]

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        items = self._parse_feed(resp.text, max_items // len(urls))
                        results.extend(items)
                except Exception as e:
                    print(f"  [RSS] Error on {url}: {e}")

        return results[:max_items]

    def _parse_feed(self, text: str, max_items: int) -> list[ContentItem]:
        if "<feed" in text[:200] or "<atom:feed" in text[:200]:
            return self._parse_atom(text, max_items)
        return self._parse_rss(text, max_items)

    def _parse_atom(self, text: str, max_items: int) -> list[ContentItem]:
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return []
        items = []
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in list(root.iter("{http://www.w3.org/2005/Atom}entry"))[:max_items]:
            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
            content_el = entry.find("{http://www.w3.org/2005/Atom}content")
            content = content_el.text if content_el is not None else ""
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            url = link_el.get("href", "") if link_el is not None else ""
            published = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
            text_clean = re.sub(r"<[^>]+>", "", content)[:2000]
            items.append(self.make_item(title=title, content=text_clean, url=url, published_at=self._parse_date(published)))
        return items

    def _parse_rss(self, text: str, max_items: int) -> list[ContentItem]:
        try:
            import xml.etree.ElementTree as ET
        except ImportError:
            return []
        items = []
        root = ET.fromstring(text)
        for item in list(root.iter("item"))[:max_items]:
            title = item.findtext("title", "")
            desc = item.findtext("description", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            text_clean = re.sub(r"<[^>]+>", "", desc)[:2000]
            items.append(self.make_item(title=title, content=text_clean, url=link, published_at=self._parse_rss2_date(pub_date)))
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

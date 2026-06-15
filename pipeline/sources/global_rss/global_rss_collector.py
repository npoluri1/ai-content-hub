"""Global RSS collector — 50+ feeds across AI, Quantum, Robotics, Enterprise, with image extraction."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
import re
from datetime import datetime


GLOBAL_FEEDS = {
    "ai_general": [
        "https://venturebeat.com/feed/",
        "https://www.technologyreview.com/feed/",
        "https://www.theverge.com/ai-artificial-intelligence/rss.xml",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
        "https://www.artificialintelligence-news.com/feed/",
        "https://aibusiness.com/rss",
    ],
    "ai_research": [
        "https://research.google/blog/feed/",
        "https://deepmind.google/blog/feed.xml",
        "https://ai.meta.com/blog/rss.xml",
        "https://blogs.nvidia.com/feed/",
        "https://www.microsoft.com/en-us/research/feed/",
        "https://research.ibm.com/blog/feed.xml",
        "https://machinelearning.apple.com/rss.xml",
        "https://openai.com/blog/rss.xml",
    ],
    "data_science_ml": [
        "https://www.analyticsvidhya.com/blog/feed/",
        "https://towardsdatascience.com/feed",
        "https://www.kdnuggets.com/feed",
        "https://www.marktechpost.com/feed/",
        "https://syncedreview.com/feed/",
        "https://www.datasciencecentral.com/feed/",
        "https://insidebigdata.com/feed/",
        "https://www.oreilly.com/radar/feed/",
    ],
    "quantum_computing": [
        "https://phys.org/rss-feed/technology-focus/quantum-computing/",
        "https://www.sciencedaily.com/rss/computers_math/quantum_computers.xml",
        "https://spectrum.ieee.org/topic/quantum-computing/rss",
        "https://quantumcomputingreport.com/feed/",
        "https://www.hpcwire.com/category/quantum-computing/feed/",
    ],
    "robotics": [
        "https://spectrum.ieee.org/topic/robotics/rss",
        "https://www.therobotreport.com/feed/",
        "https://www.roboticsbusinessreview.com/feed/",
        "https://www.sciencedaily.com/rss/computers_math/robotics.xml",
        "https://techxplore.com/rss-feed/technology-news/robotics/",
    ],
    "enterprise": [
        "https://www.cio.com/feed/",
        "https://www.infoworld.com/index.rss",
        "https://www.enterpriseai.news/feed/",
        "https://www.fastcompany.com/technology/rss",
        "https://www.forbes.com/innovation/feed/",
        "https://www.newscientist.com/subject/technology/feed/",
        "https://www.theregister.com/headlines.rss",
    ],
    "developer_platform": [
        "https://github.blog/feed/",
        "https://stackoverflow.blog/feed/",
        "https://www.docker.com/blog/feed/",
        "https://kubernetes.io/feed.xml",
        "https://aws.amazon.com/blogs/machine-learning/feed/",
        "https://cloud.google.com/blog/products/ai-machine-learning/rss",
        "https://www.databricks.com/blog/feed",
        "https://news.ycombinator.com/rss",
    ],
}


class GlobalRSSCollector(BaseCollector):
    name = "global_rss"
    source_type = "news"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        all_urls = []
        for category, urls in GLOBAL_FEEDS.items():
            all_urls.extend(urls)

        per_feed = max(1, max_items // len(all_urls))

        with httpx.Client(timeout=30, follow_redirects=True, verify=False) as client:
            for url in all_urls:
                try:
                    resp = client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
                    })
                    if resp.status_code == 200 and resp.text:
                        items = self._parse_feed(resp.text, per_feed, url)
                        results.extend(items)
                except Exception as e:
                    continue

        results.sort(key=lambda x: x.published_at or datetime(2000, 1, 1), reverse=True)
        return results[:max_items]

    def _parse_feed(self, text: str, max_items: int, feed_url: str) -> list[ContentItem]:
        if "<feed" in text[:200] or "<atom:feed" in text[:200]:
            return self._parse_atom(text, max_items, feed_url)
        return self._parse_rss(text, max_items, feed_url)

    def _extract_images(self, html_text: str) -> list[str]:
        urls = re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html_text)
        clean = []
        for u in urls:
            if not u.startswith("data:") and not u.startswith("//"):
                clean.append(u.split("?")[0])
        return clean[:3]

    def _parse_atom(self, text: str, max_items: int, feed_url: str) -> list[ContentItem]:
        import xml.etree.ElementTree as ET
        items = []
        root = ET.fromstring(text)
        for entry in list(root.iter("{http://www.w3.org/2005/Atom}entry"))[:max_items]:
            try:
                title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
                content_el = entry.find("{http://www.w3.org/2005/Atom}content")
                summary_el = entry.find("{http://www.w3.org/2005/Atom}summary")
                raw_html = ""
                if content_el is not None and content_el.text:
                    raw_html = content_el.text
                elif summary_el is not None and summary_el.text:
                    raw_html = summary_el.text
                link_el = entry.find("{http://www.w3.org/2005/Atom}link")
                url = link_el.get("href", "") if link_el is not None else ""
                published = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
                updated = entry.findtext("{http://www.w3.org/2005/Atom}updated", "")
                author_el = entry.find("{http://www.w3.org/2005/Atom}author")
                author = author_el.findtext("{http://www.w3.org/2005/Atom}name", "") if author_el is not None else ""

                text_clean = re.sub(r"<[^>]+>", "", raw_html)[:2000]
                images = self._extract_images(raw_html)
                pub_date = self._parse_date(published) or self._parse_date(updated)

                items.append(self.make_item(
                    title=title, content=text_clean, url=url,
                    published_at=pub_date, author_name=author,
                    image_urls=images,
                    metadata={"feed": feed_url},
                ))
            except Exception:
                continue
        return items

    def _parse_rss(self, text: str, max_items: int, feed_url: str) -> list[ContentItem]:
        import xml.etree.ElementTree as ET
        items = []
        root = ET.fromstring(text)
        channel = root.find("channel")
        item_elements = channel.findall("item") if channel is not None else root.findall("item")
        for item in list(item_elements)[:max_items]:
            try:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                content_encoded = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                author = item.findtext("author", "") or item.findtext("dc:creator", "")

                raw_html = content_encoded or desc or ""
                text_clean = re.sub(r"<[^>]+>", "", raw_html)[:2000]
                images = self._extract_images(raw_html)

                items.append(self.make_item(
                    title=title, content=text_clean, url=link,
                    published_at=self._parse_rss2_date(pub_date),
                    author_name=author,
                    image_urls=images,
                    metadata={"feed": feed_url},
                ))
            except Exception:
                continue
        return items

    def _parse_date(self, s: str):
        if not s:
            return None
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return d.replace(tzinfo=None)
        except Exception:
            return None

    def _parse_rss2_date(self, s: str):
        if not s:
            return None
        from email.utils import parsedate_to_datetime
        try:
            d = parsedate_to_datetime(s)
            return d.replace(tzinfo=None)
        except Exception:
            return None

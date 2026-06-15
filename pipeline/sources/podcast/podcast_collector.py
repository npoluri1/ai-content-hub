"""Podcast RSS collector — fetches AI/tech podcast episodes with audio URLs."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
import re
from datetime import datetime


PODCAST_FEEDS = {
    "nvidia_ai": "https://feeds.simplecast.com/nVIDIA_AI_Podcast",
    "practical_ai": "https://changelog.com/practicalai/feed",
    "last_week_in_ai": "https://lastweekin.ai/feed/podcast/",
    "twiml_ai": "https://twimlai.com/feed/podcast/",
    "data_skeptic": "https://dataskeptic.libsyn.com/rss",
    "lex_fridman": "https://lexfridman.com/feed/podcast/",
    "software_engineering_daily": "https://feeds.simplecast.com/sLjM1Tud",
    "ai_in_business": "https://aiinbusiness.podbean.com/feed.xml",
    "mit_ai": "https://www.podcastics.com/podcast/artificial-intelligence/feed.xml",
}


class PodcastCollector(BaseCollector):
    name = "podcast"
    source_type = "podcast"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []
        per_feed = max(1, max_items // len(PODCAST_FEEDS))

        with httpx.Client(timeout=30, follow_redirects=True, verify=False) as client:
            for name, url in PODCAST_FEEDS.items():
                try:
                    resp = client.get(url, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Accept": "application/rss+xml, application/xml, text/xml",
                    })
                    if resp.status_code == 200 and resp.text:
                        items = self._parse_podcast_rss(resp.text, per_feed, name)
                        results.extend(items)
                except Exception:
                    continue

        results.sort(key=lambda x: x.published_at or datetime.min, reverse=True)
        return results[:max_items]

    def _parse_podcast_rss(self, text: str, max_items: int, feed_name: str) -> list[ContentItem]:
        import xml.etree.ElementTree as ET
        items = []
        root = ET.fromstring(text)
        channel = root.find("channel")
        if channel is None:
            return items

        podcast_title = channel.findtext("title", feed_name)
        podcast_desc = channel.findtext("description", "")
        podcast_image = channel.findtext("image/url", "")

        for item in list(channel.findall("item"))[:max_items]:
            try:
                title = item.findtext("title", "")
                desc = item.findtext("description", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                duration = item.findtext("{http://www.apple.com/itunes/}duration", "")
                episode_image = item.findtext("{http://www.apple.com/itunes/}image", "")

                enclosure = item.find("enclosure")
                audio_url = enclosure.get("url", "") if enclosure is not None else ""
                audio_type = enclosure.get("type", "") if enclosure is not None else ""

                text_clean = re.sub(r"<[^>]+>", "", desc)[:2000]
                images = [episode_image] if episode_image else ([podcast_image] if podcast_image else [])

                content = f"[Podcast: {podcast_title}]\n{text_clean}"
                if duration:
                    content = f"[Duration: {duration}s]\n{content}"

                metadata = {
                    "feed_name": feed_name,
                    "podcast_title": podcast_title,
                    "duration_seconds": duration,
                    "audio_url": audio_url,
                    "audio_type": audio_type,
                }

                items.append(self.make_item(
                    title=f"[{podcast_title}] {title}",
                    content=content,
                    url=link,
                    published_at=self._parse_rss2_date(pub_date),
                    image_urls=images,
                    metadata=metadata,
                ))
            except Exception:
                continue
        return items

    def _parse_rss2_date(self, s: str):
        if not s:
            return None
        from email.utils import parsedate_to_datetime
        try:
            d = parsedate_to_datetime(s)
            return d.replace(tzinfo=None)
        except Exception:
            return None

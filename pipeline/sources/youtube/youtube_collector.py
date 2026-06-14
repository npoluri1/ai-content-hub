"""YouTube collector — fetches videos via YouTube Data API v3."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime


class YouTubeCollector(BaseCollector):
    name = "youtube"
    source_type = "video"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        if not settings.YOUTUBE_API_KEY:
            return self._collect_demo_fallback(max_items)

        import httpx
        results = []
        channels = [c.strip() for c in settings.YOUTUBE_CHANNELS.split(",") if c.strip()]

        with httpx.Client(timeout=30) as client:
            for channel_id in channels[:3]:
                try:
                    resp = client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "channelId": channel_id,
                            "order": "date",
                            "maxResults": min(20, max_items // len(channels)),
                            "type": "video",
                            "key": settings.YOUTUBE_API_KEY,
                        },
                    )
                    if resp.status_code == 200:
                        for item in resp.json().get("items", []):
                            results.append(self._parse_video(item))
                except Exception as e:
                    print(f"  [YouTube] Error: {e}")

            # Also search by keyword
            for query in ["AI agents", "LangGraph", "MCP protocol", "RAG tutorial"]:
                try:
                    resp = client.get(
                        "https://www.googleapis.com/youtube/v3/search",
                        params={
                            "part": "snippet",
                            "q": query,
                            "order": "date",
                            "maxResults": 10,
                            "type": "video",
                            "key": settings.YOUTUBE_API_KEY,
                        },
                    )
                    if resp.status_code == 200:
                        for item in resp.json().get("items", []):
                            results.append(self._parse_video(item))
                except:
                    pass

        return results[:max_items]

    def _parse_video(self, item: dict) -> ContentItem:
        snippet = item.get("snippet", {})
        video_id = item.get("id", {}).get("videoId", "")
        title = snippet.get("title", "")
        description = snippet.get("description", "")
        channel_title = snippet.get("channelTitle", "")
        published = snippet.get("publishedAt", "")
        thumbnails = snippet.get("thumbnails", {})
        thumb_url = ""
        if "high" in thumbnails:
            thumb_url = thumbnails["high"]["url"]
        elif "medium" in thumbnails:
            thumb_url = thumbnails["medium"]["url"]

        return self.make_item(
            title=title,
            content=description[:1000],
            url=f"https://youtube.com/watch?v={video_id}",
            author_name=channel_title,
            author_url=f"https://youtube.com/channel/{snippet.get('channelId', '')}",
            hashtags=["YouTube"],
            image_urls=[thumb_url] if thumb_url else [],
            video_url=f"https://youtube.com/watch?v={video_id}",
            published_at=self._parse_date(published),
        )

    def _parse_date(self, s: str):
        try:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        except:
            return None

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("youtube", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

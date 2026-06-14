"""Hacker News collector — uses Firebase API (free, no key)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from datetime import datetime


class HNCollector(BaseCollector):
    name = "hackernews"
    source_type = "post"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        results = []

        with httpx.Client(timeout=30) as client:
            try:
                resp = client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                if resp.status_code != 200:
                    return self._collect_demo_fallback(max_items)
                story_ids = resp.json()[:max_items]

                for sid in story_ids:
                    try:
                        sresp = client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                        if sresp.status_code == 200:
                            story = sresp.json()
                            if story and story.get("type") == "story":
                                results.append(self._parse_story(story))
                    except:
                        pass
            except Exception as e:
                print(f"  [HN] Error: {e}")

        return results[:max_items] or self._collect_demo_fallback(max_items)

    def _parse_story(self, story: dict) -> ContentItem:
        title = story.get("title", "")
        text = story.get("text", "") or title
        url = story.get("url", f"https://news.ycombinator.com/item?id={story.get('id', '')}")
        author = story.get("by", "")
        score = story.get("score", 0)
        timestamp = story.get("time", 0)

        return self.make_item(
            title=title,
            content=text,
            url=url,
            author_name=author,
            hashtags=["HackerNews"],
            engagement=score,
            published_at=datetime.fromtimestamp(timestamp) if timestamp else None,
        )

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("hackernews", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

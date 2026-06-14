"""Reddit collector — uses PRAW (Python Reddit API Wrapper) or direct HTTP API."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime
import re


class RedditCollector(BaseCollector):
    name = "reddit"
    source_type = "post"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            return self._collect_praw(max_items)
        return self._collect_http_api(max_items) or self._collect_demo_fallback(max_items)

    def _collect_praw(self, max_items: int) -> list[ContentItem]:
        try:
            import praw
        except ImportError:
            print("  [Reddit] praw not installed. Install: pip install praw")
            return self._collect_demo_fallback(max_items)

        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        results = []
        subreddits = [s.strip() for s in settings.REDDIT_SUBREDDITS.split(",")]
        for sub_name in subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for post in sub.hot(limit=min(20, max_items // len(subreddits))):
                    results.append(self._parse_post(post))
            except Exception as e:
                print(f"  [Reddit] Error on r/{sub_name}: {e}")
        return results[:max_items]

    def _collect_http_api(self, max_items: int) -> list[ContentItem]:
        import httpx
        results = []
        subreddits = [s.strip() for s in settings.REDDIT_SUBREDDITS.split(",")]
        with httpx.Client(timeout=15) as client:
            for sub_name in subreddits[:3]:
                try:
                    resp = client.get(
                        f"https://www.reddit.com/r/{sub_name}/hot.json",
                        headers={"User-Agent": settings.REDDIT_USER_AGENT},
                        params={"limit": min(20, max_items // len(subreddits))},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for child in data.get("data", {}).get("children", []):
                            post_data = child.get("data", {})
                            results.append(self._parse_json_post(post_data))
                except Exception as e:
                    print(f"  [Reddit-HTTP] Error on r/{sub_name}: {e}")
        return results[:max_items]

    def _parse_post(self, post) -> ContentItem:
        text = post.title + "\n" + (post.selftext or "")
        hashtags = re.findall(r"#(\w+)", text)
        return self.make_item(
            title=post.title,
            content=text,
            url=f"https://reddit.com{post.permalink}",
            author_name=f"u/{post.author.name if post.author else 'deleted'}",
            hashtags=hashtags,
            engagement=post.score,
            published_at=datetime.fromtimestamp(post.created_utc),
        )

    def _parse_json_post(self, d: dict) -> ContentItem:
        text = d.get("title", "") + "\n" + (d.get("selftext", "") or "")
        hashtags = re.findall(r"#(\w+)", text)
        return self.make_item(
            title=d.get("title", ""),
            content=text,
            url=f"https://reddit.com{d.get('permalink', '')}",
            author_name=f"u/{d.get('author', 'deleted')}",
            hashtags=hashtags,
            engagement=d.get("score", 0),
            published_at=datetime.fromtimestamp(d.get("created_utc", 0)),
        )

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("reddit", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

"""Content quality scoring — multi-factor quality evaluation."""

from ..core.models import ContentItem
from datetime import datetime, timedelta
import math
import re
from collections import defaultdict


SOURCE_AUTHORITY = {
    "arxiv": 20,
    "techcrunch": 18,
    "wired": 17,
    "nature": 20,
    "science": 20,
    "ieee": 19,
    "acm": 19,
    "github": 16,
    "medium": 12,
    "linkedin": 15,
    "twitter": 8,
    "x": 8,
    "reddit": 10,
    "hackernews": 14,
    "youtube": 11,
    "ycombinator": 14,
    "bluesky": 8,
    "substack": 13,
    "newsletter": 13,
    "blog": 12,
    "news": 14,
    "paper": 19,
    "video": 10,
    "podcast": 12,
    "discord": 5,
    "slack": 5,
    "telegram": 6,
    "whatsapp": 5,
    "wechat": 6,
    "zhihu": 11,
    "jianshu": 8,
    "csdn": 9,
    "cnblogs": 9,
    "v2ex": 8,
    "oschina": 9,
    "infoq": 15,
    "dzone": 12,
    "devto": 11,
    "hashnode": 10,
    "stackoverflow": 14,
    "quora": 9,
    "forbes": 16,
    "bloomberg": 17,
    "reuters": 17,
    "apnews": 16,
    "bbc": 16,
    "cnn": 15,
    "nytimes": 16,
    "wsj": 17,
    "ft": 17,
    "economist": 17,
}

QUALITY_TIERS = {
    "excellent": (80, 101),
    "good": (60, 80),
    "average": (40, 60),
    "poor": (0, 40),
}


class QualityScorer:
    def __init__(self, authority_scores: dict = None):
        self.authority = authority_scores or SOURCE_AUTHORITY

    def score(self, text: str) -> dict:
        length_score = self._length_score(text)
        readability_score = self._readability_score(text)
        engagement_score = 0
        freshness_score = self._freshness_score(None)

        total = length_score + readability_score + engagement_score + 10 + freshness_score

        return {
            "score": min(100, total),
            "factors": {
                "length_score": length_score,
                "readability_score": readability_score,
                "engagement_score": engagement_score,
                "source_authority_score": 10,
                "freshness_score": freshness_score,
            },
            "details": {
                "word_count": len(text.split()) if text else 0,
                "sentence_count": max(len(re.findall(r'[.!?]+', text)), 1) if text else 1,
                "flesch_score": self._flesch_readability(text) if text else 0,
            }
        }

    def score_item(self, item: ContentItem) -> ContentItem:
        text = item.content or item.title
        length_score = self._length_score(text)
        readability_score = self._readability_score(text)
        engagement_score = self._engagement_score(item.engagement)
        source_authority_score = self._source_authority_score(item.source)
        freshness_score = self._freshness_score(item.published_at)

        total = length_score + readability_score + engagement_score + source_authority_score + freshness_score

        item.metadata["quality_score"] = min(100, total)
        item.metadata["quality_factors"] = {
            "length_score": length_score,
            "readability_score": readability_score,
            "engagement_score": engagement_score,
            "source_authority_score": source_authority_score,
            "freshness_score": freshness_score,
        }
        item.metadata["quality_tier"] = self._get_tier(item.metadata["quality_score"])
        return item

    def score_batch(self, items: list[ContentItem]) -> list[ContentItem]:
        return [self.score_item(item) for item in items]

    def get_trending_content(self, topic: str = None, limit: int = 10) -> list[ContentItem]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()
        all_items = []

        if topic:
            results = store.get_by_topic(topic, limit=200)
        else:
            results = store.search("", limit=200)

        items = []
        for r in results:
            published = r.get("published_at", "")
            pub_date = None
            if published:
                try:
                    pub_date = datetime.fromisoformat(published)
                except (ValueError, TypeError):
                    pub_date = None

            item = ContentItem(
                id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                url=r.get("url", ""),
                source=r.get("source", ""),
                author_name=r.get("author", ""),
                published_at=pub_date,
                engagement=int(r.get("engagement", 0) or 0),
            )
            self.score_item(item)
            items.append(item)

        items.sort(key=lambda x: x.metadata.get("quality_score", 0), reverse=True)
        return items[:limit]

    def get_top_sources(self, topic: str = None, limit: int = 10) -> list[dict]:
        from ..storage.sql_store import SQLStore
        store = SQLStore()

        if topic:
            results = store.get_by_topic(topic, limit=500)
        else:
            results = store.search("", limit=500)

        source_scores = defaultdict(list)
        for r in results:
            source = r.get("source", "")
            if not source:
                continue
            item = ContentItem(
                id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                url=r.get("url", ""),
                source=source,
                engagement=int(r.get("engagement", 0) or 0),
            )
            self.score_item(item)
            source_scores[source].append(item.metadata.get("quality_score", 0))

        rankings = []
        for source, scores in source_scores.items():
            rankings.append({
                "source": source,
                "avg_quality": round(sum(scores) / len(scores), 1),
                "count": len(scores),
            })

        rankings.sort(key=lambda x: x["avg_quality"], reverse=True)
        return rankings[:limit]

    def get_quality_distribution(self, topic: str = None) -> dict:
        from ..storage.sql_store import SQLStore
        store = SQLStore()

        if topic:
            results = store.get_by_topic(topic, limit=1000)
        else:
            results = store.search("", limit=1000)

        dist = {"excellent": 0, "good": 0, "average": 0, "poor": 0}
        for r in results:
            published = r.get("published_at", "")
            pub_date = None
            if published:
                try:
                    pub_date = datetime.fromisoformat(published)
                except (ValueError, TypeError):
                    pub_date = None

            item = ContentItem(
                id=r.get("id", ""),
                title=r.get("title", ""),
                content=r.get("content", ""),
                url=r.get("url", ""),
                source=r.get("source", ""),
                engagement=int(r.get("engagement", 0) or 0),
                published_at=pub_date,
            )
            self.score_item(item)
            tier = item.metadata.get("quality_tier", "average")
            dist[tier] = dist.get(tier, 0) + 1

        return dist

    def _length_score(self, text: str) -> int:
        if not text:
            return 0
        word_count = len(text.split())
        if word_count >= 2000:
            return 20
        return int((word_count / 2000) * 20)

    def _readability_score(self, text: str) -> int:
        if not text:
            return 0
        flesch = self._flesch_readability(text)
        return max(0, min(20, int(flesch / 5)))

    def _flesch_readability(self, text: str) -> float:
        sentences = len(re.findall(r'[.!?]+', text))
        words = len(text.split())
        syllables = self._count_syllables(text)

        if sentences == 0 or words == 0:
            return 50

        return max(0, 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words))

    def _count_syllables(self, text: str) -> int:
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        total = 0
        for word in words:
            count = 0
            word = re.sub(r'e$', '', word)
            word = re.sub(r'[^aeiouy]+', ' ', word)
            count = len(word.split())
            if count == 0:
                count = 1
            total += count
        return total

    def _engagement_score(self, engagement: int) -> int:
        if not engagement or engagement <= 0:
            return 0
        return min(20, int(math.log10(engagement + 1) * 4))

    def _source_authority_score(self, source: str) -> int:
        if not source:
            return 10
        source_lower = source.lower().strip()
        if source_lower in self.authority:
            return self.authority[source_lower]
        for key, score in self.authority.items():
            if key in source_lower or source_lower in key:
                return score
        return 10

    def _freshness_score(self, published_at: datetime) -> int:
        if published_at is None:
            return 10
        now = datetime.now()
        age = now - published_at
        hours = age.total_seconds() / 3600

        if hours < 24:
            return 20
        elif hours < 72:
            return 16
        elif hours < 168:
            return 12
        elif hours < 720:
            return 8
        elif hours < 2160:
            return 4
        else:
            return 0

    def _get_tier(self, score: int) -> str:
        for tier, (low, high) in QUALITY_TIERS.items():
            if low <= score < high:
                return tier
        return "average"

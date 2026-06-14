from abc import ABC, abstractmethod
from .models import ContentItem
import hashlib
import re


class BaseCollector(ABC):
    name: str = "base"
    source_type: str = "post"

    @abstractmethod
    def collect(self, max_items: int = 100) -> list[ContentItem]:
        ...

    def clean_content(self, text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[^\w\s\.\,\!\?\-\:\;\(\)\#\@\/]", "", text)
        return text.strip()

    def make_id(self, source: str, unique_key: str) -> str:
        raw = f"{source}:{unique_key}"
        return hashlib.md5(raw.encode()).hexdigest()

    def make_item(
        self,
        title: str,
        content: str,
        url: str = "",
        author_name: str = "",
        author_url: str = "",
        published_at=None,
        hashtags: list[str] = None,
        topics: list[str] = None,
        image_urls: list[str] = None,
        video_url: str = "",
        engagement: int = 0,
        metadata: dict = None,
    ) -> ContentItem:
        cleaned = self.clean_content(content)
        unique_key = url or cleaned[:100]
        return ContentItem(
            id=self.make_id(self.name, unique_key),
            title=title,
            content=content,
            content_cleaned=cleaned,
            url=url,
            source=self.name,
            source_type=self.source_type,
            author_name=author_name,
            author_url=author_url,
            published_at=published_at,
            hashtags=hashtags or [],
            topics=topics or [],
            image_urls=image_urls or [],
            video_url=video_url,
            engagement=engagement,
            metadata=metadata or {},
        )

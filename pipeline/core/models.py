from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ContentItem(BaseModel):
    id: str
    title: str
    content: str
    content_cleaned: str = ""
    url: str = ""
    source: str  # linkedin, reddit, techcrunch, etc.
    source_type: str = "post"  # post, news, paper, video, image
    author_name: str = ""
    author_url: str = ""
    published_at: Optional[datetime] = None
    crawled_at: datetime = Field(default_factory=datetime.now)
    hashtags: list[str] = []
    topics: list[str] = []
    relevance_score: float = 0.0
    engagement: int = 0
    image_urls: list[str] = []
    video_url: str = ""
    metadata: dict = {}


class ClassifiedItem(ContentItem):
    is_relevant: bool = False
    classification_method: str = "keyword"  # keyword, llm, hybrid


class DigestConfig(BaseModel):
    topics: list[str] = []
    max_per_topic: int = 10
    include_irrelevant: bool = False
    format: str = "markdown"  # markdown, html, json


class SourceConfig(BaseModel):
    name: str
    enabled: bool = True
    scrape_interval_minutes: int = 360
    max_items_per_batch: int = 100
    api_key: str = ""
    api_secret: str = ""
    username: str = ""
    password: str = ""
    extra: dict = {}


class ScheduleConfig(BaseModel):
    source_schedules: dict[str, int] = {}
    digest_interval_minutes: int = 360
    digest_topics: list[str] = []
    digest_destinations: list[str] = ["file"]

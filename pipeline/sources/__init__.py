from .demo.demo_collector import DemoCollector
from .linkedin.linkedin_collector import LinkedInCollector
from .reddit.reddit_collector import RedditCollector
from .techcrunch.techcrunch_collector import TechCrunchCollector
from .techgig.techgig_collector import TechGigCollector
from .arxiv.arxiv_collector import ArXivCollector
from .youtube.youtube_collector import YouTubeCollector
from .hackernews.hn_collector import HNCollector
from .medium.medium_collector import MediumCollector
from .rss.rss_collector import RSSCollector
from .newsapi.newsapi_collector import NewsAPICollector
from .devto.devto_collector import DevToCollector
from .global_rss.global_rss_collector import GlobalRSSCollector
from .podcast.podcast_collector import PodcastCollector

COLLECTOR_MAP = {
    "demo": DemoCollector,
    "linkedin": LinkedInCollector,
    "reddit": RedditCollector,
    "techcrunch": TechCrunchCollector,
    "techgig": TechGigCollector,
    "arxiv": ArXivCollector,
    "youtube": YouTubeCollector,
    "hackernews": HNCollector,
    "medium": MediumCollector,
    "rss": RSSCollector,
    "newsapi": NewsAPICollector,
    "devto": DevToCollector,
    "global_rss": GlobalRSSCollector,
    "podcast": PodcastCollector,
}


def get_collector(name: str):
    Cls = COLLECTOR_MAP.get(name)
    if not Cls:
        raise ValueError(f"Unknown collector: {name}")
    return Cls()


def get_enabled_collectors(enabled_sources: list[str]):
    collectors = []
    for src in enabled_sources:
        src = src.strip()
        if src in COLLECTOR_MAP:
            collectors.append(get_collector(src))
    return collectors

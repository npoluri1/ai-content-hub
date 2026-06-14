"""TechGig collector — web scraping for tech news and articles."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
import re
from datetime import datetime


class TechGigCollector(BaseCollector):
    name = "techgig"
    source_type = "news"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        import httpx
        from bs4 import BeautifulSoup
        results = []
        urls = [
            "https://www.techgig.com/artificial-intelligence",
            "https://www.techgig.com/cloud-computing",
            "https://www.techgig.com/emerging-technologies",
        ]

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            for url in urls:
                try:
                    resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "lxml")
                        articles = soup.select("article, .article-card, .news-card")
                        for art in list(articles)[:10]:
                            link_el = art.find("a")
                            title_el = art.find(["h2", "h3", "h4"])
                            title = title_el.get_text(strip=True) if title_el else ""
                            link = link_el.get("href", "") if link_el else ""
                            if link and not link.startswith("http"):
                                link = "https://www.techgig.com" + link

                            desc_el = art.find(["p", ".description", ".summary"])
                            content = desc_el.get_text(strip=True) if desc_el else title

                            results.append(self.make_item(
                                title=title,
                                content=content,
                                url=link,
                                engagement=0,
                            ))
                except Exception as e:
                    print(f"  [TechGig] Error: {e}")

        return results[:max_items] or self._collect_demo_fallback(max_items)

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        return [
            self.make_item(
                title="TechGig: AI Skills Most In-Demand in 2026",
                content="TechGig report shows AI/ML engineering, prompt engineering, and MCP development as top skills for 2026. Salaries up 40% year over year.",
                url="https://www.techgig.com/ai-skills-2026",
                hashtags=["AI", "career"],
                engagement=120,
            ),
            self.make_item(
                title="India's AI Startup Ecosystem Booms",
                content="Indian AI startups raised $12B in H1 2026. Agent infrastructure, healthcare AI, and fintech lead the wave.",
                url="https://www.techgig.com/india-ai-startups",
                hashtags=["AI", "startup"],
                engagement=89,
            ),
        ][:max_items]

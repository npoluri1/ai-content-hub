"""LinkedIn collector — Playwright scraper + Proxycurl API (optional)."""

from ...core.base_collector import BaseCollector
from ...core.models import ContentItem
from ...core.config import settings
from datetime import datetime
import re


class LinkedInCollector(BaseCollector):
    name = "linkedin"
    source_type = "post"

    def collect(self, max_items: int = 100) -> list[ContentItem]:
        if settings.LINKEDIN_PROXYCURL_API_KEY:
            return self._collect_proxycurl(max_items)
        if settings.LINKEDIN_EMAIL and settings.LINKEDIN_PASSWORD:
            return self._collect_playwright(max_items)
        return self._collect_demo_fallback(max_items)

    def _collect_proxycurl(self, max_items: int) -> list[ContentItem]:
        import httpx
        results = []
        search_queries = [
            "artificial intelligence", "AI agents", "LangGraph", "RAG",
            "MCP protocol", "quantum computing", "robotics", "LLM"
        ]
        with httpx.Client(timeout=30) as client:
            for query in search_queries[:3]:
                try:
                    resp = client.get(
                        "https://nubela.co/proxycurl/api/v2/search/posts",
                        params={"query": query, "count": min(20, max_items)},
                        headers={"Authorization": f"Bearer {settings.LINKEDIN_PROXYCURL_API_KEY}"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for post in data.get("posts", []):
                            results.append(self._parse_post(post))
                except Exception as e:
                    print(f"  [LinkedIn-Proxycurl] Error: {e}")
        return results[:max_items]

    def _collect_playwright(self, max_items: int) -> list[ContentItem]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("  [LinkedIN] playwright not installed. Install: pip install playwright && playwright install chromium")
            return self._collect_demo_fallback(max_items)

        results = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto("https://www.linkedin.com/login")
                page.fill("#username", settings.LINKEDIN_EMAIL)
                page.fill("#password", settings.LINKEDIN_PASSWORD)
                page.click("button[type=submit]")
                page.wait_for_timeout(5000)

                hashtags = ["AI", "AgenticAI", "LangGraph", "RAG", "MCP", "QuantumComputing", "Robotics", "LLM"]
                for tag in hashtags[:3]:
                    page.goto(f"https://www.linkedin.com/feed/hashtag/{tag}/")
                    page.wait_for_timeout(3000)
                    posts = page.query_selector_all("div.feed-shared-update-v2")
                    for post in posts[:10]:
                        text = post.inner_text()
                        results.append(self.make_item(
                            title=f"LinkedIn #{tag} post",
                            content=text,
                            hashtags=[tag],
                            engagement=0,
                        ))
            except Exception as e:
                print(f"  [LinkedIn-Playwright] Error: {e}")
            finally:
                browser.close()
        return results[:max_items]

    def _collect_demo_fallback(self, max_items: int) -> list[ContentItem]:
        from ..demo.demo_collector import DEMO_DATA
        items = DEMO_DATA.get("linkedin", [])
        for item in items:
            item.content_cleaned = self.clean_content(item.content)
        return items[:max_items]

    def _parse_post(self, raw: dict) -> ContentItem:
        text = raw.get("text", raw.get("content", ""))
        hashtags = re.findall(r"#(\w+)", text)
        topics = self._detect_topics(text, hashtags)
        return ContentItem(
            id=self.make_id("linkedin", raw.get("url", text[:80])),
            title=text[:100],
            content=text,
            content_cleaned=self.clean_content(text),
            url=raw.get("url", ""),
            source="linkedin",
            source_type="post",
            author_name=raw.get("author", {}).get("name", ""),
            author_url=raw.get("author", {}).get("url", ""),
            hashtags=hashtags,
            topics=topics,
            engagement=raw.get("likes", raw.get("engagement", 0)),
            published_at=self._parse_date(raw.get("date", "")),
        )

    def _detect_topics(self, text: str, hashtags: list[str]) -> list[str]:
        text_lower = (text + " " + " ".join(hashtags)).lower()
        topics = []
        mapping = {
            "AI": ["ai ", "artificial intelligence", "machine learning", "deep learning", "gpt", "llm", "neural"],
            "AgenticAI": ["agent", "langgraph", "autogen", "crewai", "multi-agent", "agentic"],
            "AI_Frameworks": ["langchain", "llamaindex", "haystack", "fastapi", "pytorch", "tensorflow"],
            "Quantum_Computing": ["quantum", "qbit", "qubit", "willow", "qiskit"],
            "Robotics": ["robot", "robotics", "humanoid", "ros ", "automation"],
            "RAG": ["rag", "retrieval", "vector", "chromadb", "qdrant", "embedding"],
            "MCP": ["mcp", "model context protocol", "tool calling", "function calling"],
            "LLM_Ops": ["fine-tune", "fine tune", "guardrail", "observability", "langfuse", "deploy"],
        }
        for topic, keywords in mapping.items():
            if any(k in text_lower for k in keywords):
                topics.append(topic)
        return topics

    def _parse_date(self, date_str: str):
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None

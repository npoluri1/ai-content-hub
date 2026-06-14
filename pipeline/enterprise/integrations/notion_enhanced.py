from ...core.config import settings
from ...core.models import ContentItem, ClassifiedItem
from typing import Optional
import httpx, json, os, logging, time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"


class NotionEnhanced:
    def __init__(self, api_key: str = None, database_id: str = None):
        self.api_key = api_key or getattr(settings, "NOTION_API_KEY", None) or ""
        self.database_id = database_id or getattr(settings, "NOTION_DATABASE_ID", None) or ""
        self.api_base = "https://api.notion.com/v1"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        if not self.api_key:
            return {}
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    def _request(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        if not self.api_key:
            logger.warning("Notion API key not configured")
            return None
        url = f"{self.api_base}{path}"
        try:
            resp = self._client.request(method, url, headers=self._headers(), json=data)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 3))
                logger.warning(f"Notion rate limited, retrying after {retry_after}s")
                time.sleep(retry_after)
                return self._request(method, path, data)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except httpx.HTTPError as e:
            logger.error(f"Notion request failed: {e}")
            return {"error": str(e)}

    def _build_text_block(self, text: str, block_type: str = "paragraph") -> dict:
        return {
            "object": "block",
            "type": block_type,
            block_type: {
                "rich_text": [{"type": "text", "text": {"content": text[:2000]}}],
            },
        }

    def create_content_page(self, item: ContentItem) -> Optional[str]:
        props = {
            "Title": {
                "title": [{"type": "text", "text": {"content": item.title[:2000]}}],
            },
            "Source": {
                "select": {"name": item.source.capitalize()},
            },
            "Topics": {
                "multi_select": [{"name": t[:100]} for t in item.topics[:20]],
            },
            "Status": {
                "status": {"name": "New"},
            },
            "Relevance": {
                "number": round(item.relevance_score, 2),
            },
            "URL": {
                "url": item.url if item.url else None,
            },
        }
        if item.published_at:
            props["Published Date"] = {
                "date": {"start": item.published_at.isoformat()}
            }
        body = {
            "parent": {"database_id": self.database_id},
            "properties": props,
            "children": [],
        }
        if item.image_urls:
            body["cover"] = {"type": "external", "external": {"url": item.image_urls[0]}}
        content_text = item.content_cleaned or item.content
        chunks = [content_text[i:i + 1900] for i in range(0, len(content_text), 1900)]
        for chunk in chunks[:50]:
            body["children"].append(self._build_text_block(chunk))
        if item.url:
            body["children"].append(self._build_text_block(f"Read more: {item.url}"))
        result = self._request("POST", "/pages", body)
        if result and "id" in result:
            logger.info(f"Created Notion page for '{item.title[:50]}...' (ID: {result['id']})")
            return result["id"]
        return None

    def create_digest_database(self, digest_items: list[ContentItem], title: str = None) -> Optional[str]:
        db_title = title or f"Content Digest {datetime.now().strftime('%Y-%m-%d')}"
        body = {
            "parent": {"type": "page_id", "page_id": self.database_id},
            "title": [{"type": "text", "text": {"content": db_title}}],
            "properties": {
                "Title": {"title": {}},
                "Source": {"select": {}},
                "Topics": {"multi_select": {}},
                "Status": {"status": {}},
                "Relevance": {"number": {}},
                "URL": {"url": {}},
                "Published Date": {"date": {}},
            },
        }
        result = self._request("POST", "/databases", body)
        if not result or "id" not in result:
            logger.error("Failed to create digest database")
            return None
        db_id = result["id"]
        for item in digest_items:
            self.database_id = db_id
            self.create_content_page(item)
        self.database_id = settings.NOTION_DATABASE_ID or self.database_id
        logger.info(f"Created digest database '{db_title}' (ID: {db_id}) with {len(digest_items)} items")
        return db_id

    def update_page_properties(self, page_id: str, properties: dict) -> bool:
        result = self._request("PATCH", f"/pages/{page_id}", {"properties": properties})
        return result is not None and "error" not in result

    def query_database(self, filter_dict: dict = None, sorts: list = None) -> list[dict]:
        body = {"page_size": 100}
        if filter_dict:
            body["filter"] = filter_dict
        if sorts:
            body["sorts"] = sorts
        results = []
        cursor = None
        while True:
            if cursor:
                body["start_cursor"] = cursor
            resp = self._request("POST", f"/databases/{self.database_id}/query", body)
            if not resp:
                break
            results.extend(resp.get("results", []))
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        return results

    def archive_old_pages(self, days_old: int = 30, database_id: str = None) -> int:
        target_db = database_id or self.database_id
        cutoff = (datetime.now() - timedelta(days=days_old)).isoformat()
        filter_dict = {
            "property": "Published Date",
            "date": {"before": cutoff},
        }
        sorts = [{"property": "Published Date", "direction": "ascending"}]
        body = {"page_size": 100, "filter": filter_dict, "sorts": sorts}
        archived = 0
        cursor = None
        while True:
            qbody = dict(body)
            if cursor:
                qbody["start_cursor"] = cursor
            resp = self._request("POST", f"/databases/{target_db}/query", qbody)
            if not resp:
                break
            for page in resp.get("results", []):
                page_id = page["id"]
                result = self._request("PATCH", f"/pages/{page_id}", {"archived": True})
                if result and "error" not in result:
                    archived += 1
            if not resp.get("has_more"):
                break
            cursor = resp.get("next_cursor")
        logger.info(f"Archived {archived} pages older than {days_old} days")
        return archived

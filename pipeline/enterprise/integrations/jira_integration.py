from ...core.config import settings
from ...core.models import ContentItem, ClassifiedItem
from typing import Optional
import httpx, json, os, logging, base64

logger = logging.getLogger(__name__)

PRIORITY_MAP = {
    0.0: "Low", 0.2: "Low", 0.4: "Medium", 0.6: "Medium",
    0.8: "High", 1.0: "Highest",
}


class JiraIntegration:
    def __init__(self, base_url: str = None, email: str = None, api_token: str = None, project_key: str = None):
        self.base_url = (base_url or getattr(settings, "JIRA_BASE_URL", None) or "").rstrip("/")
        self.email = email or getattr(settings, "JIRA_EMAIL", None) or ""
        self.api_token = api_token or getattr(settings, "JIRA_API_TOKEN", None) or ""
        self.project_key = project_key or getattr(settings, "JIRA_PROJECT_KEY", None) or ""
        self.api_base = f"{self.base_url}/rest/api/3"
        auth_str = f"{self.email}:{self.api_token}"
        self._auth_header = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        return {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        if not self.base_url or not self.email or not self.api_token:
            logger.warning("Jira integration not fully configured")
            return None
        url = f"{self.api_base}{path}"
        try:
            resp = self._client.request(method, url, headers=self._headers(), json=data)
            if resp.status_code == 401:
                logger.error("Jira auth failed - check email and API token")
                return {"error": "Authentication failed"}
            if resp.status_code == 404:
                logger.warning(f"Jira resource not found: {path}")
                return None
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except httpx.HTTPError as e:
            logger.error(f"Jira request failed: {e}")
            return {"error": str(e)}

    def create_issue_from_item(self, item: ContentItem, issue_type: str = "Task", priority: str = None) -> Optional[dict]:
        if not priority:
            score = min(max(item.relevance_score, 0.0), 1.0)
            rounded = round(score * 2) / 2
            priority = PRIORITY_MAP.get(rounded, "Medium")
        summary = item.title[:255]
        description = f"{item.content_cleaned or item.content}\n\n---\n*Original:* {item.url}\n*Source:* {item.source}\n*Published:* {item.published_at}"
        labels = list(item.topics) + [item.source]
        if item.hashtags:
            labels.extend(item.hashtags)
        labels = [l.replace(" ", "_").lower()[:50] for l in labels if l]
        return self.create_issue(summary, description, issue_type, priority, labels)

    def create_issue(self, summary: str, description: str, issue_type: str, priority: str, labels: list[str] = None) -> Optional[dict]:
        fields = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
        }
        if labels:
            fields["labels"] = labels
        return self._request("POST", "/issue", {"fields": fields})

    def search_issues(self, jql: str) -> list[dict]:
        result = self._request("POST", "/search", {"jql": jql, "maxResults": 50})
        if result and "issues" in result:
            return result["issues"]
        return []

    def add_comment(self, issue_key: str, comment: str) -> Optional[dict]:
        body = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment}],
                    }
                ],
            }
        }
        return self._request("POST", f"/issue/{issue_key}/comment", body)

    def find_or_create_sprint(self, sprint_name: str) -> Optional[dict]:
        boards_result = self._request("GET", "/board")
        if not boards_result:
            return None
        boards = boards_result.get("values", [])
        for board in boards:
            sprints_result = self._request("GET", f"/board/{board['id']}/sprint")
            if sprints_result:
                for sprint in sprints_result.get("values", []):
                    if sprint.get("name") == sprint_name and sprint.get("state") in ("active", "future"):
                        return sprint
        if boards:
            board_id = boards[0]["id"]
            return self._request("POST", f"/board/{board_id}/sprint", {
                "name": sprint_name,
                "startDate": os.popen("date /T 2>nul").read().strip() or "",
                "endDate": "",
            })
        return None

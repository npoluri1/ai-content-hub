from ...core.config import settings
from ...core.models import ContentItem
from typing import Optional
import httpx, json, os, logging

logger = logging.getLogger(__name__)


class GitHubIntegration:
    def __init__(self, token: str = None, repo_owner: str = "", repo_name: str = ""):
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self.repo_owner = repo_owner or ""
        self.repo_name = repo_name or ""
        self.base_url = "https://api.github.com"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        if not self.token:
            logger.warning("GitHub token not configured")
            return None
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(3):
            try:
                resp = self._client.request(method, url, headers=self._headers(), json=data)
                if resp.status_code == 403 and "rate limit" in resp.text.lower():
                    logger.warning("GitHub API rate limited")
                    import time
                    time.sleep(60)
                    continue
                if resp.status_code == 401:
                    logger.error("GitHub token invalid or expired")
                    return {"error": "Authentication failed"}
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.HTTPError as e:
                logger.error(f"GitHub request failed: {e}")
                if attempt == 2:
                    return {"error": str(e)}
                import time
                time.sleep(1)
        return {"error": "Max retries exceeded"}

    def create_issue_from_item(self, item: ContentItem, labels: list[str] = None) -> dict:
        title = item.title[:256]
        body_parts = [
            f"## {item.title}",
            "",
            f"**Source:** {item.source}",
            f"**URL:** {item.url}",
            f"**Published:** {item.published_at or 'N/A'}",
            f"**Relevance Score:** {item.relevance_score:.2f}",
            f"**Engagement:** {item.engagement}",
            "",
            "---",
            "",
            item.content_cleaned or item.content,
        ]
        body = "\n".join(body_parts)
        all_labels = list(item.topics) + [item.source]
        if item.hashtags:
            all_labels.extend(item.hashtags)
        if labels:
            all_labels.extend(labels)
        all_labels = [l.replace(" ", "_").lower()[:40] for l in all_labels if l]
        return self.create_issue(title, body, all_labels)

    def create_issue(self, title: str, body: str, labels: list[str] = None, assignees: list[str] = None) -> dict:
        if not self.repo_owner or not self.repo_name:
            logger.warning("GitHub repo_owner and repo_name must be set")
            return {"error": "Repository not configured"}
        data = {"title": title, "body": body}
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
        result = self._request("POST", f"repos/{self.repo_owner}/{self.repo_name}/issues", data)
        return result or {"error": "Failed to create issue"}

    def search_repositories(self, query: str, limit: int = 10) -> list[dict]:
        result = self._request("GET", f"search/repositories?q={query}&per_page={limit}&sort=stars&order=desc")
        if result and "items" in result:
            repos = []
            for r in result["items"][:limit]:
                repos.append({
                    "id": r.get("id"),
                    "name": r.get("full_name"),
                    "description": r.get("description"),
                    "url": r.get("html_url"),
                    "stars": r.get("stargazers_count"),
                    "forks": r.get("forks_count"),
                    "language": r.get("language"),
                    "topics": r.get("topics", []),
                    "updated_at": r.get("updated_at"),
                })
            return repos
        return []

    def search_code(self, query: str, repo: str = None) -> list[dict]:
        q = f"{query} repo:{repo}" if repo else query
        result = self._request("GET", f"search/code?q={q}&per_page=10")
        if result and "items" in result:
            snippets = []
            for s in result["items"][:10]:
                snippets.append({
                    "name": s.get("name"),
                    "path": s.get("path"),
                    "repository": s.get("repository", {}).get("full_name"),
                    "url": s.get("html_url"),
                })
            return snippets
        return []

    def get_trending_repos(self, topic: str = "ai", limit: int = 10) -> list[dict]:
        query = f"topic:{topic} stars:>100"
        result = self._request("GET", f"search/repositories?q={query}&per_page={limit}&sort=stars&order=desc")
        if result and "items" in result:
            repos = []
            for r in result["items"][:limit]:
                repos.append({
                    "id": r.get("id"),
                    "name": r.get("full_name"),
                    "description": r.get("description"),
                    "url": r.get("html_url"),
                    "stars": r.get("stargazers_count"),
                    "forks": r.get("forks_count"),
                    "language": r.get("language"),
                    "topics": r.get("topics", []),
                })
            return repos
        return []

    def create_gist(self, filename: str, content: str, description: str = "", public: bool = False) -> dict:
        data = {
            "description": description,
            "public": public,
            "files": {filename: {"content": content}},
        }
        result = self._request("POST", "gists", data)
        return result or {"error": "Failed to create gist"}

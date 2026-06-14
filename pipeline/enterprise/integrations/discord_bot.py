from ...core.config import settings
from ...core.models import ContentItem
from typing import Optional
import httpx, json, os, logging

logger = logging.getLogger(__name__)

SEVERITY_COLORS = {
    "info": 0x36A64F,
    "success": 0x00FF00,
    "warning": 0xFFCC00,
    "error": 0xDC3545,
    "danger": 0xDC3545,
    "critical": 0xFF0000,
}

SEVERITY_EMOJIS = {
    "info": "\u2139\ufe0f",
    "success": "\u2705",
    "warning": "\u26a0\ufe0f",
    "error": "\U0001f6a8",
    "danger": "\U0001f6a8",
    "critical": "\U0001f525",
}

SOURCE_EMOJIS = {
    "linkedin": "\U0001f4bc", "reddit": "\U0001f916", "techcrunch": "\U0001f4f0",
    "techgig": "\U0001f4bb", "arxiv": "\U0001f4c4", "youtube": "\U0001f3a5",
    "hackernews": "\U0001f431", "medium": "\u270d\ufe0f", "rss": "\U0001f4e1",
    "newsapi": "\U0001f310", "devto": "\U0001f468\u200d\U0001f4bb",
}


class DiscordBot:
    def __init__(self, bot_token: str = None, guild_id: str = None):
        self.bot_token = bot_token or os.environ.get("DISCORD_BOT_TOKEN", "")
        self.guild_id = guild_id or ""
        self.base_url = "https://discord.com/api/v10"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        if not self.bot_token:
            logger.warning("Discord bot token not configured")
            return None
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(3):
            try:
                resp = self._client.request(method, url, headers=self._headers(), json=data)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Discord rate limited, retrying after {retry_after}s")
                    import time
                    time.sleep(retry_after)
                    continue
                if resp.status_code == 401:
                    logger.error("Discord bot token invalid")
                    return {"error": "Authentication failed"}
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.HTTPError as e:
                logger.error(f"Discord request failed: {e}")
                if attempt == 2:
                    return {"error": str(e)}
                import time
                time.sleep(1)
        return {"error": "Max retries exceeded"}

    def send_message(self, channel_id: str, content: str, embed: dict = None) -> dict:
        data = {"content": content[:2000]}
        if embed:
            data["embeds"] = [embed]
        result = self._request("POST", f"channels/{channel_id}/messages", data)
        return result or {"error": "Failed to send message"}

    def send_content_embed(self, channel_id: str, item: ContentItem) -> dict:
        emoji = SOURCE_EMOJIS.get(item.source, "\U0001f4cc")
        snippet = item.content_cleaned or item.content
        description = snippet[:400] + ("..." if len(snippet) > 400 else "")

        fields = [
            {"name": "Source", "value": f"{emoji} {item.source}", "inline": True},
            {"name": "Score", "value": f"{item.relevance_score:.2f}", "inline": True},
            {"name": "Engagement", "value": str(item.engagement), "inline": True},
        ]
        if item.topics:
            fields.append({"name": "Topics", "value": " | ".join(f"`{t}`" for t in item.topics[:8]), "inline": False})

        embed = {
            "title": item.title[:256],
            "description": description,
            "color": 0x58A6FF,
            "footer": {"text": f"AI Content Hub \u2022 {item.source}"},
            "timestamp": item.published_at.isoformat() if item.published_at else None,
            "fields": fields,
        }
        if item.url:
            embed["url"] = item.url
        if item.image_urls:
            embed["image"] = {"url": item.image_urls[0]}

        return self.send_message(channel_id, f"**{emoji} New Content: {item.title}**", embed)

    def send_digest(self, channel_id: str, digest_text: str, topic: str = None, max_len: int = 2000) -> dict:
        topic_suffix = f" \u2014 {topic}" if topic else ""
        header = f"\U0001f4cb **Daily Digest{topic_suffix}**"
        if len(digest_text) <= max_len:
            data = {"content": f"{header}\n\n{digest_text}"}
            return self._request("POST", f"channels/{channel_id}/messages", data) or {"error": "Failed"}

        parts = []
        remaining = digest_text
        while remaining:
            split_at = remaining.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            parts.append(remaining[:split_at])
            remaining = remaining[split_at:].lstrip()

        last_result = {"error": "No parts sent"}
        for i, part in enumerate(parts):
            prefix = f"{header} ({i + 1}/{len(parts)})" if i == 0 else f"(continued {i + 1}/{len(parts)})"
            content = f"{prefix}\n\n{part}"
            data = {"content": content[:2000]}
            last_result = self._request("POST", f"channels/{channel_id}/messages", data)
        return last_result or {"error": "Failed to send digest"}

    def send_alert(self, channel_id: str, title: str, description: str, severity: str = "info", footer: str = None) -> dict:
        color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["info"])
        emoji = SEVERITY_EMOJIS.get(severity, "\u2139\ufe0f")
        embed = {
            "title": f"{emoji} {title}",
            "description": description,
            "color": color,
            "footer": {"text": footer or f"Severity: {severity} | AI Content Hub"},
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        return self.send_message(channel_id, f"{emoji} **{title}**", embed)

    def create_thread(self, channel_id: str, name: str, message: str) -> dict:
        msg_result = self.send_message(channel_id, message)
        if not msg_result or "id" not in msg_result:
            return {"error": "Failed to create base message"}
        message_id = msg_result["id"]
        data = {"name": name[:100], "message_id": message_id, "auto_archive_duration": 1440}
        result = self._request("POST", f"channels/{channel_id}/messages/{message_id}/threads", data)
        return result or {"error": "Failed to create thread"}

    def add_reaction(self, channel_id: str, message_id: str, emoji: str) -> bool:
        encoded = __import__("urllib.parse").quote(emoji, safe="")
        result = self._request("PUT", f"channels/{channel_id}/messages/{message_id}/reactions/{encoded}/@me")
        return result is not None and "error" not in result

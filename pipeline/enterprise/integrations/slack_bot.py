from ...core.config import settings
from ...core.models import ContentItem, ClassifiedItem
from typing import Optional
import httpx, json, os, logging

logger = logging.getLogger(__name__)

SOURCE_EMOJIS = {
    "linkedin": "\U0001f4bc", "reddit": "\U0001f916", "techcrunch": "\U0001f4f0",
    "techgig": "\U0001f4bb", "arxiv": "\U0001f4c4", "youtube": "\U0001f3a5",
    "hackernews": "\U0001f431", "medium": "\u270d\ufe0f", "rss": "\U0001f4e1",
    "newsapi": "\U0001f310", "devto": "\U0001f468\u200d\U0001f4bb",
}

SEVERITY_COLORS = {
    "info": "#36a64f", "warning": "#ffcc00", "error": "#dc3545",
    "danger": "#dc3545", "critical": "#ff0000",
}


class SlackBot:
    def __init__(self, bot_token: str = None, signing_secret: str = None):
        self.bot_token = bot_token or getattr(settings, "SLACK_BOT_TOKEN", None)
        self.signing_secret = signing_secret or getattr(settings, "SLACK_SIGNING_SECRET", None)
        self.base_url = "https://slack.com/api"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        if not self.bot_token:
            logger.warning("Slack bot token not configured")
            return None
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(3):
            try:
                resp = self._client.request(method, url, headers=self._headers(), json=data)
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 5))
                    logger.warning(f"Rate limited, retrying after {retry_after}s")
                    import time
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                result = resp.json()
                if not result.get("ok"):
                    logger.error(f"Slack API error: {result.get('error')}")
                return result
            except httpx.HTTPError as e:
                logger.error(f"Slack request failed: {e}")
                if attempt == 2:
                    return {"ok": False, "error": str(e)}
                import time
                time.sleep(1)
        return {"ok": False, "error": "Max retries exceeded"}

    def send_message(self, channel: str, text: str, blocks: list = None) -> Optional[dict]:
        data = {"channel": channel, "text": text}
        if blocks:
            data["blocks"] = blocks
        return self._request("POST", "chat.postMessage", data)

    def send_content_item(self, channel: str, item: ContentItem) -> Optional[dict]:
        emoji = SOURCE_EMOJIS.get(item.source, "\U0001f4cc")
        snippet = item.content_cleaned or item.content
        snippet = snippet[:297] + "..." if len(snippet) > 300 else snippet

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {item.title[:100]}", "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": snippet},
            },
        ]

        if item.topics:
            tag_text = " | ".join(f"`{t}`" for t in item.topics[:8])
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"*Topics:* {tag_text}"}],
            })

        if item.hashtags:
            hashtag_str = " ".join(f"#{h}" for h in item.hashtags[:10])
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": hashtag_str}],
            })

        blocks.append({
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Source:* {item.source}"},
                {"type": "mrkdwn", "text": f"*Score:* {item.relevance_score:.2f}"},
                {"type": "mrkdwn", "text": f"*Engagement:* {item.engagement}"},
            ],
        })

        actions = []
        if item.url:
            actions.append({
                "type": "button",
                "text": {"type": "plain_text", "text": "View Original", "emoji": True},
                "url": item.url,
                "action_id": "view_original",
            })
        actions.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Summarize", "emoji": True},
            "action_id": "summarize",
            "value": item.id,
        })
        actions.append({
            "type": "button",
            "text": {"type": "plain_text", "text": "Save to Workspace", "emoji": True},
            "action_id": "save_workspace",
            "value": item.id,
        })
        blocks.append({"type": "actions", "elements": actions})

        return self.send_message(channel, f"New: {item.title}", blocks)

    def send_digest(self, channel: str, digest_text: str, topic: str = None) -> Optional[dict]:
        topic_suffix = f" \u2014 {topic}" if topic else ""
        header_text = f"\U0001f4cb Daily Digest{topic_suffix}"
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": header_text, "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": digest_text[:3000]},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "Generated by AI Content Hub"}],
            },
        ]
        return self.send_message(channel, header_text, blocks)

    def send_alert(self, channel: str, alert_type: str, message: str, severity: str = "info") -> Optional[dict]:
        color = SEVERITY_COLORS.get(severity, "#36a64f")
        emoji_map = {"info": "\u2139\ufe0f", "warning": "\u26a0\ufe0f", "error": "\U0001f6a8", "danger": "\U0001f6a8", "critical": "\U0001f525"}
        emoji = emoji_map.get(severity, "\u2139\ufe0f")
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"{emoji} {alert_type.upper()}", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"Severity: *{severity}* | `{color}`"}],
            },
        ]
        return self.send_message(channel, f"[{severity.upper()}] {alert_type}: {message}", blocks)

    def open_modal(self, trigger_id: str, modal_view: dict) -> Optional[dict]:
        return self._request("POST", "views.open", {
            "trigger_id": trigger_id,
            "view": modal_view,
        })

    def respond_to_action(self, payload: dict) -> dict:
        action = payload.get("actions", [{}])[0] if payload.get("actions") else {}
        action_id = action.get("action_id", "")
        if action_id == "summarize":
            return {
                "response_action": "update",
                "view": {
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Summarize"},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Summarizing item `{action.get('value')}`\n\nThis may take a moment...",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [{"type": "mrkdwn", "text": "AI Content Hub"}],
                        },
                    ],
                },
            }
        elif action_id == "save_workspace":
            return {
                "response_action": "update",
                "view": {
                    "type": "modal",
                    "title": {"type": "plain_text", "text": "Saved"},
                    "close": {"type": "plain_text", "text": "Close"},
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Item `{action.get('value')}` has been saved to workspace.",
                            },
                        },
                    ],
                },
            }
        elif action_id == "view_original":
            return {"text": "Opening original link\u2026"}
        return {"text": f"Action `{action_id}` received"}

    def parse_slash_command(self, payload: dict) -> dict:
        command = payload.get("command", "")
        text = payload.get("text", "")
        channel_id = payload.get("channel_id", "")
        if command == "/search":
            return {
                "response_type": "ephemeral",
                "text": f"Searching for: *{text}*",
            }
        elif command == "/digest":
            return {
                "response_type": "in_channel",
                "text": f"Generating digest for topic: *{text or 'all'}*",
            }
        elif command == "/summarize":
            return {
                "response_type": "ephemeral",
                "text": f"Summarizing: *{text}*",
            }
        elif command == "/alert":
            parts = text.split(" ", 1)
            severity = parts[0] if parts else "info"
            message = parts[1] if len(parts) > 1 else "No message"
            self.send_alert(channel_id, "Slash Alert", message, severity)
            return {"response_type": "ephemeral", "text": f"Alert sent ({severity})"}
        return {"text": f"Unknown command: `{command}`"}

    def register_commands(self, app):
        if hasattr(app, "command"):
            @app.command("/search")
            def handle_search(ack, command):
                ack()
                return self.parse_slash_command(command)

            @app.command("/digest")
            def handle_digest(ack, command):
                ack()
                return self.parse_slash_command(command)

            @app.command("/summarize")
            def handle_summarize(ack, command):
                ack()
                return self.parse_slash_command(command)

            @app.command("/alert")
            def handle_alert(ack, command):
                ack()
                return self.parse_slash_command(command)

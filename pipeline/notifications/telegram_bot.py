import logging
from typing import Optional, Callable

import httpx

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"
MAX_MSG_LENGTH = 4096


class TelegramNotifier:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)
        self._http_client: Optional[httpx.Client] = None

    @property
    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=15.0)
        return self._http_client

    def _call(self, method: str, **kwargs) -> Optional[dict]:
        if not self.bot_token:
            logger.warning("Telegram bot_token not configured")
            return None
        url = TELEGRAM_API_BASE.format(token=self.bot_token, method=method)
        payload = {"chat_id": self.chat_id, **kwargs}
        try:
            resp = self._client.post(url, json=payload, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                logger.error("Telegram API error: %s", data.get("description"))
                return None
            return data
        except httpx.HTTPError as e:
            logger.error("Telegram HTTP error: %s", e)
            return None

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        if not self.bot_token:
            logger.info("Telegram message not sent (no bot_token): %s chars", len(text))
            return False
        result = self._call("sendMessage", text=text, parse_mode=parse_mode)
        return result is not None

    def send_digest(self, digest_text: str) -> bool:
        if not self.bot_token:
            logger.info("Telegram digest not sent (no bot_token): %s chars", len(digest_text))
            return False
        if len(digest_text) <= MAX_MSG_LENGTH:
            return self.send_message(digest_text, parse_mode="Markdown")

        chunks = []
        start = 0
        while start < len(digest_text):
            end = start + MAX_MSG_LENGTH
            if end >= len(digest_text):
                chunks.append(digest_text[start:])
                break
            split_at = digest_text.rfind("\n", start, end)
            if split_at <= start:
                split_at = digest_text.rfind(" ", start, end)
                if split_at <= start:
                    split_at = end
            chunks.append(digest_text[start:split_at])
            start = split_at + 1

        success = True
        for i, chunk in enumerate(chunks):
            header = f"📄 *Digest ({i+1}/{len(chunks)})*\n\n" if len(chunks) > 1 else ""
            ok = self.send_message(header + chunk, parse_mode="Markdown")
            if not ok:
                success = False
        return success

    def send_item(self, item: ContentItem) -> bool:
        if not self.bot_token:
            return False
        snippet = (item.content_cleaned or item.content)[:300]
        if len(snippet) == 300:
            snippet = snippet.rsplit(" ", 1)[0] + "..."
        hashtags_str = " ".join(f"#{h}" for h in item.hashtags[:5]) if item.hashtags else ""
        text = (
            f"*{item.title}*\n\n"
            f"_{item.source}_ | _{item.source_type}_\n\n"
            f"{snippet}\n\n"
        )
        if hashtags_str:
            text += f"{hashtags_str}\n\n"
        text += f"[Read more]({item.url})"
        return self.send_message(text, parse_mode="Markdown")

    def send_photo(self, image_url: str, caption: str = "") -> bool:
        if not self.bot_token:
            return False
        payload = {"chat_id": self.chat_id, "photo": image_url}
        if caption:
            payload["caption"] = caption
        result = self._call("sendPhoto", **payload)
        return result is not None

    def send_topic_summary(self, topic: str, items: list[ContentItem]) -> bool:
        if not self.bot_token:
            return False
        text = f"*{topic.replace('_', ' ').title()}*\n\n"
        for i, item in enumerate(items[:8], 1):
            snippet = (item.content_cleaned or item.content)[:100]
            if len(snippet) == 100:
                snippet = snippet.rsplit(" ", 1)[0] + "..."
            text += f"{i}. *{item.title}*\n  {snippet}\n  [{item.source}]({item.url})\n\n"
        return self.send_message(text, parse_mode="Markdown")

    def start_polling(self, message_handler: Optional[Callable] = None):
        if not self.bot_token:
            logger.error("Cannot start polling: bot_token not configured")
            return
        logger.info("Starting Telegram polling (long-poll mode)...")
        last_update_id = 0
        default_handler = lambda msg: logger.info("Received: %s", msg.get("text"))
        handler = message_handler or default_handler
        try:
            while True:
                url = TELEGRAM_API_BASE.format(token=self.bot_token, method="getUpdates")
                params = {"offset": last_update_id + 1, "timeout": 30}
                try:
                    resp = self._client.get(url, params=params, timeout=35.0)
                    resp.raise_for_status()
                    data = resp.json()
                    if not data.get("ok"):
                        continue
                    for update in data.get("result", []):
                        last_update_id = update["update_id"]
                        message = update.get("message")
                        if message:
                            handler(message)
                except httpx.TimeoutException:
                    continue
                except httpx.HTTPError as e:
                    logger.error("Polling HTTP error: %s", e)
        except KeyboardInterrupt:
            logger.info("Telegram polling stopped")

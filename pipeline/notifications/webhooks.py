import hashlib
import hmac
import json
import logging
import os
from typing import Optional

import httpx

from ..core.config import settings
from ..core.models import ContentItem, ClassifiedItem

logger = logging.getLogger(__name__)

VALID_EVENTS = {"new_item", "digest", "alert", "source_complete"}


class WebhookDispatcher:
    def __init__(self):
        self._webhooks: dict[str, dict] = {}
        self._config_path = os.path.join(settings.DATA_DIR, "webhooks.json")
        self._http_client: Optional[httpx.Client] = None

    @property
    def _client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=10.0)
        return self._http_client

    def register(
        self,
        name: str,
        url: str,
        events: list[str],
        secret: str = None,
        headers: dict = None,
    ):
        invalid = [e for e in events if e not in VALID_EVENTS]
        if invalid:
            raise ValueError(f"Invalid event(s): {invalid}. Valid: {VALID_EVENTS}")
        self._webhooks[name] = {
            "url": url,
            "events": list(events),
            "secret": secret,
            "headers": headers or {},
        }
        logger.info("Webhook '%s' registered for events: %s", name, events)

    def unregister(self, name: str):
        self._webhooks.pop(name, None)
        logger.info("Webhook '%s' unregistered", name)

    def dispatch(self, event: str, payload: dict) -> list[dict]:
        results = []
        for name, config in self._webhooks.items():
            if event not in config["events"]:
                continue
            result = self._send_webhook(
                url=config["url"],
                payload=payload,
                headers=config.get("headers"),
                secret=config.get("secret"),
            )
            result["name"] = name
            results.append(result)
        logger.info("Dispatched event '%s' to %d webhooks", event, len(results))
        return results

    def dispatch_new_item(self, item: ContentItem) -> list[dict]:
        payload = {
            "event": "new_item",
            "item": item.model_dump(mode="json"),
        }
        return self.dispatch("new_item", payload)

    def dispatch_digest(self, digest_text: str, topic: str = None) -> list[dict]:
        payload = {
            "event": "digest",
            "digest": digest_text[:5000],
            "topic": topic,
        }
        return self.dispatch("digest", payload)

    def dispatch_alert(self, topic: str, item: ContentItem) -> list[dict]:
        payload = {
            "event": "alert",
            "topic": topic,
            "item": item.model_dump(mode="json"),
        }
        return self.dispatch("alert", payload)

    def _sign_payload(self, payload: dict, secret: str) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        sig = hmac.new(
            secret.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return sig

    def _send_webhook(
        self,
        url: str,
        payload: dict,
        headers: dict = None,
        secret: str = None,
    ) -> dict:
        result = {"status_code": None, "success": False, "error": None}
        merged_headers = dict(headers or {})
        merged_headers.setdefault("Content-Type", "application/json")

        if secret:
            sig = self._sign_payload(payload, secret)
            merged_headers["X-Webhook-Signature"] = sig

        try:
            resp = self._client.post(url, json=payload, headers=merged_headers, timeout=10.0)
            result["status_code"] = resp.status_code
            if 200 <= resp.status_code < 300:
                result["success"] = True
            else:
                result["error"] = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except httpx.TimeoutException:
            result["error"] = "Request timed out after 10s"
        except httpx.HTTPError as e:
            result["error"] = str(e)
        except Exception as e:
            result["error"] = str(e)

        return result

    def load_from_config(self):
        webhook_urls_raw = getattr(settings, "WEBHOOK_URLS", None)
        if webhook_urls_raw:
            try:
                entries = json.loads(webhook_urls_raw)
                for entry in entries:
                    self.register(
                        name=entry.get("name", entry["url"]),
                        url=entry["url"],
                        events=entry.get("events", ["new_item"]),
                        secret=entry.get("secret"),
                        headers=entry.get("headers"),
                    )
                logger.info("Loaded %d webhooks from env config", len(entries))
                return
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Failed to parse WEBHOOK_URLS: %s", e)

        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data:
                    self.register(
                        name=entry["name"],
                        url=entry["url"],
                        events=entry.get("events", ["new_item"]),
                        secret=entry.get("secret"),
                        headers=entry.get("headers"),
                    )
                logger.info("Loaded %d webhooks from %s", len(data), self._config_path)
            except Exception as e:
                logger.error("Failed to load webhooks from file: %s", e)
        else:
            logger.info("No webhook config found at %s", self._config_path)

    def save_to_config(self):
        os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
        data = []
        for name, config in self._webhooks.items():
            data.append({
                "name": name,
                "url": config["url"],
                "events": config["events"],
                "secret": config.get("secret"),
                "headers": config.get("headers"),
            })
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info("Saved %d webhooks to %s", len(data), self._config_path)
        except Exception as e:
            logger.error("Failed to save webhooks: %s", e)

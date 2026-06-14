from ...core.config import settings
from ...core.models import ContentItem
from typing import Optional
import httpx, json, os, logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class TwilioSMS:
    def __init__(self, account_sid: str = None, auth_token: str = None, from_number: str = None):
        self.account_sid = account_sid or os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = auth_token or os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_number = from_number or os.environ.get("TWILIO_FROM_NUMBER", "")
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}"
        self._client = httpx.Client(timeout=30)

    def _request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio not fully configured")
            return None
        url = f"{self.base_url}/{endpoint}"
        auth = httpx.BasicAuth(self.account_sid, self.auth_token)
        for attempt in range(3):
            try:
                resp = self._client.request(method, url, auth=auth, data=data)
                if resp.status_code == 429:
                    import time
                    time.sleep(5)
                    continue
                if resp.status_code == 401:
                    logger.error("Twilio auth failed - check Account SID and Auth Token")
                    return {"error": "Authentication failed"}
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.HTTPError as e:
                logger.error(f"Twilio request failed: {e}")
                if attempt == 2:
                    return {"error": str(e)}
                import time
                time.sleep(1)
        return {"error": "Max retries exceeded"}

    def send_sms(self, to: str, message: str) -> dict:
        data = {"To": to, "From": self.from_number, "Body": message[:1600]}
        result = self._request("POST", "Messages.json", data)
        return result or {"error": "Failed to send SMS"}

    def send_alert(self, to: str, alert_type: str, item_title: str, item_url: str = None) -> dict:
        alert_tag = {
            "breaking": "\U0001f6a8 BREAKING",
            "update": "\u2705 UPDATE",
            "trending": "\U0001f525 TRENDING",
            "digest": "\U0001f4cb DIGEST",
        }.get(alert_type, f"[{alert_type.upper()}]")
        message = f"{alert_tag}: {item_title[:120]}"
        if item_url:
            message += f" | {item_url}"
        return self.send_sms(to, message)

    def send_digest_link(self, to: str, digest_url: str, topic: str = None) -> dict:
        topic_str = f" ({topic})" if topic else ""
        message = f"\U0001f4cb AI Content Hub Digest{topic_str}: {digest_url}"
        return self.send_sms(to, message)

    def get_message_history(self, limit: int = 20) -> list[dict]:
        result = self._request("GET", f"Messages.json?PageSize={limit}")
        if result and "messages" in result:
            history = []
            for m in result["messages"]:
                history.append({
                    "sid": m.get("sid"),
                    "to": m.get("to"),
                    "from": m.get("from"),
                    "body": m.get("body"),
                    "status": m.get("status"),
                    "direction": m.get("direction"),
                    "date_sent": m.get("date_sent"),
                    "price": m.get("price"),
                    "error_code": m.get("error_code"),
                })
            return history
        return []

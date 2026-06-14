from ...core.config import settings
from ...core.models import ContentItem
from typing import Optional
import httpx, json, os, logging

logger = logging.getLogger(__name__)


class HubSpotIntegration:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("HUBSPOT_API_KEY", "")
        self.base_url = "https://api.hubapi.com/crm/v3"
        self._client = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, data: dict = None) -> Optional[dict]:
        if not self.api_key:
            logger.warning("HubSpot API key not configured")
            return None
        url = f"{self.base_url}/{path}"
        for attempt in range(3):
            try:
                resp = self._client.request(method, url, headers=self._headers(), json=data)
                if resp.status_code == 429:
                    import time
                    time.sleep(5)
                    continue
                if resp.status_code == 401:
                    logger.error("HubSpot auth failed - check API key")
                    return {"error": "Authentication failed"}
                resp.raise_for_status()
                return resp.json() if resp.content else {}
            except httpx.HTTPError as e:
                logger.error(f"HubSpot request failed: {e}")
                if attempt == 2:
                    return {"error": str(e)}
                import time
                time.sleep(1)
        return {"error": "Max retries exceeded"}

    def create_contact(self, email: str, firstname: str = "", lastname: str = "",
                       company: str = "", **properties) -> dict:
        props = {"email": email}
        if firstname:
            props["firstname"] = firstname
        if lastname:
            props["lastname"] = lastname
        if company:
            props["company"] = company
        props.update(properties)
        data = {"properties": props}
        result = self._request("POST", "objects/contacts", data)
        if result and "error" in result:
            search = self._request("POST", "objects/contacts/search", {
                "filterGroups": [{"filters": [{"propertyName": "email", "operator": "EQ", "value": email}]}]
            })
            if search and "results" in search and search["results"]:
                contact_id = search["results"][0]["id"]
                return self._request("PATCH", f"objects/contacts/{contact_id}", data) or result
        return result or {"error": "Failed to create contact"}

    def create_deal(self, dealname: str, amount: float = 0, pipeline: str = "default",
                    dealstage: str = "appointmentscheduled",
                    associated_contact_ids: list[str] = None) -> dict:
        props = {
            "dealname": dealname[:255],
            "amount": str(amount),
            "pipeline": pipeline,
            "dealstage": dealstage,
        }
        data = {"properties": props}
        if associated_contact_ids:
            data["associations"] = [
                {
                    "to": {"id": cid},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 3}],
                }
                for cid in associated_contact_ids
            ]
        result = self._request("POST", "objects/deals", data)
        return result or {"error": "Failed to create deal"}

    def search_contacts(self, query: str, limit: int = 10) -> list[dict]:
        result = self._request("POST", "objects/contacts/search", {
            "query": query,
            "limit": limit,
        })
        contacts = []
        if result and "results" in result:
            for c in result["results"]:
                contacts.append({
                    "id": c.get("id"),
                    "email": c.get("properties", {}).get("email"),
                    "firstname": c.get("properties", {}).get("firstname"),
                    "lastname": c.get("properties", {}).get("lastname"),
                    "company": c.get("properties", {}).get("company"),
                    "phone": c.get("properties", {}).get("phone"),
                    "created_at": c.get("createdAt"),
                    "updated_at": c.get("updatedAt"),
                })
        return contacts

    def log_note(self, contact_id: str, note: str) -> dict:
        data = {
            "properties": {"hs_timestamp": __import__("datetime").datetime.now().isoformat(), "hs_note_body": note},
            "associations": [
                {
                    "to": {"id": contact_id},
                    "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}],
                }
            ],
        }
        result = self._request("POST", "objects/notes", data)
        return result or {"error": "Failed to log note"}

    def create_task_from_item(self, item: ContentItem, owner_email: str = None) -> dict:
        body = f"Review and process content from {item.source}:\n\nTitle: {item.title}\nURL: {item.url}\n\n{item.content_cleaned or item.content[:500]}"
        props = {
            "hs_timestamp": __import__("datetime").datetime.now().isoformat(),
            "hs_task_body": body,
            "hs_task_subject": f"Review: {item.title[:200]}",
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "HIGH" if item.relevance_score >= 0.7 else "MEDIUM" if item.relevance_score >= 0.4 else "LOW",
        }
        if owner_email:
            props["hubspot_owner_id"] = owner_email
        data = {"properties": props}

        contact = None
        if item.author_name:
            search = self._request("POST", "objects/contacts/search", {
                "query": item.author_name,
                "limit": 1,
            })
            if search and "results" in search and search["results"]:
                contact = search["results"][0]
                data["associations"] = [
                    {
                        "to": {"id": contact["id"]},
                        "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 204}],
                    }
                ]

        result = self._request("POST", "objects/tasks", data)
        return result or {"error": "Failed to create task"}

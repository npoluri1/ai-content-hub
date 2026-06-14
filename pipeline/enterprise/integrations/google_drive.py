from ...core.config import settings
from ...core.models import ContentItem, ClassifiedItem
from typing import Optional
import httpx, json, os, logging, time

logger = logging.getLogger(__name__)

_GOOGLE_AUTH_AVAILABLE = False
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest
    _GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    pass

_PYJWT_AVAILABLE = False
try:
    import jwt
    _PYJWT_AVAILABLE = True
except ImportError:
    pass

SCOPES = ["https://www.googleapis.com/auth/drive"]


class GoogleDriveIntegration:
    def __init__(self, credentials_path: str = None, folder_id: str = None):
        self.credentials_path = credentials_path or getattr(settings, "GOOGLE_DRIVE_CREDENTIALS_PATH", None) or ""
        self.folder_id = folder_id or getattr(settings, "GOOGLE_DRIVE_FOLDER_ID", None) or ""
        self.api_base = "https://www.googleapis.com/drive/v3"
        self.upload_base = "https://www.googleapis.com/upload/drive/v3"
        self._token = None
        self._token_expiry = 0
        self._client = httpx.Client(timeout=60)

    def _get_access_token(self) -> Optional[str]:
        if self._token and time.time() < self._token_expiry:
            return self._token
        if not self.credentials_path or not os.path.isfile(self.credentials_path):
            logger.warning("Google Drive credentials file not found")
            return None
        if _GOOGLE_AUTH_AVAILABLE:
            try:
                creds = service_account.Credentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
                creds.refresh(GoogleRequest())
                self._token = creds.token
                self._token_expiry = creds.expiry.timestamp() - 60
                return self._token
            except Exception as e:
                logger.error(f"Google auth refresh failed: {e}")
                return None
        if _PYJWT_AVAILABLE:
            try:
                with open(self.credentials_path) as f:
                    sa_info = json.load(f)
                now = int(time.time())
                claims = {
                    "iss": sa_info["client_email"],
                    "scope": " ".join(SCOPES),
                    "aud": "https://oauth2.googleapis.com/token",
                    "exp": now + 3600,
                    "iat": now,
                }
                signed_jwt = jwt.encode(claims, sa_info["private_key"], algorithm="RS256")
                resp = httpx.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": signed_jwt,
                    },
                )
                resp.raise_for_status()
                token_data = resp.json()
                self._token = token_data["access_token"]
                self._token_expiry = now + token_data.get("expires_in", 3600) - 60
                return self._token
            except Exception as e:
                logger.error(f"JWT-based auth failed: {e}")
                return None
        logger.error(
            "No auth method available. Install google-auth or PyJWT:\n"
            "  pip install google-auth google-auth-httpx\n"
            "  or pip install pyjwt cryptography"
        )
        return None

    def _headers(self, access_token: str = None) -> dict:
        if access_token:
            return {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
        return {}

    def upload_export(self, file_path: str, mime_type: str = "text/markdown") -> Optional[dict]:
        token = self._get_access_token()
        if not token:
            logger.warning("Cannot upload: no access token")
            return None
        if not os.path.isfile(file_path):
            logger.error(f"File not found: {file_path}")
            return None
        file_name = os.path.basename(file_path)
        try:
            metadata = {"name": file_name, "mimeType": mime_type}
            if self.folder_id:
                metadata["parents"] = [self.folder_id]
            with open(file_path, "rb") as f:
                file_content = f.read()
            resp = self._client.post(
                f"{self.upload_base}/files?uploadType=multipart",
                headers={"Authorization": f"Bearer {token}"},
                files={
                    "metadata": (None, json.dumps(metadata), "application/json; charset=UTF-8"),
                    "file": (file_name, file_content, mime_type),
                },
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"Uploaded {file_name} to Drive (ID: {result.get('id')})")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Drive upload failed: {e}")
            return {"error": str(e)}

    def upload_digest(self, digest_text: str, filename: str = None) -> Optional[dict]:
        if not filename:
            filename = f"digest_{int(time.time())}.md"
        tmp_path = os.path.join(os.path.dirname(self.credentials_path) or os.getcwd(), f"_{filename}")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(digest_text)
            return self.upload_export(tmp_path, "text/markdown")
        finally:
            if os.path.isfile(tmp_path):
                os.remove(tmp_path)

    def create_folder(self, name: str, parent_id: str = None) -> Optional[str]:
        token = self._get_access_token()
        if not token:
            return None
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        try:
            resp = self._client.post(
                f"{self.api_base}/files",
                headers=self._headers(token),
                json=metadata,
            )
            resp.raise_for_status()
            folder_id = resp.json().get("id")
            logger.info(f"Created folder '{name}' (ID: {folder_id})")
            return folder_id
        except httpx.HTTPError as e:
            logger.error(f"Failed to create folder: {e}")
            return None

    def list_files(self, query: str = None, limit: int = 20) -> list[dict]:
        token = self._get_access_token()
        if not token:
            return []
        params = {"pageSize": min(limit, 100), "fields": "files(id,name,mimeType,modifiedTime,size)"}
        if query:
            params["q"] = query
        if self.folder_id and not query:
            params["q"] = f"'{self.folder_id}' in parents and trashed=false"
        try:
            resp = self._client.get(f"{self.api_base}/files", headers=self._headers(token), params=params)
            resp.raise_for_status()
            return resp.json().get("files", [])
        except httpx.HTTPError as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def search_content(self, query: str) -> list[dict]:
        drive_query = f"name contains '{query}' or fullText contains '{query}'"
        return self.list_files(query=drive_query, limit=50)

    def sync_to_drive(self, local_dir: str, drive_folder_id: str = None) -> dict:
        token = self._get_access_token()
        if not token:
            return {"status": "error", "message": "No access token"}
        target_folder = drive_folder_id or self.folder_id
        if not target_folder:
            folder_name = os.path.basename(os.path.normpath(local_dir))
            target_folder = self.create_folder(f"sync_{folder_name}")
            if not target_folder:
                return {"status": "error", "message": "Failed to create sync folder"}
        results = {"uploaded": 0, "failed": 0, "skipped": 0, "files": []}
        if not os.path.isdir(local_dir):
            return {"status": "error", "message": f"Directory not found: {local_dir}"}
        for root, dirs, files in os.walk(local_dir):
            for file_name in files:
                if file_name.startswith(".") or file_name.endswith((".pyc", ".tmp")):
                    results["skipped"] += 1
                    continue
                file_path = os.path.join(root, file_name)
                try:
                    result = self.upload_export(file_path)
                    if result and "id" in result:
                        results["uploaded"] += 1
                        results["files"].append({"name": file_name, "id": result["id"]})
                    else:
                        results["failed"] += 1
                except Exception as e:
                    logger.error(f"Failed to sync {file_name}: {e}")
                    results["failed"] += 1
        results["status"] = "completed"
        logger.info(f"Sync complete: {results['uploaded']} uploaded, {results['failed']} failed, {results['skipped']} skipped")
        return results

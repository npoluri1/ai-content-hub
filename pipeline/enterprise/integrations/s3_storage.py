from ...core.config import settings
from ...core.models import ContentItem
from typing import Optional
import httpx, json, os, logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CloudStorage:
    def __init__(self, provider: str = "s3", bucket: str = None, region: str = "us-east-1",
                 access_key: str = None, secret_key: str = None, endpoint_url: str = None):
        self.provider = provider.lower()
        self.bucket = bucket or os.environ.get("CLOUD_STORAGE_BUCKET", "ai-content-hub")
        self.region = region or os.environ.get("CLOUD_STORAGE_REGION", "us-east-1")
        self.access_key = access_key or os.environ.get("CLOUD_STORAGE_ACCESS_KEY", "")
        self.secret_key = secret_key or os.environ.get("CLOUD_STORAGE_SECRET_KEY", "")
        self.endpoint_url = endpoint_url or os.environ.get("CLOUD_STORAGE_ENDPOINT", "")
        self._boto3 = None
        self._client = None
        self._init_client()

    def _init_client(self):
        if self.provider in ("s3", "minio", "gcs", "azure"):
            try:
                import boto3
                self._boto3 = boto3
                session_kwargs = {
                    "aws_access_key_id": self.access_key,
                    "aws_secret_access_key": self.secret_key,
                    "region_name": self.region,
                }
                if self.endpoint_url:
                    session_kwargs["endpoint_url"] = self.endpoint_url
                self._client = boto3.client("s3", **{k: v for k, v in session_kwargs.items() if v})
            except ImportError:
                logger.warning("boto3 not available, falling back to local file system")
                self._client = None
        else:
            logger.warning(f"Unknown provider '{self.provider}', falling back to local file system")
            self._client = None

    def _local_path(self, remote_path: str) -> str:
        base = os.path.join(settings.DATA_DIR, "cloud_storage", self.bucket)
        full = os.path.join(base, remote_path.lstrip("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        return full

    def upload_file(self, local_path: str, remote_path: str = None) -> str:
        if remote_path is None:
            remote_path = os.path.basename(local_path)
        if not os.path.exists(local_path):
            logger.error(f"Local file not found: {local_path}")
            return ""

        if self._client:
            try:
                extra = {}
                if local_path.endswith(".md"):
                    extra["ContentType"] = "text/markdown"
                elif local_path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                    extra["ContentType"] = f"image/{local_path.rsplit('.', 1)[-1]}"
                self._client.upload_file(local_path, self.bucket, remote_path, ExtraArgs=extra)
                return self.get_signed_url(remote_path) or f"s3://{self.bucket}/{remote_path}"
            except Exception as e:
                logger.error(f"Failed to upload to cloud: {e}")
                return ""

        dest = self._local_path(remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        import shutil
        shutil.copy2(local_path, dest)
        logger.warning(f"[LOCAL FALLBACK] File stored at: {dest}")
        return dest

    def upload_content(self, content: str, remote_path: str, content_type: str = "text/markdown") -> str:
        if self._client:
            try:
                self._client.put_object(
                    Bucket=self.bucket,
                    Key=remote_path,
                    Body=content.encode("utf-8"),
                    ContentType=content_type,
                )
                return self.get_signed_url(remote_path) or f"s3://{self.bucket}/{remote_path}"
            except Exception as e:
                logger.error(f"Failed to upload content to cloud: {e}")
                return ""

        dest = self._local_path(remote_path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(content)
        logger.warning(f"[LOCAL FALLBACK] Content stored at: {dest}")
        return dest

    def download_file(self, remote_path: str, local_path: str) -> bool:
        if self._client:
            try:
                self._client.download_file(self.bucket, remote_path, local_path)
                return True
            except Exception as e:
                logger.error(f"Failed to download from cloud: {e}")
                return False

        src = self._local_path(remote_path)
        if not os.path.exists(src):
            logger.error(f"Local file not found: {src}")
            return False
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        import shutil
        shutil.copy2(src, local_path)
        return True

    def list_files(self, prefix: str = "", limit: int = 100) -> list[dict]:
        if self._client:
            try:
                resp = self._client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=limit)
                files = []
                for obj in resp.get("Contents", []):
                    files.append({
                        "key": obj.get("Key"),
                        "size": obj.get("Size"),
                        "last_modified": obj.get("LastModified").isoformat() if obj.get("LastModified") else None,
                        "etag": obj.get("ETag"),
                    })
                return files
            except Exception as e:
                logger.error(f"Failed to list cloud files: {e}")
                return []

        base = self._local_path(prefix)
        if not os.path.exists(base):
            return []
        files = []
        for root, dirs, names in os.walk(base):
            for name in names[:limit]:
                full = os.path.join(root, name)
                rel = os.path.relpath(full, self._local_path(""))
                files.append({
                    "key": rel.replace("\\", "/"),
                    "size": os.path.getsize(full),
                    "last_modified": __import__("datetime").datetime.fromtimestamp(
                        os.path.getmtime(full)).isoformat(),
                })
        return files[:limit]

    def delete_file(self, remote_path: str) -> bool:
        if self._client:
            try:
                self._client.delete_object(Bucket=self.bucket, Key=remote_path)
                return True
            except Exception as e:
                logger.error(f"Failed to delete cloud file: {e}")
                return False

        dest = self._local_path(remote_path)
        if os.path.exists(dest):
            os.remove(dest)
            return True
        return False

    def get_signed_url(self, remote_path: str, expires_in: int = 3600) -> str:
        if self._client:
            try:
                return self._client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self.bucket, "Key": remote_path},
                    ExpiresIn=expires_in,
                )
            except Exception as e:
                logger.error(f"Failed to generate presigned URL: {e}")
                return ""
        return ""

    def sync_directory(self, local_dir: str, remote_prefix: str = "") -> dict:
        if not os.path.isdir(local_dir):
            return {"error": f"Directory not found: {local_dir}"}
        stats = {"uploaded": 0, "skipped": 0, "failed": 0, "files": []}
        for root, dirs, names in os.walk(local_dir):
            for name in names:
                local_file = os.path.join(root, name)
                rel_path = os.path.relpath(local_file, local_dir)
                remote_path = f"{remote_prefix}/{rel_path}".replace("\\", "/").lstrip("/")
                result = self.upload_file(local_file, remote_path)
                if result:
                    stats["uploaded"] += 1
                    stats["files"].append({"local": local_file, "remote": remote_path, "url": result})
                else:
                    stats["failed"] += 1
        return stats

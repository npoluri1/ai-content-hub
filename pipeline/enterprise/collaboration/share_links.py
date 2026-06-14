import sqlite3
import os
import secrets
import string
import json
from datetime import datetime, timedelta, timezone


def _generate_code(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class ShareLinkManager:
    def __init__(self, db_path: str = "./data/shares.db"):
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS share_links (
                    share_code TEXT PRIMARY KEY,
                    content_id TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT,
                    max_access INTEGER DEFAULT 0,
                    access_count INTEGER DEFAULT 0,
                    password_hash TEXT,
                    require_auth INTEGER DEFAULT 0,
                    is_revoked INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS share_access_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    share_code TEXT NOT NULL,
                    accessor TEXT,
                    accessed_at TEXT DEFAULT (datetime('now')),
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (share_code) REFERENCES share_links(share_code)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_content ON share_links(content_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_shares_creator ON share_links(created_by)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_log_code ON share_access_log(share_code)")

    def create_share(
        self,
        content_id: str,
        created_by: str,
        expires_in_hours: int = 24,
        max_access: int = 0,
        password: str = None,
        require_auth: bool = False
    ) -> str:
        share_code = _generate_code()
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)).isoformat()
        password_hash = None
        if password:
            import hashlib
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO share_links (share_code, content_id, created_by, expires_at, max_access, password_hash, require_auth)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (share_code, content_id, created_by, expires_at, max_access, password_hash, int(require_auth))
            )
        return share_code

    def get_share(self, share_code: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM share_links WHERE share_code = ?", (share_code,)
            ).fetchone()
            if not row:
                return None
            return dict(row)

    def access_share(
        self,
        share_code: str,
        accessor: str = None,
        password: str = None
    ) -> dict:
        share = self.get_share(share_code)
        if not share:
            return {"error": "Share link not found"}
        if share["is_revoked"]:
            return {"error": "Share link has been revoked"}
        if share["expires_at"]:
            try:
                expires = datetime.fromisoformat(share["expires_at"])
                if expires < datetime.now(timezone.utc):
                    return {"error": "Share link has expired"}
            except (ValueError, TypeError):
                pass
        if share["max_access"] > 0 and share["access_count"] >= share["max_access"]:
            return {"error": "Share link has reached maximum access count"}
        if share["password_hash"]:
            import hashlib
            if not password:
                return {"error": "Password required"}
            if hashlib.sha256(password.encode()).hexdigest() != share["password_hash"]:
                return {"error": "Invalid password"}
        if share["require_auth"] and not accessor:
            return {"error": "Authentication required"}

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE share_links SET access_count = access_count + 1 WHERE share_code = ?",
                (share_code,)
            )
            conn.execute(
                "INSERT INTO share_access_log (share_code, accessor) VALUES (?, ?)",
                (share_code, accessor)
            )

        return {
            "content_id": share["content_id"],
            "share_code": share_code,
            "created_by": share["created_by"]
        }

    def revoke_share(self, share_code: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE share_links SET is_revoked = 1 WHERE share_code = ?",
                (share_code,)
            )
            return cur.rowcount > 0

    def list_shares(self, created_by: str = None, content_id: str = None) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if created_by and content_id:
                rows = conn.execute(
                    "SELECT * FROM share_links WHERE created_by = ? AND content_id = ? ORDER BY created_at DESC",
                    (created_by, content_id)
                ).fetchall()
            elif created_by:
                rows = conn.execute(
                    "SELECT * FROM share_links WHERE created_by = ? ORDER BY created_at DESC",
                    (created_by,)
                ).fetchall()
            elif content_id:
                rows = conn.execute(
                    "SELECT * FROM share_links WHERE content_id = ? ORDER BY created_at DESC",
                    (content_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM share_links ORDER BY created_at DESC"
                ).fetchall()
            return [dict(r) for r in rows]

    def get_share_analytics(self, share_code: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            share = self.get_share(share_code)
            if not share:
                return None

            log_rows = conn.execute(
                "SELECT * FROM share_access_log WHERE share_code = ? ORDER BY accessed_at DESC",
                (share_code,)
            ).fetchall()

            unique_accessors = set()
            for r in log_rows:
                if r[2]:
                    unique_accessors.add(r[2])

            last_accessed = log_rows[0][3] if log_rows else None

            return {
                "share_code": share_code,
                "access_count": share["access_count"],
                "unique_visitors": len(unique_accessors),
                "last_accessed": last_accessed,
                "access_log": [
                    {"accessor": r[2], "accessed_at": r[3]}
                    for r in log_rows[-20:]
                ]
            }

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            expired = conn.execute(
                "SELECT share_code FROM share_links WHERE expires_at IS NOT NULL AND expires_at < ? AND is_revoked = 0",
                (now,)
            ).fetchall()
            codes = [r[0] for r in expired]
            if not codes:
                return 0
            conn.execute(
                f"DELETE FROM share_links WHERE share_code IN ({','.join('?' for _ in codes)})",
                codes
            )
            conn.execute(
                f"DELETE FROM share_access_log WHERE share_code IN ({','.join('?' for _ in codes)})",
                codes
            )
            return len(codes)

    def generate_share_url(self, share_code: str, base_url: str = "https://hub.example.com/share") -> str:
        return f"{base_url}/{share_code}"

    def get_public_content(self, limit: int = 20) -> list[dict]:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT content_id, share_code, created_by, created_at
                   FROM share_links
                   WHERE is_revoked = 0
                     AND (expires_at IS NULL OR expires_at > ?)
                     AND (max_access = 0 OR access_count < max_access)
                   ORDER BY created_at DESC LIMIT ?""",
                (now, limit)
            ).fetchall()
            return [dict(r) for r in rows]

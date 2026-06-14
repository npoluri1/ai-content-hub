import hashlib
import os
import sqlite3
import json
import hmac
import base64
import logging
import time
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from ..core.config import settings

logger = logging.getLogger(__name__)

try:
    import jwt as pyjwt
    HAS_PYJWT = True
except ImportError:
    HAS_PYJWT = False
    logger.debug("PyJWT not installed, using HMAC-based tokens")


class JWTAuth:
    def __init__(self, secret_key: str = None, algorithm: str = "HS256", token_expiry_hours: int = 24):
        self.secret_key = secret_key or settings.APP_NAME + "_secret_key_change_in_production"
        self.algorithm = algorithm
        self.token_expiry_hours = token_expiry_hours
        self._db_path = Path(settings.DATA_DIR)
        self._ensure_db()

    def _ensure_db(self):
        self._db_path.mkdir(parents=True, exist_ok=True)
        db_file = self._db_path / "auth.db"
        conn = sqlite3.connect(str(db_file))
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    created_at TEXT NOT NULL,
                    last_login TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _get_conn(self):
        db_file = self._db_path / "auth.db"
        return sqlite3.connect(str(db_file))

    def hash_password(self, password: str) -> tuple[str, str]:
        salt = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
        hashed = hashlib.sha256((salt + password).encode()).hexdigest()
        return hashed, salt

    def verify_password(self, password: str, hashed: str, salt: str) -> bool:
        check = hashlib.sha256((salt + password).encode()).hexdigest()
        return hmac.compare_digest(check, hashed)

    def create_user(self, username: str, password: str, role: str = "user") -> dict:
        password_hash, salt = self.hash_password(password)
        created_at = datetime.utcnow().isoformat()
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO users (username, password_hash, salt, role, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, salt, role, created_at),
            )
            conn.commit()
            return {"id": conn.execute("SELECT last_insert_rowid()").fetchone()[0], "username": username, "role": role, "created_at": created_at}
        except sqlite3.IntegrityError:
            raise ValueError(f"User '{username}' already exists")
        finally:
            conn.close()

    def authenticate(self, username: str, password: str) -> str:
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, username, password_hash, salt, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                raise ValueError("Invalid username or password")
            user_id, username, password_hash, salt, role = row
            if not self.verify_password(password, password_hash, salt):
                raise ValueError("Invalid username or password")
            conn.execute("UPDATE users SET last_login = ? WHERE id = ?", (datetime.utcnow().isoformat(), user_id))
            conn.commit()
            return self._create_token({"sub": str(user_id), "username": username, "role": role})
        finally:
            conn.close()

    def verify_token(self, token: str) -> dict:
        if HAS_PYJWT:
            try:
                payload = pyjwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                return payload
            except pyjwt.ExpiredSignatureError:
                raise ValueError("Token has expired")
            except pyjwt.InvalidTokenError as e:
                raise ValueError(f"Invalid token: {e}")
        else:
            return self._verify_hmac_token(token)

    def get_current_user(self, token: str) -> dict:
        payload = self.verify_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token payload")
        conn = self._get_conn()
        try:
            row = conn.execute(
                "SELECT id, username, role, created_at, last_login FROM users WHERE id = ?",
                (int(user_id),),
            ).fetchone()
            if not row:
                raise ValueError("User not found")
            return {"id": row[0], "username": row[1], "role": row[2], "created_at": row[3], "last_login": row[4]}
        finally:
            conn.close()

    def require_auth(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Request, HTTPException
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                for _, v in kwargs.items():
                    if isinstance(v, Request):
                        request = v
                        break
            if not request:
                raise HTTPException(status_code=500, detail="Request object not found")
            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
            token = auth_header[7:]
            try:
                payload = self.verify_token(token)
                request.state.user = payload
            except ValueError as e:
                raise HTTPException(status_code=401, detail=str(e))
            return await func(*args, **kwargs)
        return wrapper

    def _create_token(self, payload: dict) -> str:
        if HAS_PYJWT:
            expiry = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
            payload["exp"] = expiry
            payload["iat"] = datetime.utcnow()
            return pyjwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        else:
            return self._create_hmac_token(payload)

    def _create_hmac_token(self, payload: dict) -> str:
        payload["exp"] = time.time() + (self.token_expiry_hours * 3600)
        payload["iat"] = time.time()
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
        body = base64.urlsafe_b64encode(json.dumps(payload, default=str).encode()).rstrip(b"=").decode()
        signature = hmac.new(
            self.secret_key.encode(),
            f"{header}.{body}".encode(),
            hashlib.sha256,
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
        return f"{header}.{body}.{sig_b64}"

    def _verify_hmac_token(self, token: str) -> dict:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_b64, body_b64, sig_b64 = parts
        expected_sig = hmac.new(
            self.secret_key.encode(),
            f"{header_b64}.{body_b64}".encode(),
            hashlib.sha256,
        ).digest()
        actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")
        if not hmac.compare_digest(expected_sig, actual_sig):
            raise ValueError("Invalid token signature")
        body_padded = body_b64 + "=" * (4 - len(body_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body_padded))
        if payload.get("exp", 0) < time.time():
            raise ValueError("Token has expired")
        return payload

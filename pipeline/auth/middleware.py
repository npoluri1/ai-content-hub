import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .jwt_auth import JWTAuth

logger = logging.getLogger(__name__)

jwt_auth = JWTAuth()


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, public_paths: list[str] = None):
        super().__init__(app)
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/login",
            "/register",
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.public_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Missing or invalid Authorization header"})

        token = auth_header[7:]
        try:
            payload = jwt_auth.verify_token(token)
            request.state.user = payload
        except ValueError as e:
            return JSONResponse(status_code=401, content={"detail": str(e)})

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window_seconds

        with self._requests._lock:
            self._requests[client_ip] = [t for t in self._requests[client_ip] if t > window_start]
            request_count = len(self._requests[client_ip])

            if request_count >= self.max_requests:
                retry_after = int(self._requests[client_ip][0] + self.window_seconds - now)
                headers = {
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                    "Retry-After": str(retry_after),
                }
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Rate limit exceeded. Try again in {retry_after} seconds."},
                    headers=headers,
                )

            self._requests[client_ip].append(now)

        response = await call_next(request)

        if isinstance(response, Response):
            remaining = max(0, self.max_requests - request_count - 1)
            response.headers["X-RateLimit-Limit"] = str(self.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + self.window_seconds))

        return response

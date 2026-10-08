"""HTTP middleware for ShopClaim Bridge."""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from shop_claim_bridge.rate_limit import rate_limiter

_API_PREFIX = "/api/v1/"
_DEFAULT_MAX = 300
_DEFAULT_WINDOW = 60.0
_HEALTH_PATH = "/health"
_HEALTH_METHODS = {b"GET", b"HEAD", b"OPTIONS"}
_DEFAULT_HEALTH_CORS_ORIGINS = frozenset({"http://127.0.0.1:8790"})


def _client_ip(scope: Scope) -> str:
    headers = dict(scope.get("headers") or [])
    forwarded = headers.get(b"x-forwarded-for", b"").decode("latin-1")
    if forwarded:
        return forwarded.split(",")[0].strip()
    client = scope.get("client")
    if client:
        return str(client[0])
    return "unknown"


def _header(scope: Scope, name: bytes) -> str:
    for key, value in scope.get("headers") or []:
        if key == name:
            return value.decode("latin-1")
    return ""


class HealthCorsMiddleware:
    """Allow browser status page to read GET /health only (not /api/v1/*)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        allow_origins: frozenset[str] | set[str] | None = None,
    ) -> None:
        self.app = app
        self.allow_origins = frozenset(allow_origins or _DEFAULT_HEALTH_CORS_ORIGINS)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "").encode("ascii")
        if path != _HEALTH_PATH or method not in _HEALTH_METHODS:
            await self.app(scope, receive, send)
            return

        origin = _header(scope, b"origin")
        allow = origin if origin in self.allow_origins else ""

        if method == b"OPTIONS":
            headers: list[tuple[bytes, bytes]] = [
                (b"access-control-allow-methods", b"GET, HEAD, OPTIONS"),
                (b"access-control-max-age", b"86400"),
                (b"content-length", b"0"),
            ]
            if allow:
                headers.append((b"access-control-allow-origin", allow.encode("latin-1")))
                headers.append((b"vary", b"Origin"))
            await send({"type": "http.response.start", "status": 204, "headers": headers})
            await send({"type": "http.response.body", "body": b""})
            return

        async def send_with_cors(message: Message) -> None:
            if allow and message["type"] == "http.response.start":
                raw = list(message.get("headers") or [])
                raw.append((b"access-control-allow-origin", allow.encode("latin-1")))
                raw.append((b"vary", b"Origin"))
                message = {**message, "headers": raw}
            await send(message)

        await self.app(scope, receive, send_with_cors)


class ApiRateLimitMiddleware:
    """Rate limit mod API by client IP (S3 mitigation)."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        max_events: int = _DEFAULT_MAX,
        window_sec: float = _DEFAULT_WINDOW,
    ) -> None:
        self.app = app
        self.max_events = max_events
        self.window_sec = window_sec

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(_API_PREFIX):
            ip = _client_ip(scope)
            key = f"api_v1:{ip}"
            if not rate_limiter.allow(
                key, max_events=self.max_events, window_sec=self.window_sec
            ):
                body = json.dumps({"detail": "Too many requests"}).encode("utf-8")
                await send(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return

        await self.app(scope, receive, send)

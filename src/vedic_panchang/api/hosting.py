"""Protections for the hosted API: per-client rate limiting and response headers.

Each server instance keeps its own counts in memory (no shared store needed at this scale;
the hosting platform also caps the number of instances).
"""

import json
import time
from collections import deque

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_WINDOW_S = 60.0


class RateLimit:
    """Allow at most ``per_minute`` requests per client per rolling minute; 0 disables it.

    The client is the first address in ``X-Forwarded-For`` when ``trust_proxy`` is set (the
    hosting platform's load balancer adds it), else the connection's address.
    """

    def __init__(self, app: ASGIApp, per_minute: int, trust_proxy: bool = False):
        self.app = app
        self.per_minute = per_minute
        self.trust_proxy = trust_proxy
        self.hits: dict[str, deque[float]] = {}
        self._last_sweep = time.monotonic()

    def _client(self, scope: Scope) -> str:
        if self.trust_proxy:
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-for":
                    return value.decode("latin-1").split(",")[0].strip()
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < _WINDOW_S:
            return
        self._last_sweep = now
        for key in [k for k, q in self.hits.items() if not q or now - q[-1] > _WINDOW_S]:
            del self.hits[key]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or self.per_minute <= 0 or scope["path"] == "/health":
            await self.app(scope, receive, send)
            return
        now = time.monotonic()
        self._sweep(now)
        hits = self.hits.setdefault(self._client(scope), deque())
        while hits and now - hits[0] > _WINDOW_S:
            hits.popleft()
        if len(hits) >= self.per_minute:
            retry = max(1, int(_WINDOW_S - (now - hits[0])) + 1)
            body = json.dumps(
                {
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Please wait a moment and try again.",
                        "details": {"retry_after_seconds": retry},
                    },
                    "request": {"path": scope["path"]},
                }
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"retry-after", str(retry).encode()),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        hits.append(now)
        await self.app(scope, receive, send)


class ResponseHeaders:
    """Security headers on every response; successful /v1 answers may be cached for an hour
    (values are deterministic for a given city, date and rule version)."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        cacheable = scope["path"].startswith("/v1/") and scope["method"] == "GET"

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"referrer-policy", b"no-referrer"))
                if cacheable and message["status"] == 200:
                    headers.append((b"cache-control", b"public, max-age=3600"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)

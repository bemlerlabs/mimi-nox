"""
server/middleware.py – Security Middleware für LAN Mode.
Erzeugt ein zufälliges Auth-Token und schützt alle API-Endpunkte.
"""
from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict

from fastapi import Header, HTTPException, Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

LAN_AUTH_TOKEN: str | None = None


def init_auth(lan_mode: bool = False) -> str | None:
    global LAN_AUTH_TOKEN
    if lan_mode:
        LAN_AUTH_TOKEN = secrets.token_urlsafe(32)
        print(f"  🔑 LAN Auth Token generated — embedded in QR code")
        return LAN_AUTH_TOKEN
    LAN_AUTH_TOKEN = None
    return None


async def verify_auth(request: Request) -> None:
    if LAN_AUTH_TOKEN is None:
        return
    token = request.headers.get("X-Auth-Token")
    if token != LAN_AUTH_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized — invalid or missing X-Auth-Token")


class AuthMiddleware(BaseHTTPMiddleware):
    """Schützt alle /api/* Endpunkte im LAN Mode."""
    async def dispatch(self, request: Request, call_next):
        if LAN_AUTH_TOKEN is not None:
            path = request.url.path
            if path.startswith("/api/") and path != "/api/health":
                token = request.headers.get("X-Auth-Token")
                if token != LAN_AUTH_TOKEN:
                    return Response(
                        "Unauthorized — X-Auth-Token header required in LAN mode",
                        status_code=401,
                    )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if LAN_AUTH_TOKEN:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "connect-src 'self' ws://localhost:* http://localhost:*; "
                "img-src 'self' data:; "
                "font-src 'self' data:"
            )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 60, window: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if LAN_AUTH_TOKEN is None:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        window_start = now - self.window
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]

        if len(self.requests[client_ip]) >= self.max_requests:
            return Response(
                "Rate limit exceeded. Try again later.",
                status_code=429,
                headers={"Retry-After": str(self.window)},
            )

        self.requests[client_ip].append(now)
        return await call_next(request)

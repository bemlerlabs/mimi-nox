"""
◑ MiMi Nox – Observability primitives (Phase 4 Item 15)
core/observability.py

Single source of truth für:
  - stabile, maschinenlesbare Error-Codes (ErrorCode-Enum)
  - Request-ID-Generierung (X-Request-ID Header + Body, korrelierte Logs)
  - strukturierte JSON-Logs (structured_log)
  - Starlette-HTTP-Middleware-Factory (Request-ID + Request-Logging)

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from enum import Enum

REQUEST_ID_HEADER = "X-Request-ID"

# Dedizierter Logger — bleibt von uvicorn.error / getLogger("uvicorn") entkoppelt.
_logger = logging.getLogger("mimi_nox.obs")


class ErrorCode(str, Enum):
    """Stabile, maschinenlesbare Fehlercodes (Phase 4 Item 15).

    Werte ändern sich nie; neue Codes werden nur appendiert (Backcompat).
    Das Mapping auf Exit-Codes/HTTP-Status bleibt in den Callern (CLI/Engine).
    """
    USAGE = "usage_error"        # CLI: ungültige Argumente / argparse usage
    RUNTIME = "runtime_error"    # CLI: Laufzeitfehler (Exit 1)
    VALIDATION = "validation_error"  # HTTP 400: Request-Validierung
    AUTH = "auth_error"          # HTTP 401: fehlender/falscher Token
    STREAM = "stream_error"      # SSE: Fehler mitten im Stream
    UPSTREAM = "upstream_error"  # Provider/Backend (Ollama/ds4) nicht erreichbar
    INTERNAL = "internal_error"  # unerwartete Exception (500)


def new_request_id(prefix: str = "req") -> str:
    """Kompakte, kollisionsarme Request-ID (uuid4-hex, gekürzt)."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def structured_log(
    level: str, event: str, request_id: str | None = None, **fields
) -> None:
    """Emittiert eine einzeilige, JSON-parsebare strukturierte Log-Zeile.

    Args:
        level:  "debug" | "info" | "warning" | "error"
        event:  stabiles Event-Name (z.B. "request", "internal_error")
        request_id: korrelierte Request-ID (X-Request-ID)
        fields: beliebige strukturierte Felder (method, path, status, ...)
    """
    record = {
        "ts": f"{time.time():.3f}",
        "level": level,
        "event": event,
        "request_id": request_id,
    }
    record.update(fields)
    line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    getattr(_logger, level)(line)


def error_payload(
    code: ErrorCode, message: str, request_id: str | None = None
) -> dict:
    """OpenAI-konformer Fehler-Body mit stabilen Codes (Phase 4)."""
    body = {"error": {"message": message, "code": code.value}}
    if request_id:
        body["error"]["request_id"] = request_id
    return body


def make_observability_middleware(prefix: str = "req"):
    """Factory für eine Starlette-HTTP-Middleware: Request-ID + strukturierte Logs.

    - setzt request.state.rid (Request-ID, X-Request-ID Header falls gesendet)
    - schreibt X-Request-ID in die Response-Header
    - loggt jede Request als strukturierte JSON-Zeile (event="request")
    - unerwartete Exceptions → 500 mit ErrorCode.INTERNAL + Request-ID

    prefix: Präfix der generierten Request-IDs (z.B. "chatcmpl-" für die Engine).

    Verwendet lazy imports, damit core/ leicht bleibt (kein schweres Modul im
    CLI-Load-Pfad).
    """
    async def _middleware(request, call_next):
        from starlette.responses import JSONResponse  # lazy

        rid = request.headers.get(REQUEST_ID_HEADER) or new_request_id(prefix)
        request.state.rid = rid
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001
            structured_log(
                "error", "internal_error", request_id=rid,
                method=request.method, path=request.url.path,
                error=str(exc),
            )
            response = JSONResponse(
                error_payload(ErrorCode.INTERNAL, str(exc), rid),
                status_code=500,
                headers={REQUEST_ID_HEADER: rid},
            )
        response.headers[REQUEST_ID_HEADER] = rid
        structured_log(
            "info", "request", request_id=rid,
            method=request.method, path=request.url.path,
            status=response.status_code,
            duration_ms=f"{1000 * (time.perf_counter() - start):.1f}",
        )
        return response

    return _middleware

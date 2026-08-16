"""
◑ MiMi Nox – OpenAI-kompatible Engine (Phase 3)
server/openai.py

Stellt die lokale Engine als OpenAI-kompatible API bereit, damit andere
Agent-CLIs (JCode, Codex, OpenCode, Gemini CLI) als Consumer dranhängen können.

Endpunkte:
  GET  /v1/models            → Model-Liste (aus dem aktiven Provider)
  POST /v1/chat/completions  → Chat-Completion, non-stream + stream (SSE)

Auth-Modell:
  - api_token gesetzt → Jeder Request braucht Header ``X-Auth-Token`` (401 sonst)
  - api_token None    → kein Token nötig (nur für localhost-Bind gedacht)

Backend: build_provider_client() (offline-first: lokales Ollama default).

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.model_provider import (
    ModelProviderConfig,
    build_provider_client,
    get_active_provider,
)
from core.model_config import ModelConfig, ModelTier, TIER_MAP
from core.model_router import get_router
from core.observability import (
    REQUEST_ID_HEADER,
    ErrorCode,
    error_payload,
    make_observability_middleware,
)

DEFAULT_MODEL = "gemma4:12b"
STREAM_MARKER = "[DONE]"
OWNED_BY = "mimi-nox"


def _provider_config_for(cfg: ModelConfig) -> ModelProviderConfig:
    """Konvertiert eine Router-ModelConfig in eine Provider-Config (offline-first)."""
    return ModelProviderConfig(
        provider="local_ollama",
        model=cfg.name,
        base_url=cfg.base_url,  # http://<host> — lokal oder DGX/ds4
        label=cfg.tier.value,
        offline_capable=True,
        requires_internet=False,
    )


def _request_id() -> str:
    return ""  # deprecated: Request-ID kommt aus der Observability-Middleware


def _now() -> int:
    return int(time.time())


def _chat_stream(client: Any, model: str, messages: list[dict]) -> Any:
    """AsyncIterator vom Backend (dicts mit ``message.content``).

    ``chat(..., stream=True)`` liefert bereits einen AsyncIterator (kein
    Coroutine) — wird per ``async for`` konsumiert.
    """
    return client.chat(model=model, messages=messages, stream=True)


def _sse_delta(rid: str, model: str, content: str) -> str:
    payload = {
        "id": rid,
        "object": "chat.completion.chunk",
        "created": _now(),
        "model": model,
        "choices": [
            {"index": 0, "delta": {"content": content}, "finish_reason": None}
        ],
    }
    return f"data: {json.dumps(payload)}\n\n"


async def _sse_stream(client: Any, model: str, messages: list[dict], rid: str):
    try:
        async for chunk in _chat_stream(client, model, messages):
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                yield _sse_delta(rid, model, delta)
        yield f"data: {STREAM_MARKER}\n\n"
    except Exception as exc:  # noqa: BLE001
        yield f"data: {json.dumps(error_payload(ErrorCode.STREAM, str(exc), rid))}\n\n"


def create_openai_app(api_token: str | None = None) -> FastAPI:
    """
    Baut die OpenAI-kompatible FastAPI-App.

    Genutzt in Tests (httpx.ASGITransport) und in ``miminox serve`` (uvicorn).

    Expliziter leerer Lifespan: umgeht den FastAPI-Default-Router-Lifespan,
    der in dieser starlette-Version beim Startup mit
    "NoneType object is not callable" fehlschlägt (Muster wie server/main.py).
    """

    @asynccontextmanager
    async def _lifespan(_app: FastAPI):
        yield

    app = FastAPI(
        title="MiMi Nox OpenAI-compatible Engine",
        description="Local-first engine endpoint for agent CLIs",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_lifespan,
    )

    async def _require_token(request: Request) -> None:
        if not api_token:
            return
        header = request.headers.get("x-auth-token")
        if header != api_token:
            raise HTTPException(status_code=401, detail="Invalid or missing X-Auth-Token")

    async def _parse_body(request: Request) -> dict:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")
        return body

    @app.get("/v1/models")
    async def list_models(request: Request):
        await _require_token(request)
        active = get_active_provider()
        seen: set[str] = set()
        data = []
        # Alle Hardware-Tiers transparent auflisten (offline/fast/power)
        for cfg in TIER_MAP.values():
            if cfg.name not in seen:
                seen.add(cfg.name)
                data.append({"id": cfg.name, "object": "model", "created": 0, "owned_by": OWNED_BY})
        # Aktives Modell sicherstellen (z.B. custom provider)
        if active.model not in seen:
            data.append({"id": active.model, "object": "model", "created": 0, "owned_by": OWNED_BY})
        return JSONResponse(
            {"object": "list", "data": data},
            headers={"X-Model-Provider": OWNED_BY, "X-Model-Tier": active.provider},
        )

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        await _require_token(request)
        body = await _parse_body(request)

        messages = body.get("messages")
        if not isinstance(messages, list) or not messages:
            raise HTTPException(status_code=400, detail="messages required (non-empty array)")
        # Jeder Eintrag muss role + content haben (OpenAI-Contract)
        for msg in messages:
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Each message needs role and content")

        model_param = body.get("model")
        stream = bool(body.get("stream", False))

        # Modell-Auflösung: explizites model im Request gewinnt; sonst Router
        # (Hardware-Adaptivität gemma4:12b ↔ ds4, single source of truth).
        if model_param:
            cfg = ModelConfig(name=model_param, tier=ModelTier.FAST)
            tier = "explicit"
        else:
            cfg = await get_router().resolve()
            tier = cfg.tier.value
        model = cfg.name
        client = build_provider_client(_provider_config_for(cfg))
        rid = request.state.rid

        resp_headers = {
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Model-Tier": tier,
            "X-Model-Name": model,
            "X-Model-Provider": OWNED_BY,
        }

        if stream:
            return StreamingResponse(
                _sse_stream(client, model, messages, rid),
                media_type="text/event-stream",
                headers=resp_headers,
            )

        # Non-stream: alle Chunks sammeln → ein Completion
        content = ""
        async for chunk in _chat_stream(client, model, messages):
            content += chunk.get("message", {}).get("content", "")

        return JSONResponse(
            {
                "id": rid,
                "object": "chat.completion",
                "created": _now(),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            },
            headers={
                "X-Model-Tier": tier,
                "X-Model-Name": model,
                "X-Model-Provider": OWNED_BY,
            },
        )

    # ── Observability (Phase 4 Item 15): Request-ID + strukturierte Logs ──
    app.middleware("http")(make_observability_middleware(prefix="chatcmpl-"))

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException):
        rid = request.state.rid
        message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        code_id = ErrorCode.AUTH if exc.status_code == 401 else ErrorCode.VALIDATION
        return JSONResponse(
            error_payload(code_id, message, rid),
            status_code=exc.status_code,
            headers={REQUEST_ID_HEADER: rid},
        )

    return app

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
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from core.model_provider import build_provider_client, get_active_provider

DEFAULT_MODEL = "gemma4:12b"
STREAM_MARKER = "[DONE]"


def _request_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:12]}"


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
        yield f"data: {json.dumps({'error': {'message': str(exc)}})}\n\n"


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
        return JSONResponse(
            {
                "object": "list",
                "data": [
                    {"id": active.model, "object": "model", "created": 0, "owned_by": "mimi-nox"}
                ],
            }
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

        model = body.get("model") or DEFAULT_MODEL
        stream = bool(body.get("stream", False))

        client = build_provider_client()
        rid = _request_id()

        if stream:
            return StreamingResponse(
                _sse_stream(client, model, messages, rid),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
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
            }
        )

    return app

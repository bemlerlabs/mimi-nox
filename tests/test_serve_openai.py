"""
◑ MiMi Nox – Contract-Tests für die OpenAI-kompatible Engine (Phase 3)
tests/test_serve_openai.py

Verifiziert den OpenAI-Contract von ``server.openai.create_openai_app``:
  - GET  /v1/models            → Model-Liste aus dem aktiven Provider
  - POST /v1/chat/completions  → non-stream (ein Completion) + stream (SSE)
  - X-Auth-Token erforderlich, wenn api_token gesetzt ist (401 sonst)
  - Request-Validierung (messages-Format)

Läuft offline: build_provider_client wird mit einem Fake-AsyncClient gemockt
(kein Ollama/Netzwerk nötig).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from server.openai import create_openai_app

CHUNKS = ["Hello", " from", " the", " Black", " Forest"]
FULL = "".join(CHUNKS)


class FakeClient:
    """Ersatz für build_provider_client(): liefert einen AsyncIterator."""

    def chat(self, model, messages, stream):  # noqa: ARG002
        async def _gen():
            for chunk in CHUNKS:
                yield {"message": {"content": chunk}}

        return _gen()


@pytest.fixture
def fake_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("server.openai.build_provider_client", lambda: FakeClient())


# ---------------------------------------------------------------------------
# /v1/models
# ---------------------------------------------------------------------------


def test_models_lists_active_model(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.get("/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    assert data["object"] == "list"
    assert data["data"][0]["object"] == "model"
    assert data["data"][0]["id"]  # das aktive Modell (gemma4:12b default)


# ---------------------------------------------------------------------------
# /v1/chat/completions — non-stream
# ---------------------------------------------------------------------------


def test_chat_non_stream_returns_single_completion(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "gemma4:12b", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["choices"][0]["message"]["content"] == FULL
    assert body["choices"][0]["finish_reason"] == "stop"


# ---------------------------------------------------------------------------
# /v1/chat/completions — SSE stream
# ---------------------------------------------------------------------------


def test_chat_stream_emits_sse_chunks_and_done(fake_provider):
    with TestClient(create_openai_app()) as client:
        with client.stream(
            "POST",
            "/v1/chat/completions",
            json={
                "model": "gemma4:12b",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            },
        ) as resp:
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/event-stream")
            # iter_lines() splittet auf \n → leere Trennzeilen zwischen Events filtern
            lines = [ln for ln in resp.iter_lines() if ln]

    # N Daten-Chunks + 1 [DONE]-Terminator
    assert len(lines) == len(CHUNKS) + 1
    assert lines[-1] == "data: [DONE]"
    # Jeder Daten-Chunk muss gültiges OpenAI-Chunk-JSON sein und delta.content tragen
    collected = ""
    for line in lines[:-1]:
        assert line.startswith("data: ")
        payload = __import__("json").loads(line[6:])
        assert payload["object"] == "chat.completion.chunk"
        collected += payload["choices"][0]["delta"]["content"]
    assert collected == FULL


# ---------------------------------------------------------------------------
# Auth-Token
# ---------------------------------------------------------------------------


def test_models_rejects_request_without_token_when_configured(fake_provider):
    with TestClient(create_openai_app(api_token="supersecret")) as client:
        resp = client.get("/v1/models")
    assert resp.status_code == 401


def test_models_allows_request_with_correct_token(fake_provider):
    with TestClient(create_openai_app(api_token="supersecret")) as client:
        resp = client.get("/v1/models", headers={"X-Auth-Token": "supersecret"})
    assert resp.status_code == 200


def test_chat_rejects_missing_token_when_configured(fake_provider):
    with TestClient(create_openai_app(api_token="supersecret")) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Request-Validierung
# ---------------------------------------------------------------------------


def test_chat_rejects_missing_messages(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post("/v1/chat/completions", json={"model": "gemma4:12b"})
    assert resp.status_code == 400


def test_chat_rejects_empty_messages(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post("/v1/chat/completions", json={"messages": []})
    assert resp.status_code == 400


def test_chat_rejects_message_without_content(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user"}]},
        )
    assert resp.status_code == 400

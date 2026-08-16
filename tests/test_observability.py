"""
◑ MiMi Nox – Observability-Tests (Phase 4 Item 15)
tests/test_observability.py

Verifiziert:
  - serve: X-Request-ID Header auf allen Responses (+ Body-id Korrelation)
  - serve: Fehler-Body trägt stabile Error-Codes + request_id
  - serve: SSE-Stream-Fehler emitieren error.code == "stream_error"
  - CLI:   JSON-Error-Output trägt stabile code_id neben dem Exit-Code

Läuft offline: build_provider_client wird mit einem Fake-AsyncClient gemockt.
"""
from __future__ import annotations

import argparse
import json

import pytest
from fastapi.testclient import TestClient

from server.openai import create_openai_app

CHUNKS = ["Hello", " from", " the", " Black", " Forest"]


class FakeClient:
    """Ersatz für build_provider_client(): liefert einen AsyncIterator."""

    def chat(self, model, messages, stream):  # noqa: ARG002
        async def _gen():
            for chunk in CHUNKS:
                yield {"message": {"content": chunk}}

        return _gen()


class BreakingClient:
    """Chat, der nach dem ersten Chunk mit RuntimeError abbricht (Stream-Fehler)."""

    def chat(self, model, messages, stream):  # noqa: ARG002
        async def _gen():
            yield {"message": {"content": "teil"}}
            raise RuntimeError("upstream kaputt")

        return _gen()


@pytest.fixture
def fake_provider(monkeypatch):
    monkeypatch.setattr("server.openai.build_provider_client", lambda *a, **k: FakeClient())


@pytest.fixture
def breaking_provider(monkeypatch):
    monkeypatch.setattr("server.openai.build_provider_client", lambda *a, **k: BreakingClient())


# ---------------------------------------------------------------------------
# X-Request-ID Header
# ---------------------------------------------------------------------------


def test_models_response_has_request_id_header(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.get("/v1/models")
    assert resp.status_code == 200
    rid = resp.headers.get("x-request-id")
    assert rid and rid.startswith("chatcmpl-")


def test_chat_response_has_request_id_header_correlated_with_body(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post(
            "/v1/chat/completions",
            json={"model": "gemma4:12b", "messages": [{"role": "user", "content": "hi"}]},
        )
    assert resp.status_code == 200
    rid = resp.headers.get("x-request-id")
    assert rid
    body_id = resp.json()["id"]
    assert body_id == rid  # Header und Body korrelieren


# ---------------------------------------------------------------------------
# Stabile Error-Codes
# ---------------------------------------------------------------------------


def test_validation_error_has_stable_code_and_request_id(fake_provider):
    with TestClient(create_openai_app()) as client:
        resp = client.post("/v1/chat/completions", json={"model": "gemma4:12b"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["request_id"]
    assert resp.headers.get("x-request-id") == body["error"]["request_id"]


def test_auth_error_has_stable_code():
    with TestClient(create_openai_app(api_token="supersecret")) as client:
        resp = client.get("/v1/models")  # ohne X-Auth-Token
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"]["code"] == "auth_error"
    assert body["error"]["request_id"]


def test_stream_error_emits_stable_code(breaking_provider):
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
            body = resp.read().decode()
    # Erster Daten-Chunk + Fehler-Chunk (kein [DONE], da der Stream abbricht)
    events = [e for e in body.split("\n\n") if e]
    data_lines = [e for e in events if e.startswith("data:")]
    err_payload = json.loads(data_lines[-1][len("data: ") :])
    assert err_payload["error"]["code"] == "stream_error"
    assert "upstream kaputt" in err_payload["error"]["message"]


# ---------------------------------------------------------------------------
# CLI – stabile Error-Codes
# ---------------------------------------------------------------------------


def test_cli_emit_error_json_has_code_id(capsys):
    from miminox_cli import _emit_error

    args = argparse.Namespace(json=True)
    _emit_error(args, 1, "kaputt", "fix it")
    data = json.loads(capsys.readouterr().out)
    assert data["error"]["code"] == 1
    assert data["error"]["code_id"] == "runtime_error"
    assert data["error"]["message"] == "kaputt"
    assert data["error"]["fix"] == "fix it"


def test_cli_emit_error_usage_code_id(capsys):
    from miminox_cli import _emit_error

    args = argparse.Namespace(json=True)
    _emit_error(args, 2, "bad args", "")
    data = json.loads(capsys.readouterr().out)
    assert data["error"]["code"] == 2
    assert data["error"]["code_id"] == "usage_error"

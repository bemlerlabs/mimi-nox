from __future__ import annotations

import importlib
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _reload_provider(monkeypatch, **env):
    for key in [
        "MIMI_MODEL_PROVIDER",
        "MIMI_NOX_MODEL",
        "MIMI_CUSTOM_OLLAMA_BASE_URL",
        "MIMI_OPENAI_COMPAT_BASE_URL",
        "MIMI_OPENAI_COMPAT_API_KEY",
        "MIMI_LOCAL_OLLAMA_BASE_URL",
        "OLLAMA_HOST",
    ]:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    import core.model_provider as provider

    return importlib.reload(provider)


def test_given_fresh_environment_when_provider_loaded_then_local_ollama_e4b_is_default(monkeypatch):
    """
    GIVEN no provider env configuration
    WHEN the model provider is loaded
    THEN MiMi Nox defaults to local Ollama with Gemma 4 E4B.
    """
    provider = _reload_provider(monkeypatch)
    active = provider.get_active_provider()
    assert active.provider == "local_ollama"
    assert active.model == "gemma4:e4b"
    assert active.base_url == "http://localhost:11434"
    assert active.offline_capable is True
    assert active.requires_internet is False


def test_given_ollama_host_env_when_provider_loaded_then_local_provider_uses_that_endpoint(monkeypatch):
    """
    GIVEN Docker or a user start script points Ollama at a reachable host
    WHEN the local provider is loaded
    THEN chat uses the same endpoint instead of silently falling back to localhost.
    """
    provider = _reload_provider(monkeypatch, OLLAMA_HOST="http://host.docker.internal:11434")
    active = provider.get_active_provider()
    assert active.provider == "local_ollama"
    assert active.base_url == "http://host.docker.internal:11434"


def test_given_provider_config_when_validated_then_only_supported_types_are_allowed(monkeypatch):
    """
    GIVEN provider configuration
    WHEN provider types are validated
    THEN only the first release provider set is accepted.
    """
    provider = _reload_provider(monkeypatch)
    assert provider.validate_provider_type("local_ollama") == "local_ollama"
    assert provider.validate_provider_type("custom_ollama") == "custom_ollama"
    assert provider.validate_provider_type("openai_compatible") == "openai_compatible"
    with pytest.raises(ValueError):
        provider.validate_provider_type("random_cloud")


def test_given_custom_ollama_when_client_built_then_custom_base_url_is_used(monkeypatch):
    """
    GIVEN a user-owned Ollama-compatible endpoint
    WHEN a provider client is created
    THEN the Ollama client receives that exact base URL.
    """
    provider = _reload_provider(
        monkeypatch,
        MIMI_MODEL_PROVIDER="custom_ollama",
        MIMI_CUSTOM_OLLAMA_BASE_URL="http://192.168.1.25:11434",
    )
    active = provider.get_active_provider()
    with patch("core.model_provider.ollama.AsyncClient") as client_cls:
        provider.build_provider_client(active)
    client_cls.assert_called_once_with(host="http://192.168.1.25:11434")


def test_given_openai_compatible_without_key_when_checked_then_setup_error_is_clear(monkeypatch):
    """
    GIVEN an online provider without an API key
    WHEN runtime readiness is checked
    THEN the error is explicit and no network call is attempted.
    """
    provider = _reload_provider(
        monkeypatch,
        MIMI_MODEL_PROVIDER="openai_compatible",
        MIMI_OPENAI_COMPAT_BASE_URL="https://api.example.test/v1",
    )
    active = provider.get_active_provider()
    with pytest.raises(provider.ProviderSetupError, match="API key"):
        provider.ensure_provider_ready(active)


def test_given_openai_compatible_without_base_url_when_checked_then_setup_error_is_clear(monkeypatch):
    """
    GIVEN an online provider with a key but no endpoint
    WHEN runtime readiness is checked
    THEN the user gets a setup error before any network request.
    """
    provider = _reload_provider(
        monkeypatch,
        MIMI_MODEL_PROVIDER="openai_compatible",
        MIMI_OPENAI_COMPAT_API_KEY="test-key",
    )
    active = provider.get_active_provider()
    with pytest.raises(provider.ProviderSetupError, match="base URL"):
        provider.ensure_provider_ready(active)


@pytest.mark.asyncio
async def test_given_openai_compatible_when_client_built_then_configured_base_url_is_used(monkeypatch):
    """
    GIVEN a user-owned OpenAI-compatible API endpoint
    WHEN chat is called through the central provider client
    THEN the request is sent to that configured endpoint with the server-side key.
    """
    provider = _reload_provider(
        monkeypatch,
        MIMI_MODEL_PROVIDER="openai_compatible",
        MIMI_OPENAI_COMPAT_BASE_URL="https://api.example.test/v1",
        MIMI_OPENAI_COMPAT_API_KEY="test-key",
        MIMI_OPENAI_COMPAT_MODEL="custom-model",
    )
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}]}

    class FakeHttpClient:
        def __init__(self, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, *, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr(provider.httpx, "AsyncClient", FakeHttpClient)
    client = provider.build_provider_client(provider.get_active_provider())
    response = await client.chat(
        model="custom-model",
        messages=[{"role": "user", "content": "hello"}],
        stream=False,
    )

    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "custom-model"
    assert captured["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert response.message.content == "ok"


def test_given_model_provider_api_when_health_and_provider_loaded_then_offline_flags_match(monkeypatch, tmp_path):
    """
    GIVEN local Ollama is the active provider
    WHEN /api/health and /api/model/providers are called
    THEN both expose offline-capable local provider state.
    """
    _reload_provider(monkeypatch)
    monkeypatch.setenv("MIMI_NOX_MEMORY_DIR", str(tmp_path / "memory"))
    monkeypatch.setenv("MIMI_NOX_SKILLS_DIR", str(tmp_path / "skills"))

    from server.main import create_app

    with patch(
        "server.routes.health.check_ollama_connection",
        new=AsyncMock(return_value=(True, "ok", ["gemma4:e4b"])),
    ), patch(
        "server.routes.health.ConnectivityProbe.check_remote",
        new=AsyncMock(return_value=False),
    ), patch(
        "server.routes.health.get_router"
    ) as router_getter:
        router_getter.return_value.invalidate_cache.return_value = None
        router_getter.return_value.resolve = AsyncMock()
        from core.model_config import ModelConfig, ModelTier

        router_getter.return_value.resolve.return_value = ModelConfig(
            name="gemma4:e4b",
            tier=ModelTier.FAST,
        )
        client = TestClient(create_app())
        provider_res = client.get("/api/model/providers")
        health_res = client.get("/api/health")

    assert provider_res.status_code == 200
    provider_data = provider_res.json()
    assert provider_data["active"]["provider"] == "local_ollama"
    assert provider_data["active"]["offline_capable"] is True
    assert provider_data["active"]["requires_internet"] is False

    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["active_provider"] == "local_ollama"
    assert health_data["offline_capable"] is True
    assert health_data["requires_internet"] is False

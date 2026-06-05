"""Offline-first model provider configuration for MiMi Nox.

The default provider is always local Ollama. Advanced users can opt in to a
custom Ollama endpoint or an OpenAI-compatible API, but those modes must be
explicit and visible to the UI.
"""
from __future__ import annotations

import os
import json
from dataclasses import asdict, dataclass
from typing import Any, AsyncIterator, Literal

import httpx
import ollama


ProviderType = Literal["local_ollama", "custom_ollama", "openai_compatible"]
SUPPORTED_PROVIDER_TYPES = {"local_ollama", "custom_ollama", "openai_compatible"}
DEFAULT_LOCAL_MODEL = "gemma4:12b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


class ProviderSetupError(RuntimeError):
    """Raised when an opt-in provider is configured incompletely."""


@dataclass(frozen=True)
class ModelProviderConfig:
    provider: ProviderType
    model: str
    base_url: str
    label: str
    offline_capable: bool
    requires_internet: bool
    advanced_opt_in: bool = False
    api_key_configured: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProviderFunctionCall:
    name: str
    arguments: dict


@dataclass
class ProviderToolCall:
    function: ProviderFunctionCall


@dataclass
class ProviderMessage:
    content: str = ""
    thinking: str = ""
    tool_calls: list[ProviderToolCall] | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)


@dataclass
class ProviderChatResponse:
    message: ProviderMessage

    def __getitem__(self, key: str) -> Any:
        if key == "message":
            return {"content": self.message.content}
        raise KeyError(key)


class OpenAICompatibleAsyncClient:
    """Small adapter exposing the subset of Ollama's AsyncClient used here."""

    def __init__(self, *, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _chat_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _convert_messages(self, messages: list[dict]) -> list[dict]:
        converted: list[dict] = []
        for msg in messages:
            role = getattr(msg, "role", None) or msg.get("role", "user")
            content = getattr(msg, "content", None) or msg.get("content", "")
            images = msg.get("images") if isinstance(msg, dict) else None
            if images:
                parts: list[dict] = [{"type": "text", "text": str(content)}]
                for image_b64 in images:
                    parts.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        }
                    )
                converted.append({"role": role, "content": parts})
            else:
                converted.append({"role": role, "content": str(content)})
        return converted

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        stream: bool = False,
        tools: list[dict] | None = None,
        **_: Any,
    ) -> ProviderChatResponse | AsyncIterator[dict]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._convert_messages(messages),
            "stream": stream,
        }
        # External APIs stay text/vision-only for now. Local Ollama remains the
        # safe default for tool execution and sandbox approvals.
        _ = tools

        if stream:
            return self._stream_chat(payload)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(self._chat_url(), headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        message = data.get("choices", [{}])[0].get("message", {})
        return ProviderChatResponse(
            message=ProviderMessage(content=message.get("content") or "")
        )

    async def _stream_chat(self, payload: dict[str, Any]) -> AsyncIterator[dict]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                self._chat_url(),
                headers=self._headers(),
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if raw == "[DONE]":
                        break
                    if not raw:
                        continue
                    data = json.loads(raw)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content") or ""
                    if content:
                        yield {"message": {"content": content}}


_ACTIVE_OVERRIDE: ModelProviderConfig | None = None


def validate_provider_type(provider: str) -> ProviderType:
    if provider not in SUPPORTED_PROVIDER_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_PROVIDER_TYPES))
        raise ValueError(f"Unsupported model provider '{provider}'. Allowed: {allowed}")
    return provider  # type: ignore[return-value]


def _base_url(value: str | None, default: str = DEFAULT_OLLAMA_BASE_URL) -> str:
    raw = (value or default).strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = f"http://{raw}"
    return raw


def _provider_from_env() -> ModelProviderConfig:
    provider = validate_provider_type(os.environ.get("MIMI_MODEL_PROVIDER", "local_ollama"))

    if provider == "custom_ollama":
        return ModelProviderConfig(
            provider="custom_ollama",
            model=os.environ.get("MIMI_NOX_MODEL", DEFAULT_LOCAL_MODEL),
            base_url=_base_url(os.environ.get("MIMI_CUSTOM_OLLAMA_BASE_URL")),
            label="Custom Ollama",
            offline_capable=True,
            requires_internet=False,
            advanced_opt_in=True,
        )

    if provider == "openai_compatible":
        return ModelProviderConfig(
            provider="openai_compatible",
            model=os.environ.get("MIMI_OPENAI_COMPAT_MODEL", "custom-model"),
            base_url=_base_url(os.environ.get("MIMI_OPENAI_COMPAT_BASE_URL"), ""),
            label="OpenAI-compatible API",
            offline_capable=False,
            requires_internet=True,
            advanced_opt_in=True,
            api_key_configured=bool(os.environ.get("MIMI_OPENAI_COMPAT_API_KEY")),
        )

    return ModelProviderConfig(
        provider="local_ollama",
        model=os.environ.get("MIMI_NOX_MODEL", DEFAULT_LOCAL_MODEL),
        base_url=_base_url(os.environ.get("MIMI_LOCAL_OLLAMA_BASE_URL")),
        label="Local Ollama",
        offline_capable=True,
        requires_internet=False,
    )


def get_active_provider() -> ModelProviderConfig:
    return _ACTIVE_OVERRIDE or _provider_from_env()


def set_active_provider(
    *,
    provider: str,
    model: str | None = None,
    base_url: str | None = None,
) -> ModelProviderConfig:
    """Set a session-local provider override used until process restart."""
    global _ACTIVE_OVERRIDE
    provider_type = validate_provider_type(provider)

    if provider_type == "local_ollama":
        config = ModelProviderConfig(
            provider="local_ollama",
            model=model or DEFAULT_LOCAL_MODEL,
            base_url=_base_url(base_url),
            label="Local Ollama",
            offline_capable=True,
            requires_internet=False,
        )
    elif provider_type == "custom_ollama":
        config = ModelProviderConfig(
            provider="custom_ollama",
            model=model or DEFAULT_LOCAL_MODEL,
            base_url=_base_url(base_url),
            label="Custom Ollama",
            offline_capable=True,
            requires_internet=False,
            advanced_opt_in=True,
        )
    else:
        config = ModelProviderConfig(
            provider="openai_compatible",
            model=model or "custom-model",
            base_url=_base_url(base_url, ""),
            label="OpenAI-compatible API",
            offline_capable=False,
            requires_internet=True,
            advanced_opt_in=True,
            api_key_configured=bool(os.environ.get("MIMI_OPENAI_COMPAT_API_KEY")),
        )

    _ACTIVE_OVERRIDE = config
    return config


def list_provider_options() -> list[dict]:
    return [
        ModelProviderConfig(
            provider="local_ollama",
            model=DEFAULT_LOCAL_MODEL,
            base_url=DEFAULT_OLLAMA_BASE_URL,
            label="Local Ollama",
            offline_capable=True,
            requires_internet=False,
        ).to_dict(),
        ModelProviderConfig(
            provider="custom_ollama",
            model=DEFAULT_LOCAL_MODEL,
            base_url=DEFAULT_OLLAMA_BASE_URL,
            label="Custom Ollama",
            offline_capable=True,
            requires_internet=False,
            advanced_opt_in=True,
        ).to_dict(),
        ModelProviderConfig(
            provider="openai_compatible",
            model="custom-model",
            base_url="",
            label="OpenAI-compatible API",
            offline_capable=False,
            requires_internet=True,
            advanced_opt_in=True,
            api_key_configured=bool(os.environ.get("MIMI_OPENAI_COMPAT_API_KEY")),
        ).to_dict(),
    ]


def ensure_provider_ready(config: ModelProviderConfig | None = None) -> None:
    active = config or get_active_provider()
    if active.provider == "openai_compatible" and not active.api_key_configured:
        raise ProviderSetupError(
            "OpenAI-compatible API provider selected, but no API key is configured. "
            "Set MIMI_OPENAI_COMPAT_API_KEY or switch back to Local Ollama."
        )
    if active.provider == "openai_compatible" and not active.base_url:
        raise ProviderSetupError(
            "OpenAI-compatible API provider selected, but no base URL is configured. "
            "Set MIMI_OPENAI_COMPAT_BASE_URL or switch back to Local Ollama."
        )


def build_provider_client(config: ModelProviderConfig | None = None) -> Any:
    active = config or get_active_provider()
    ensure_provider_ready(active)
    if active.provider == "openai_compatible":
        return OpenAICompatibleAsyncClient(
            base_url=active.base_url,
            api_key=os.environ["MIMI_OPENAI_COMPAT_API_KEY"],
        )
    return ollama.AsyncClient(host=active.base_url)

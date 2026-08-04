"""server/routes/health.py – GET /api/health

Erweitert um Hybrid-Architektur Informationen:
  - active_tier:  welcher Tier gerade aktiv ist (offline | fast | power)
  - active_model: welches Modell gerade genutzt wird
  - dgx_online:   ob der DGX Remote-Server erreichbar ist
"""
from __future__ import annotations

import asyncio
import json
import urllib.request

from fastapi import APIRouter
from pydantic import BaseModel

from core import __version__
from core.connectivity_probe import ConnectivityProbe
from core.model_provider import get_active_provider
from core.model_router import get_router

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    ollama: bool
    models: list[str]
    # Hybrid-Architektur Felder
    active_tier:  str
    active_model: str
    dgx_online:   bool
    active_provider: str
    offline_capable: bool
    requires_internet: bool
    model_installed: bool = True
    detail: str = ""


async def _quick_ollama_status(base_url: str, model: str) -> tuple[bool, bool, list[str], str]:
    """Fast, non-blocking UI health probe for local/custom Ollama."""
    url = f"{base_url.rstrip('/')}/api/tags"

    def _fetch() -> tuple[bool, bool, list[str], str]:
        try:
            with urllib.request.urlopen(url, timeout=0.75) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            models = [
                str(item.get("name") or item.get("model") or "")
                for item in payload.get("models", [])
                if item.get("name") or item.get("model")
            ]
            installed = any(name == model or model in name for name in models)
            detail = "connected" if installed else f"model not installed: {model}"
            return True, installed, models, detail
        except Exception as exc:
            return False, False, [], f"ollama offline: {exc}"

    return await asyncio.to_thread(_fetch)


async def check_ollama_connection(model: str) -> tuple[bool, str, list[str]]:
    """Backward-compatible health probe used by tests and older call sites."""
    provider = get_active_provider()
    connected, _installed, models, detail = await _quick_ollama_status(provider.base_url, model)
    return connected, detail, models


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Prüft ob der Server, Ollama und optional der DGX erreichbar sind.
    Gibt immer Status 200 zurück.

    Neu in v4.1:
      - active_tier:  "offline" | "fast" | "power"
      - active_model: z.B. "gemma4:e4b"
      - dgx_online:   True wenn DGX Remote-Server erreichbar

    Optimierung: Eine geteilte ConnectivityProbe-Instanz für Router + DGX-Check
    vermeidet doppelte Netzwerkaufrufe beim gleichen Health-Poll.
    """
    import os

    provider = get_active_provider()
    active_model = provider.model
    connected = False
    model_installed = True
    all_models: list[str] = []
    detail = ""
    dgx_online = False
    active_tier = "offline"

    if provider.provider in {"local_ollama", "custom_ollama"}:
        connected, detail, all_models = await check_ollama_connection(active_model)
        model_installed = any(name == active_model or active_model in name for name in all_models)
        if connected:
            active_tier = "fast" if model_installed else "offline"

    if os.environ.get("MIMI_NOX_HEALTH_DEEP") == "1":
        try:
            shared_probe = ConnectivityProbe(dgx_host=os.environ.get("MIMI_DGX_HOST"))
            router_inst = get_router()
            active_config = await router_inst.resolve()
            active_tier = active_config.tier.value
            active_model = provider.model or active_config.name
            dgx_online = await shared_probe.check_remote()
            connected, model_installed, all_models, detail = await _quick_ollama_status(
                provider.base_url,
                active_model,
            )
        except Exception:
            connected = False
            model_installed = False
            all_models = []
            detail = "deep health check failed"

    nox_models = [m for m in all_models if active_model in m]

    return HealthResponse(
        status="ok",
        version=__version__,
        ollama=connected,
        models=nox_models if nox_models else ([active_model] if connected else []),
        active_tier=active_tier,
        active_model=active_model,
        dgx_online=dgx_online,
        active_provider=provider.provider,
        offline_capable=provider.offline_capable,
        requires_internet=provider.requires_internet,
        model_installed=model_installed,
        detail=detail,
    )

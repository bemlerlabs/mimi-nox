"""server/routes/health.py – GET /api/health

Erweitert um Hybrid-Architektur Informationen:
  - active_tier:  welcher Tier gerade aktiv ist (offline | fast | power)
  - active_model: welches Modell gerade genutzt wird
  - dgx_online:   ob der DGX Remote-Server erreichbar ist
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from core import __version__
from core.chat import check_ollama_connection
from core.connectivity_probe import ConnectivityProbe
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

    # Geteilte Probe-Instanz → Router + DGX-Status aus einem einzigen Netzwerkaufruf
    shared_probe = ConnectivityProbe(
        dgx_host=os.environ.get("MIMI_DGX_HOST")
    )
    router_inst = get_router()
    router_inst.invalidate_cache()  # Frischer Check bei jedem Health-Call

    # Resolve nutzt die frische Probe (Probe-Ergebnis wird gecacht für den DGX-Check)
    active_config = await router_inst.resolve()

    # DGX-Status — nutzt den Cache der shared_probe wenn bereits aufgerufen
    dgx_online = await shared_probe.check_remote()

    # Lokales Ollama prüfen (für Legacy-Feld)
    connected, _, all_models = await check_ollama_connection(model="")
    nox_models = [m for m in all_models if active_config.name in m]

    return HealthResponse(
        status="ok",
        version=__version__,
        ollama=connected,
        models=nox_models if nox_models else ([active_config.name] if connected else []),
        active_tier=active_config.tier.value,
        active_model=active_config.name,
        dgx_online=dgx_online,
    )

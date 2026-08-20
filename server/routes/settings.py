"""server/routes/settings.py – GET/POST /api/settings

Single Source of Truth für die PWA-Einstellungen.

Warum: Das Frontend (ChatInput, SettingsPanel) ruft `getSettings()` →
`GET /api/settings`. Diese Route existierte vorher nicht → 404 →
`catch(() => {})` schluckte den Fehler → hartkodiertes `gemma4:e4b`
blieb als aktives Modell stehen, obwohl die Engine (CLI/`engine.json`)
Qwen/DGX nutzte.

Dieser Endpunkt liefert das **aktiv konfigurierte** Modell aus
`get_active_provider()` (das `engine.json` + Env liest) — exakt die
Engine, mit der `miminox tui` / `miminox start` läuft. Damit zeigt die
PWA immer dasselbe Modell wie die CLI (eine Quelle).

POST /api/settings wendet eine Provider-Auswahl an (per
`set_active_provider`, persistiert in engine.json) und gibt das neue
aktive Modell zurück.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.model_provider import (
    ProviderSetupError,
    get_active_provider,
    set_active_provider,
    validate_provider_type,
)
from core.engine_config import EngineChoice, save_engine_config

router = APIRouter(tags=["Settings"])


class ProviderSettings(BaseModel):
    type: str
    endpoint: str | None = None
    api_key: str | None = None
    model: str | None = None


class SettingsRequest(BaseModel):
    provider: ProviderSettings | None = None
    memory_enabled: bool | None = None
    language: str | None = None
    theme: str | None = None


def _active_provider_dict() -> dict:
    """Aktiven Provider in die Frontend-Shape (AppSettings.provider) mappen."""
    active = get_active_provider()
    return {
        "type": active.provider,
        "endpoint": active.base_url,
        "api_key": os.environ.get("MIMI_OPENAI_COMPAT_API_KEY", ""),
        "model": active.model,
    }


@router.get("/settings")
async def get_settings() -> dict:
    """Gibt die aktiven Einstellungen (Single Source of Truth) zurück."""
    return {
        "provider": _active_provider_dict(),
        "memory_enabled": os.environ.get("MIMI_MEMORY_ENABLED", "1") != "0",
        "language": os.environ.get("MIMI_LANGUAGE", "de"),
        "theme": os.environ.get("MIMI_THEME", "dark"),
    }


@router.post("/settings")
async def update_settings(req: SettingsRequest) -> dict:
    """Wendet eine Provider-Auswahl an und gibt das neue aktive Modell zurück.

    Persistiert in engine.json (via set_active_provider) — damit CLI und PWA
    dieselbe Engine behalten (eine Quelle).
    """
    if req.provider is not None:
        try:
            provider_type = validate_provider_type(req.provider.type)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if provider_type == "openai_compatible" and req.provider.api_key:
            os.environ["MIMI_OPENAI_COMPAT_API_KEY"] = req.provider.api_key

        try:
            set_active_provider(
                provider=provider_type,
                model=req.provider.model,
                base_url=req.provider.endpoint,
            )
        except ProviderSetupError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    if req.memory_enabled is not None:
        os.environ["MIMI_MEMORY_ENABLED"] = "1" if req.memory_enabled else "0"
    if req.language:
        os.environ["MIMI_LANGUAGE"] = req.language
    if req.theme:
        os.environ["MIMI_THEME"] = req.theme

    # Persistenz: engine.json ist die gemeinsame Quelle für CLI + PWA.
    # set_active_provider() ist nur session-lokal — ohne save_engine_config
    # würde die CLI beim nächsten Start wieder die alte Engine nutzen
    # (zwei Quellen statt einer).
    if req.provider is not None:
        active = get_active_provider()
        try:
            save_engine_config(EngineChoice(
                provider=active.provider,
                model=active.model,
                api_url=active.base_url if active.provider == "openai_compatible" else None,
            ))
        except Exception:
            pass  # Persistenz ist best-effort; die session-lokale Auswahl greift trotzdem.

    return {
        "provider": _active_provider_dict(),
        "memory_enabled": os.environ.get("MIMI_MEMORY_ENABLED", "1") != "0",
        "language": os.environ.get("MIMI_LANGUAGE", "de"),
        "theme": os.environ.get("MIMI_THEME", "dark"),
    }

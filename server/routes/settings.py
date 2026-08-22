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

import json
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.model_provider import (
    ProviderSetupError,
    get_active_provider,
    set_active_provider,
    validate_provider_type,
)
from core.engine_config import EngineChoice, load_engine_config, save_engine_config, clear_engine_config

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
                # api_url bei Ollama-Remote UND OpenAI-kompatibel persistieren:
                # ohne URL würde ein externer Ollama-Endpunkt (z.B. DGX via LAN)
                # nach dem Server-Neustart auf localhost:11434 fallen.
                api_url=active.base_url
                if active.provider in ("openai_compatible", "custom_ollama")
                and active.base_url
                else None,
            ))
        except Exception:
            pass  # Persistenz ist best-effort; die session-lokale Auswahl greift trotzdem.

    return {
        "provider": _active_provider_dict(),
        "memory_enabled": os.environ.get("MIMI_MEMORY_ENABLED", "1") != "0",
        "language": os.environ.get("MIMI_LANGUAGE", "de"),
        "theme": os.environ.get("MIMI_THEME", "dark"),
    }


# ── Setup-Status (First-Run-Gate der PWA) ──────────────────────────────────
# Root-Cause: Die PWA wusste beim ersten Start nie, ob schon eine Engine
# gewählt wurde — deshalb zeigte sie den alten Tauri-Only-Onboarding-Wizard
# (check_ollama via IPC), der im Browser nie lief. /api/setup/status ist
# die Single Source of Truth für "braucht der User die Engine-Auswahl?".


def _setup_provider_dict() -> dict:
    """Aktive Engine + Erreichbarkeits-Status für die Setup-UI."""
    persisted = load_engine_config()
    active = get_active_provider()
    provider = persisted.provider if persisted else active.provider
    model = persisted.model if (persisted and persisted.model) else active.model
    url = persisted.api_url if persisted else (active.base_url if active.provider == "openai_compatible" else None)
    reachable = False
    available_models: list[str] = []
    if provider in ("local_ollama", "custom_ollama"):
        reachable, available_models = _probe_local(provider, url)
    elif provider == "openai_compatible" and url:
        reachable, available_models = _probe_remote(url)
    return {
        "configured": persisted is not None,
        "provider": provider,
        "model": model,
        "url": url,
        "reachable": reachable,
        "available_models": available_models,
    }


def _probe_local(provider: str, url: str | None):
    """Synchroner Ollama-Probe (für den Status-Call ohne async-Kontext)."""
    import urllib.request

    base = (url or ("http://127.0.0.1:11434" if provider == "local_ollama" else "")).strip()
    if base and not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    base = base.rstrip("/")
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        names = [str(m.get("name") or "") for m in data.get("models", []) if m.get("name")]
        return True, names
    except Exception:
        return False, []


def _probe_remote(url: str):
    """Synchroner OpenAI-kompatibler Probe (GET /v1/models)."""
    import urllib.request

    base = url.strip().rstrip("/")
    if not base.startswith(("http://", "https://")):
        base = f"http://{base}"
    if base.endswith("/v1"):
        base = base[:-3]
    headers = {}
    key = os.environ.get("MIMI_OPENAI_COMPAT_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        req = urllib.request.Request(f"{base}/v1/models", headers=headers)
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        ids = [str(m.get("id") or "") for m in data.get("data", []) if m.get("id")]
        return True, ids
    except Exception:
        return False, []


@router.get("/setup/status")
async def get_setup_status() -> dict:
    """Gibt an, ob der User schon eine Engine gewählt hat.

    configured=True  → engine.json existiert → PWA springt direkt in den Chat.
    configured=False → PWA zeigt die Engine-Auswahl (End-User-Choice).
    reachable/available_models sind ein Bonus: die PWA kann die erkannten
    Modelle direkt als Auswahl anbieten (z.B. alle lokalen Ollama-Modelle).
    """
    return _setup_provider_dict()


@router.post("/setup/reset")
async def reset_setup() -> dict:
    """Löscht die Engine-Auswahl (engine.json) — der User wählt neu.

    Session-lokal bleibt der aktuelle Provider aktiv, bis neu gewählt wird.
    """
    clear_engine_config()
    return {"configured": False}

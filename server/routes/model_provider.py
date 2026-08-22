"""Model provider API for offline-first and advanced opt-in providers."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.chat import list_local_model_options, list_local_models
from core.model_provider import (
    ProviderSetupError,
    get_active_provider,
    list_provider_options,
    set_active_provider,
    validate_provider_type,
)


router = APIRouter(tags=["Model Provider"])


class ProviderUpdateRequest(BaseModel):
    provider: str
    model: str | None = None
    base_url: str | None = None
    confirm_online: bool = False


class ProviderProbeRequest(BaseModel):
    """Probe-Request: Endpunkt prüfen + verfügbare Modelle auflisten.

    Kein Persist, kein Setup — reine Erkennung. So kann die PWA nach der
    Installation alle lokalen/externen Engines erkennen, ohne dass der User
    Befehle tippen muss (User-Mandat: 'nicht Hardcore, auswählen können').
    """

    provider: str  # local_ollama | custom_ollama | openai_compatible
    base_url: str | None = None
    api_key: str | None = None


async def _probe_ollama(base_url: str | None) -> tuple[bool, list[str], str]:
    """Ollama-Protokoll-Check: GET {base}/api/tags (leichter Metadata-Call)."""
    base = (base_url or "").strip().rstrip("/")
    if not base:
        base = "http://127.0.0.1:11434"
    if "://" not in base:
        base = f"http://{base}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            data = resp.json()
        names = [str(m.get("name") or "") for m in data.get("models", []) if m.get("name")]
        return True, names, f"{base} erreichbar · {len(names)} Modelle"
    except httpx.HTTPStatusError as exc:
        return False, [], f"{base} antwortet mit HTTP {exc.response.status_code}"
    except Exception:
        return False, [], f"{base} nicht erreichbar"


async def _probe_openai_compatible(base_url: str, api_key: str | None) -> tuple[bool, list[str], str]:
    """OpenAI-kompatibler Engine-Check: GET {base}/v1/models.

    Root-Cause (wie check_engine_connection): Metadata-Endpunkt statt
    Chat-Request — ein 27B-Modell braucht Sekunden für die erste Inferenz,
    /v1/models antwortet in ~100ms.
    """
    base = (base_url or "").strip().rstrip("/")
    if not base:
        return False, [], "keine Engine-URL angegeben"
    if "://" not in base:
        base = f"http://{base}"
    if base.endswith("/v1"):
        base = base[:-3]
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base}/v1/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
        ids = [str(m.get("id") or "") for m in data.get("data", []) if m.get("id")]
        return True, ids, f"{base} erreichbar · {len(ids)} Modelle"
    except httpx.HTTPStatusError as exc:
        return False, [], f"{base} antwortet mit HTTP {exc.response.status_code}"
    except Exception:
        return False, [], f"{base} nicht erreichbar"


@router.post("/model/providers/probe")
async def probe_model_provider(req: ProviderProbeRequest) -> dict:
    """Erkennt eine Engine und listet ihre Modelle — ohne etwas zu installieren.

    GIVEN User gibt einen Ollama- oder OpenAI-kompatiblen Endpunkt ein
    WHEN  POST /api/model/providers/probe
    THEN  200 + { reachable, models, detail } (leere Liste = nicht erreichbar
          oder keine Modelle) — die PWA zeigt daraus die Auswahl.
    """
    provider = req.provider.strip()
    if provider in ("local_ollama", "custom_ollama"):
        default = "http://127.0.0.1:11434" if provider == "local_ollama" else None
        ok, models, detail = await _probe_ollama(req.base_url or default)
    elif provider == "openai_compatible":
        ok, models, detail = await _probe_openai_compatible(req.base_url or "", req.api_key)
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Unbekannter Provider '{provider}'. Allowed: local_ollama, custom_ollama, openai_compatible.",
        )
    return {"reachable": ok, "models": models, "detail": detail}


@router.get("/model/providers")
async def get_model_providers() -> dict:
    active = get_active_provider()
    local_model_options = await list_local_model_options()
    return {
        "active": active.to_dict(),
        "providers": list_provider_options(),
        "local_models": await list_local_models(),
        "local_model_options": local_model_options,
    }


@router.put("/model/provider")
async def update_model_provider(req: ProviderUpdateRequest) -> dict:
    try:
        provider = validate_provider_type(req.provider)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    if provider == "openai_compatible" and not req.confirm_online:
        raise HTTPException(
            status_code=409,
            detail="Online/API provider requires explicit confirmation.",
        )

    if provider == "local_ollama":
        local_model_options = await list_local_model_options()
        available = {item["name"] for item in local_model_options}
        if req.model and available and req.model not in available:
            raise HTTPException(
                status_code=422,
                detail=f"Lokales Modell '{req.model}' ist nicht installiert oder kein Chat-Modell.",
            )

    try:
        active = set_active_provider(
            provider=provider,
            model=req.model,
            base_url=req.base_url,
        )
    except ProviderSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"active": active.to_dict()}

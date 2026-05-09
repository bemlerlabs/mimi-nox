"""Model provider API for offline-first and advanced opt-in providers."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.chat import list_local_models
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


@router.get("/model/providers")
async def get_model_providers() -> dict:
    active = get_active_provider()
    return {
        "active": active.to_dict(),
        "providers": list_provider_options(),
        "local_models": await list_local_models(),
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

    try:
        active = set_active_provider(
            provider=provider,
            model=req.model,
            base_url=req.base_url,
        )
    except ProviderSetupError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"active": active.to_dict()}

"""
◑ MiMi Nox – Model Router
core/model_router.py

Wählt automatisch den besten verfügbaren Modell-Tier:
  OFFLINE → FAST → POWER

Entscheidungslogik:
  1. MIMI_FORCE_TIER env-var oder force_tier-Parameter → immer dieser Tier
  2. ConnectivityProbe prüft lokales Ollama + DGX Remote
  3. Ergebnis wird gecacht bis invalidate_cache() aufgerufen wird

Beispiel:
    router = get_router()
    config = await router.resolve()
    # → ModelConfig(name="gemma4:e4b", tier=FAST, host="localhost:11434")

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import os

from core.model_config import ModelConfig, ModelTier, get_model_config
from core.connectivity_probe import ConnectivityProbe


class ModelRouter:
    """
    Entscheidet welcher Modell-Tier genutzt wird.

    Priorität:
      1. force_tier Parameter (direkte Anforderung)
      2. MIMI_FORCE_TIER Env-Variable (Developer-Override)
      3. ConnectivityProbe (automatisch — beste verfügbare Option)
    """

    def __init__(self, probe: ConnectivityProbe | None = None) -> None:
        self._probe = probe or ConnectivityProbe(
            dgx_host=os.environ.get("MIMI_DGX_HOST")
        )
        self._cached_config: ModelConfig | None = None

    async def resolve(self, force_tier: str | None = None) -> ModelConfig:
        """
        Gibt die beste verfügbare ModelConfig zurück.

        Args:
            force_tier: Optionaler Tier-Override ("offline" | "fast" | "power").
                        Überschreibt Probe und Env-Variable.

        Returns:
            ModelConfig für den gewählten Tier.
        """
        # 1. Direkter Parameter-Override
        if force_tier:
            return get_model_config(ModelTier(force_tier))

        # 2. Env-Variable Override
        env_tier = os.environ.get("MIMI_FORCE_TIER")
        if env_tier:
            return get_model_config(ModelTier(env_tier))

        # 3. Cache nutzen wenn vorhanden
        if self._cached_config is not None:
            return self._cached_config

        # 4. Probe befragen und cachen
        tier = await self._probe.best_available_tier()
        config = get_model_config(tier)
        self._cached_config = config
        return config

    def invalidate_cache(self) -> None:
        """
        Leert den Cache. Nächster resolve()-Aufruf befragt die Probe erneut.
        Nützlich wenn sich die Netzwerksituation geändert hat.
        """
        self._cached_config = None


# ── Singleton ──────────────────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_router() -> ModelRouter:
    """
    Gibt den App-weiten ModelRouter zurück (Singleton).
    Beim ersten Aufruf wird er mit den Env-Variablen initialisiert.

    Returns:
        ModelRouter Singleton
    """
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router

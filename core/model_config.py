"""
◑ MiMi Nox – Model Configuration
core/model_config.py

Definiert die drei Modell-Tiers der Hybrid-Architektur:
  - OFFLINE: gemma4:e2b  → läuft auf dem Gerät, kein Internet nötig
  - FAST:    gemma4:12b  → lokal, schnell, multimodal (Consumer HW)
  - POWER:   gemma4:26b  → DGX Backend, maximale Stärke

Alle Werte sind via Env-Variablen überschreibbar:
  MIMI_OFFLINE_MODEL  (default: gemma4:e2b)
  MIMI_FAST_MODEL     (default: gemma4:12b)
  MIMI_POWER_MODEL    (default: gemma4:26b)
  MIMI_DGX_HOST       (default: localhost:11434)
  MIMI_FORCE_TIER     (optional: offline | fast | power)

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


# ── Tier Enum ──────────────────────────────────────────────────────────────

class ModelTier(str, Enum):
    """Die drei Stufen der MIMI Hybrid-Architektur."""
    OFFLINE = "offline"   # gemma4:e2b — kein Netz nötig, immer verfügbar
    FAST    = "fast"      # gemma4:12b — lokal + schnell + multimodal
    POWER   = "power"     # gemma4:26b — DGX Backend, Frontier-Level


# ── ModelConfig Dataclass ──────────────────────────────────────────────────

@dataclass(frozen=True)
class ModelConfig:
    """
    Unveränderliche Konfiguration für ein Modell.

    frozen=True: Kein versehentliches Überschreiben möglich.
    Alle Felder sind read-only nach der Erstellung.
    """
    name: str           # Ollama Modell-Name, z.B. "gemma4:12b"
    tier: ModelTier     # Welcher Tier diese Config gehört
    host: str = "localhost:11434"  # Ollama Host (lokal oder DGX)

    @property
    def is_local(self) -> bool:
        """True wenn der Ollama-Server lokal läuft."""
        return self.host == "localhost:11434"

    @property
    def is_remote(self) -> bool:
        """True wenn der Ollama-Server auf einem Remote-Host läuft (z.B. DGX)."""
        return not self.is_local

    @property
    def base_url(self) -> str:
        """HTTP-Basis-URL für den Ollama-Client."""
        return f"http://{self.host}"


# ── Tier → Config Mapping (mit Env-Variable Override) ─────────────────────

def _build_tier_map() -> dict[ModelTier, ModelConfig]:
    """
    Erstellt die TIER_MAP aus Env-Variablen oder sicheren Defaults.
    Wird beim Modul-Import aufgerufen — und bei importlib.reload() erneut.
    """
    dgx_host = os.environ.get("MIMI_DGX_HOST", "localhost:11434")

    return {
        ModelTier.OFFLINE: ModelConfig(
            name=os.environ.get("MIMI_OFFLINE_MODEL", "gemma4:e2b"),
            tier=ModelTier.OFFLINE,
            host="localhost:11434",  # Offline läuft IMMER lokal
        ),
        ModelTier.FAST: ModelConfig(
            name=os.environ.get("MIMI_FAST_MODEL", "gemma4:12b"),
            tier=ModelTier.FAST,
            host="localhost:11434",  # Fast läuft lokal
        ),
        ModelTier.POWER: ModelConfig(
            name=os.environ.get("MIMI_POWER_MODEL", "gemma4:26b"),
            tier=ModelTier.POWER,
            host=dgx_host,           # Power läuft auf DGX (oder lokal als Fallback)
        ),
    }


# Wird beim Import gebaut — bleibt für die Laufzeit stabil
TIER_MAP: dict[ModelTier, ModelConfig] = _build_tier_map()


def get_model_config(tier: ModelTier) -> ModelConfig:
    """
    Gibt die ModelConfig für den angegebenen Tier zurück.

    Args:
        tier: ModelTier.OFFLINE | FAST | POWER

    Returns:
        ModelConfig mit name, tier, host, is_local, base_url
    """
    return TIER_MAP[tier]

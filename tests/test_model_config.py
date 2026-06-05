"""
◑ MiMi Nox – test_model_config.py

TDD Tests für core/model_config.py (Hybrid-Architektur Tier-System).

Strategie: Given / When / Then
  - Alle Tests sind rein unit-level (kein Netzwerk, kein Ollama)
  - Dreifache Tiefenabdeckung: Datenmodell → Env-Config → Tier-Logik
"""
from __future__ import annotations

import os
import pytest
from unittest.mock import patch


# ── Tiefe 1: Datenmodell ────────────────────────────────────────────────────

class TestModelTier:
    """GIVEN der ModelTier Enum existiert"""

    def test_offline_tier_value(self):
        """WHEN auf ModelTier.OFFLINE zugegriffen wird
        THEN hat er den String-Wert 'offline'"""
        from core.model_config import ModelTier
        assert ModelTier.OFFLINE.value == "offline"

    def test_fast_tier_value(self):
        """WHEN auf ModelTier.FAST zugegriffen wird
        THEN hat er den String-Wert 'fast'"""
        from core.model_config import ModelTier
        assert ModelTier.FAST.value == "fast"

    def test_power_tier_value(self):
        """WHEN auf ModelTier.POWER zugegriffen wird
        THEN hat er den String-Wert 'power'"""
        from core.model_config import ModelTier
        assert ModelTier.POWER.value == "power"

    def test_tier_from_string(self):
        """WHEN ModelTier('fast') aufgerufen wird
        THEN gibt es ModelTier.FAST zurück"""
        from core.model_config import ModelTier
        assert ModelTier("fast") == ModelTier.FAST


class TestModelConfig:
    """GIVEN ein ModelConfig-Objekt"""

    def test_local_config_is_local(self):
        """WHEN host='localhost:11434'
        THEN .is_local gibt True zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)
        assert cfg.is_local is True

    def test_local_config_is_not_remote(self):
        """WHEN host='localhost:11434'
        THEN .is_remote gibt False zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)
        assert cfg.is_remote is False

    def test_remote_config_is_remote(self):
        """WHEN host='192.168.1.50:11434'
        THEN .is_remote gibt True zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(
            name="gemma4:26b",
            tier=ModelTier.POWER,
            host="192.168.1.50:11434",
        )
        assert cfg.is_remote is True

    def test_remote_config_is_not_local(self):
        """WHEN host='dgx.local:11434'
        THEN .is_local gibt False zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(
            name="gemma4:26b",
            tier=ModelTier.POWER,
            host="dgx.local:11434",
        )
        assert cfg.is_local is False

    def test_base_url_local(self):
        """WHEN host='localhost:11434'
        THEN .base_url gibt 'http://localhost:11434' zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)
        assert cfg.base_url == "http://localhost:11434"

    def test_base_url_remote(self):
        """WHEN host='dgx.local:11434'
        THEN .base_url gibt 'http://dgx.local:11434' zurück"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(
            name="gemma4:26b",
            tier=ModelTier.POWER,
            host="dgx.local:11434",
        )
        assert cfg.base_url == "http://dgx.local:11434"

    def test_config_is_immutable(self):
        """WHEN versucht wird, name zu ändern
        THEN wirft es einen FrozenInstanceError"""
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)
        with pytest.raises(Exception):
            cfg.name = "changed"  # type: ignore[misc]


# ── Tiefe 2: TIER_MAP und get_model_config ──────────────────────────────────

class TestTierMap:
    """GIVEN die TIER_MAP ist konfiguriert"""

    def test_offline_tier_uses_e2b(self):
        """WHEN get_model_config(OFFLINE) aufgerufen wird
        THEN gibt es ein Config mit 'e2b' im Namen zurück"""
        from core.model_config import ModelTier, get_model_config
        cfg = get_model_config(ModelTier.OFFLINE)
        assert "e2b" in cfg.name

    def test_fast_tier_uses_12b(self):
        """WHEN get_model_config(FAST) aufgerufen wird
        THEN gibt es ein Config mit '12b' im Namen zurück"""
        from core.model_config import ModelTier, get_model_config
        cfg = get_model_config(ModelTier.FAST)
        assert "12b" in cfg.name

    def test_power_tier_uses_large_model(self):
        """WHEN get_model_config(POWER) aufgerufen wird
        THEN gibt es ein Config mit '26b' oder '31b' im Namen zurück"""
        from core.model_config import ModelTier, get_model_config
        cfg = get_model_config(ModelTier.POWER)
        assert any(size in cfg.name for size in ("26b", "27b", "31b"))

    def test_offline_tier_is_local(self):
        """WHEN get_model_config(OFFLINE) aufgerufen wird
        THEN ist der Host localhost"""
        from core.model_config import ModelTier, get_model_config
        cfg = get_model_config(ModelTier.OFFLINE)
        assert cfg.is_local is True

    def test_all_tiers_have_correct_tier_field(self):
        """WHEN jeder Tier abgerufen wird
        THEN stimmt das .tier-Feld mit dem angeforderten Tier überein"""
        from core.model_config import ModelTier, get_model_config
        for tier in ModelTier:
            cfg = get_model_config(tier)
            assert cfg.tier == tier


# ── Tiefe 3: Env-Variable Override ─────────────────────────────────────────

class TestEnvOverride:
    """GIVEN Env-Variablen überschreiben die Defaults"""

    def test_offline_model_env_override(self):
        """WHEN MIMI_OFFLINE_MODEL='gemma4:2b' gesetzt ist
        THEN gibt get_model_config(OFFLINE) dieses Modell zurück"""
        from core.model_config import ModelTier
        with patch.dict(os.environ, {"MIMI_OFFLINE_MODEL": "gemma4:2b"}):
            # Modul neu laden damit Env-Var greift
            import importlib, core.model_config as m
            importlib.reload(m)
            cfg = m.get_model_config(m.ModelTier.OFFLINE)
            assert cfg.name == "gemma4:2b"
            importlib.reload(m)  # zurücksetzen

    def test_fast_model_env_override(self):
        """WHEN MIMI_FAST_MODEL='gemma4:12b' gesetzt ist
        THEN gibt get_model_config(FAST) dieses Modell zurück"""
        from core.model_config import ModelTier
        with patch.dict(os.environ, {"MIMI_FAST_MODEL": "gemma4:12b"}):
            import importlib, core.model_config as m
            importlib.reload(m)
            cfg = m.get_model_config(m.ModelTier.FAST)
            assert cfg.name == "gemma4:12b"
            importlib.reload(m)

    def test_power_model_env_override(self):
        """WHEN MIMI_POWER_MODEL='gemma4:31b' gesetzt ist
        THEN gibt get_model_config(POWER) dieses Modell zurück"""
        with patch.dict(os.environ, {"MIMI_POWER_MODEL": "gemma4:31b"}):
            import importlib, core.model_config as m
            importlib.reload(m)
            cfg = m.get_model_config(m.ModelTier.POWER)
            assert cfg.name == "gemma4:31b"
            importlib.reload(m)

    def test_dgx_host_env_override(self):
        """WHEN MIMI_DGX_HOST='dgx.local:11434' gesetzt ist
        THEN hat get_model_config(POWER) diesen Host"""
        with patch.dict(os.environ, {"MIMI_DGX_HOST": "dgx.local:11434"}):
            import importlib, core.model_config as m
            importlib.reload(m)
            cfg = m.get_model_config(m.ModelTier.POWER)
            assert cfg.host == "dgx.local:11434"
            assert cfg.is_remote is True
            importlib.reload(m)

    def test_no_env_uses_safe_defaults(self):
        """WHEN keine Env-Variablen gesetzt sind
        THEN werden die sicheren Defaults genutzt (e2b, 12b, 26b)"""
        clean_env = {
            k: v for k, v in os.environ.items()
            if not k.startswith("MIMI_")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            import importlib, core.model_config as m
            importlib.reload(m)
            assert "e2b" in m.get_model_config(m.ModelTier.OFFLINE).name
            assert "12b" in m.get_model_config(m.ModelTier.FAST).name
            importlib.reload(m)

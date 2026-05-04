"""
◑ MiMi Nox – validate_hybrid_architecture.py

E2E-Validierung der Hybrid-Architektur (Phase 5).
Drei Szenarien — alle vollständig gemockt (kein echtes Netzwerk nötig).

Ausführen:
    pytest tests/validate_hybrid_architecture.py -v

Given / When / Then — dreifache Tiefenabdeckung:
  Szenario 1: Vollständig offline (OFFLINE-Tier)
  Szenario 2: Nur lokales Ollama (FAST-Tier)
  Szenario 3: DGX verfügbar (POWER-Tier)
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ────────────────────────────────────────────────────────────────

def make_probe(local: bool, remote: bool):
    from core.connectivity_probe import ConnectivityProbe
    probe = ConnectivityProbe.__new__(ConnectivityProbe)
    probe._dgx_host = "dgx.local:11434"
    probe._local_cache_result = None
    probe._local_cache_time = 0.0
    probe._remote_cache_result = None
    probe._remote_cache_time = 0.0
    probe.check_local = AsyncMock(return_value=local)
    probe.check_remote = AsyncMock(return_value=remote)
    return probe


# ── Szenario 1: Vollständig offline ────────────────────────────────────────

class TestScenario1FullOffline:
    """
    GIVEN kein lokales Ollama, kein DGX
    → System muss OFFLINE-Tier wählen
    """

    async def test_s1_router_selects_offline_tier(self):
        """WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelTier.OFFLINE zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_probe(local=False, remote=False))
        config = await router.resolve()
        assert config.tier == ModelTier.OFFLINE

    async def test_s1_offline_model_is_e2b(self):
        """WHEN OFFLINE-Tier aktiv ist
        THEN wird gemma4:e2b als Modell genutzt"""
        from core.model_router import ModelRouter
        router = ModelRouter(probe=make_probe(local=False, remote=False))
        config = await router.resolve()
        assert "e2b" in config.name

    async def test_s1_offline_uses_local_client(self):
        """WHEN OFFLINE-Tier aktiv ist
        THEN wird ein lokaler Ollama-Client erstellt (kein Remote)"""
        from core.model_router import ModelRouter
        from core.client_factory import OllamaClientFactory
        router = ModelRouter(probe=make_probe(local=False, remote=False))
        config = await router.resolve()
        assert config.is_local is True
        # Factory erstellt lokalen Client
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaClientFactory.build(config)
            kwargs = mock_cls.call_args.kwargs if mock_cls.call_args else {}
            assert "host" not in kwargs

    async def test_s1_force_tier_offline_works(self):
        """WHEN force_tier='offline' explizit gesetzt ist
        THEN wird OFFLINE-Tier genutzt (auch wenn lokal verfügbar)"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_probe(local=True, remote=True))
        config = await router.resolve(force_tier="offline")
        assert config.tier == ModelTier.OFFLINE


# ── Szenario 2: Nur lokales Ollama ─────────────────────────────────────────

class TestScenario2LocalOnly:
    """
    GIVEN lokales Ollama läuft, kein DGX
    → System muss FAST-Tier wählen
    """

    async def test_s2_router_selects_fast_tier(self):
        """WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelTier.FAST zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_probe(local=True, remote=False))
        config = await router.resolve()
        assert config.tier == ModelTier.FAST

    async def test_s2_fast_model_is_e4b(self):
        """WHEN FAST-Tier aktiv ist
        THEN wird gemma4:e4b als Modell genutzt"""
        from core.model_router import ModelRouter
        router = ModelRouter(probe=make_probe(local=True, remote=False))
        config = await router.resolve()
        assert "e4b" in config.name

    async def test_s2_fast_is_local(self):
        """WHEN FAST-Tier aktiv ist
        THEN läuft das Modell lokal (nicht DGX)"""
        from core.model_router import ModelRouter
        router = ModelRouter(probe=make_probe(local=True, remote=False))
        config = await router.resolve()
        assert config.is_local is True

    async def test_s2_dgx_not_online(self):
        """WHEN nur lokales Ollama verfügbar ist
        THEN ist dgx_online=False (Probe gibt False zurück)"""
        probe = make_probe(local=True, remote=False)
        dgx_status = await probe.check_remote()
        assert dgx_status is False


# ── Szenario 3: DGX verfügbar ───────────────────────────────────────────────

class TestScenario3DGXAvailable:
    """
    GIVEN lokales Ollama + DGX beide verfügbar
    → System muss POWER-Tier wählen
    """

    async def test_s3_router_selects_power_tier(self):
        """WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelTier.POWER zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_probe(local=True, remote=True))
        config = await router.resolve()
        assert config.tier == ModelTier.POWER

    async def test_s3_power_model_is_large(self):
        """WHEN POWER-Tier aktiv ist
        THEN wird ein großes Modell (26b/27b/31b) genutzt"""
        from core.model_router import ModelRouter
        router = ModelRouter(probe=make_probe(local=True, remote=True))
        config = await router.resolve()
        assert any(s in config.name for s in ("26b", "27b", "31b"))

    async def test_s3_power_uses_dgx_host_when_configured(self):
        """WHEN MIMI_DGX_HOST='dgx.local:11434' konfiguriert ist
        THEN hat POWER-Config diesen Host"""
        import importlib
        with patch.dict(os.environ, {"MIMI_DGX_HOST": "dgx.local:11434"}):
            import core.model_config as m
            importlib.reload(m)
            config = m.get_model_config(m.ModelTier.POWER)
            assert config.host == "dgx.local:11434"
            assert config.is_remote is True
            importlib.reload(m)

    async def test_s3_power_client_uses_remote(self):
        """WHEN POWER-Config remote ist
        THEN erstellt ClientFactory einen Remote-Client mit Host"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(
            name="gemma4:26b",
            tier=ModelTier.POWER,
            host="dgx.local:11434",
        )
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaClientFactory.build(cfg)
            mock_cls.assert_called_once_with(host="http://dgx.local:11434")

    async def test_s3_cache_upgrade_from_fast_to_power(self):
        """GIVEN Router startete mit FAST (kein DGX)
        WHEN DGX wird verfügbar + Cache invalidiert
        THEN gibt router.resolve() POWER zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        probe = make_probe(local=True, remote=False)
        router = ModelRouter(probe=probe)

        cfg1 = await router.resolve()
        assert cfg1.tier == ModelTier.FAST

        # DGX kommt online
        probe.check_remote = AsyncMock(return_value=True)
        router.invalidate_cache()

        cfg2 = await router.resolve()
        assert cfg2.tier == ModelTier.POWER

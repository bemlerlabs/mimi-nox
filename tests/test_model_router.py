"""
◑ MiMi Nox – test_model_router.py

TDD Tests für core/model_router.py

Given / When / Then — dreifache Tiefenabdeckung:
  Tiefe 1: resolve() — Tier-Entscheidung via Probe
  Tiefe 2: force_tier + MIMI_FORCE_TIER Env-Override
  Tiefe 3: Cache-Invalidierung + Singleton
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest


# ── Helper: Fake Probe ──────────────────────────────────────────────────────

def make_fake_probe(local: bool, remote: bool):
    """Erstellt eine Fake-Probe die keine Netzwerkaufrufe macht."""
    from core.connectivity_probe import ConnectivityProbe
    probe = ConnectivityProbe.__new__(ConnectivityProbe)
    probe._dgx_host = "dgx.local:11434" if remote else None
    probe._local_cache_result = None
    probe._local_cache_time = 0.0
    probe._remote_cache_result = None
    probe._remote_cache_time = 0.0
    probe.check_local = AsyncMock(return_value=local)
    probe.check_remote = AsyncMock(return_value=remote)
    return probe


# ── Tiefe 1: resolve() — automatische Tier-Wahl ─────────────────────────────

class TestResolveAutomatic:
    """GIVEN kein force_tier — Probe entscheidet"""

    async def test_resolve_offline_when_nothing_available(self):
        """GIVEN lokales Ollama und DGX nicht erreichbar
        WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelConfig mit tier=OFFLINE zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=False, remote=False))
        cfg = await router.resolve()
        assert cfg.tier == ModelTier.OFFLINE
        assert "e2b" in cfg.name

    async def test_resolve_fast_when_only_local(self):
        """GIVEN nur lokales Ollama erreichbar
        WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelConfig mit tier=FAST zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=True, remote=False))
        cfg = await router.resolve()
        assert cfg.tier == ModelTier.FAST
        assert "12b" in cfg.name

    async def test_resolve_power_when_dgx_available(self):
        """GIVEN lokales Ollama + DGX beide erreichbar
        WHEN router.resolve() aufgerufen wird
        THEN gibt es ModelConfig mit tier=POWER zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=True, remote=True))
        cfg = await router.resolve()
        assert cfg.tier == ModelTier.POWER

    async def test_resolve_returns_model_config_object(self):
        """WHEN router.resolve() aufgerufen wird
        THEN gibt es immer ein ModelConfig-Objekt zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelConfig
        router = ModelRouter(probe=make_fake_probe(local=True, remote=False))
        cfg = await router.resolve()
        assert isinstance(cfg, ModelConfig)


# ── Tiefe 2: force_tier Parameter + Env-Override ────────────────────────────

class TestForceTier:
    """GIVEN force_tier überschreibt die automatische Entscheidung"""

    async def test_force_offline_ignores_probe(self):
        """GIVEN force_tier='offline' obwohl DGX erreichbar wäre
        WHEN router.resolve(force_tier='offline') aufgerufen wird
        THEN gibt es IMMER ModelTier.OFFLINE zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=True, remote=True))
        cfg = await router.resolve(force_tier="offline")
        assert cfg.tier == ModelTier.OFFLINE

    async def test_force_power_ignores_probe(self):
        """GIVEN force_tier='power' obwohl nichts erreichbar wäre
        WHEN router.resolve(force_tier='power') aufgerufen wird
        THEN gibt es IMMER ModelTier.POWER zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=False, remote=False))
        cfg = await router.resolve(force_tier="power")
        assert cfg.tier == ModelTier.POWER

    async def test_force_fast_ignores_probe(self):
        """GIVEN force_tier='fast'
        WHEN router.resolve(force_tier='fast') aufgerufen wird
        THEN gibt es ModelTier.FAST zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        router = ModelRouter(probe=make_fake_probe(local=False, remote=False))
        cfg = await router.resolve(force_tier="fast")
        assert cfg.tier == ModelTier.FAST

    async def test_env_force_tier_overrides_automatically(self):
        """GIVEN MIMI_FORCE_TIER='power' Env-Var ist gesetzt
        WHEN router.resolve() ohne Argument aufgerufen wird
        THEN gibt es POWER zurück (egal was Probe sagt)"""
        from core.model_config import ModelTier
        with patch.dict(os.environ, {"MIMI_FORCE_TIER": "power"}):
            from core.model_router import ModelRouter
            import importlib, core.model_router as m
            importlib.reload(m)
            router = m.ModelRouter(probe=make_fake_probe(local=False, remote=False))
            cfg = await router.resolve()
            assert cfg.tier == ModelTier.POWER
            importlib.reload(m)


# ── Tiefe 3: Cache + Invalidierung + Singleton ──────────────────────────────

class TestRouterCache:
    """GIVEN der Router cached das Ergebnis für schnelle Folgeaufrufe"""

    async def test_resolve_caches_result(self):
        """GIVEN resolve() wurde einmal aufgerufen
        WHEN resolve() nochmal aufgerufen wird
        THEN wird die Probe NICHT nochmal aufgerufen (Cache-Treffer)"""
        from core.model_router import ModelRouter
        probe = make_fake_probe(local=True, remote=False)
        router = ModelRouter(probe=probe)
        await router.resolve()
        await router.resolve()
        # Probe sollte nur einmal aufgerufen worden sein
        assert probe.check_local.call_count == 1

    async def test_invalidate_cache_triggers_new_probe(self):
        """GIVEN Cache wurde invalidiert
        WHEN resolve() nochmal aufgerufen wird
        THEN wird die Probe erneut aufgerufen"""
        from core.model_router import ModelRouter
        probe = make_fake_probe(local=True, remote=False)
        router = ModelRouter(probe=probe)
        await router.resolve()
        router.invalidate_cache()
        await router.resolve()
        assert probe.check_local.call_count == 2

    async def test_tier_upgrade_after_cache_invalidation(self):
        """GIVEN erster resolve() gibt FAST zurück
        WHEN DGX wird verfügbar + invalidate_cache() + erneuter resolve()
        THEN gibt es POWER zurück"""
        from core.model_router import ModelRouter
        from core.model_config import ModelTier
        probe = make_fake_probe(local=True, remote=False)
        router = ModelRouter(probe=probe)

        cfg1 = await router.resolve()
        assert cfg1.tier == ModelTier.FAST

        # DGX wird verfügbar
        probe.check_remote = AsyncMock(return_value=True)
        router.invalidate_cache()

        cfg2 = await router.resolve()
        assert cfg2.tier == ModelTier.POWER

    def test_get_router_returns_singleton(self):
        """GIVEN get_router() wird zweimal aufgerufen
        WHEN das Modul nicht neu geladen wurde
        THEN ist es dasselbe Objekt (Singleton)"""
        import importlib, core.model_router as m
        importlib.reload(m)  # frischen Singleton starten
        router1 = m.get_router()
        router2 = m.get_router()
        assert router1 is router2
        importlib.reload(m)

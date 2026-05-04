"""
◑ MiMi Nox – test_connectivity_probe.py

TDD Tests für core/connectivity_probe.py

Given / When / Then — dreifache Tiefenabdeckung:
  Tiefe 1: check_local() — lokaler Ollama-Check
  Tiefe 2: check_remote() — DGX-Check mit Timeout
  Tiefe 3: best_available_tier() — automatische Tier-Entscheidung + Cache
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Tiefe 1: check_local() ──────────────────────────────────────────────────

class TestCheckLocal:
    """GIVEN check_local() prüft den lokalen Ollama-Server"""

    async def test_returns_true_when_ollama_reachable(self):
        """WHEN lokales Ollama antwortet
        THEN gibt check_local() True zurück"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()
        list_response = MagicMock()
        list_response.models = []
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list = AsyncMock(return_value=list_response)
            mock_cls.return_value = instance
            result = await probe.check_local()
        assert result is True

    async def test_returns_false_when_connection_refused(self):
        """WHEN Ollama nicht läuft (ConnectionRefusedError)
        THEN gibt check_local() False zurück — kein Exception-Crash"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list.side_effect = ConnectionRefusedError("refused")
            mock_cls.return_value = instance
            result = await probe.check_local()
        assert result is False

    async def test_returns_false_on_timeout(self):
        """WHEN Ollama nicht antwortet (Timeout)
        THEN gibt check_local() False zurück"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list.side_effect = asyncio.TimeoutError()
            mock_cls.return_value = instance
            result = await probe.check_local()
        assert result is False

    async def test_returns_false_on_any_exception(self):
        """WHEN ein unbekannter Fehler auftritt
        THEN gibt check_local() False zurück (defensive)"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list.side_effect = RuntimeError("unexpected!")
            mock_cls.return_value = instance
            result = await probe.check_local()
        assert result is False


# ── Tiefe 2: check_remote() ─────────────────────────────────────────────────

class TestCheckRemote:
    """GIVEN check_remote() prüft den DGX Remote-Server"""

    async def test_returns_true_when_dgx_reachable(self):
        """WHEN DGX-Host erreichbar ist
        THEN gibt check_remote() True zurück"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe(dgx_host="192.168.1.50:11434")
        list_response = MagicMock()
        list_response.models = []
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list = AsyncMock(return_value=list_response)
            mock_cls.return_value = instance
            result = await probe.check_remote()
        assert result is True

    async def test_returns_false_when_dgx_not_reachable(self):
        """WHEN DGX-Host nicht erreichbar (Timeout)
        THEN gibt check_remote() False zurück"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe(dgx_host="dgx.local:11434")
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list.side_effect = asyncio.TimeoutError()
            mock_cls.return_value = instance
            result = await probe.check_remote()
        assert result is False

    async def test_returns_false_when_no_dgx_host_configured(self):
        """WHEN kein DGX-Host konfiguriert ist
        THEN gibt check_remote() sofort False zurück (kein Netzwerkaufruf)"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe(dgx_host=None)
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            result = await probe.check_remote()
            mock_cls.assert_not_called()
        assert result is False

    async def test_uses_explicit_host_parameter(self):
        """WHEN host='10.0.0.1:11434' direkt übergeben wird
        THEN wird dieser Host anstelle des konfigurierten DGX-Hosts genutzt"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe(dgx_host="default.host:11434")
        list_response = MagicMock()
        list_response.models = []
        captured_host = []
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list = AsyncMock(return_value=list_response)
            mock_cls.return_value = instance
            def capture_host(**kwargs):
                captured_host.append(kwargs.get("host", ""))
                return instance
            mock_cls.side_effect = capture_host
            await probe.check_remote(host="10.0.0.1:11434")
        assert any("10.0.0.1:11434" in h for h in captured_host)


# ── Tiefe 3: best_available_tier() ─────────────────────────────────────────

class TestBestAvailableTier:
    """GIVEN best_available_tier() entscheidet automatisch den besten Tier"""

    async def test_offline_when_nothing_available(self):
        """GIVEN lokales Ollama + DGX beide nicht erreichbar
        WHEN best_available_tier() aufgerufen wird
        THEN gibt es ModelTier.OFFLINE zurück"""
        from core.connectivity_probe import ConnectivityProbe
        from core.model_config import ModelTier
        probe = ConnectivityProbe()
        with patch.object(probe, "check_local", return_value=False), \
             patch.object(probe, "check_remote", return_value=False):
            tier = await probe.best_available_tier()
        assert tier == ModelTier.OFFLINE

    async def test_fast_when_only_local_available(self):
        """GIVEN nur lokales Ollama erreichbar
        WHEN best_available_tier() aufgerufen wird
        THEN gibt es ModelTier.FAST zurück"""
        from core.connectivity_probe import ConnectivityProbe
        from core.model_config import ModelTier
        probe = ConnectivityProbe()
        with patch.object(probe, "check_local", return_value=True), \
             patch.object(probe, "check_remote", return_value=False):
            tier = await probe.best_available_tier()
        assert tier == ModelTier.FAST

    async def test_power_when_both_available(self):
        """GIVEN lokales Ollama + DGX beide erreichbar
        WHEN best_available_tier() aufgerufen wird
        THEN gibt es ModelTier.POWER zurück"""
        from core.connectivity_probe import ConnectivityProbe
        from core.model_config import ModelTier
        probe = ConnectivityProbe(dgx_host="dgx.local:11434")
        with patch.object(probe, "check_local", return_value=True), \
             patch.object(probe, "check_remote", return_value=True):
            tier = await probe.best_available_tier()
        assert tier == ModelTier.POWER

    async def test_ttl_cache_prevents_double_network_call(self):
        """GIVEN check_local() wurde bereits aufgerufen
        WHEN check_local() innerhalb des TTL-Fensters nochmal aufgerufen wird
        THEN wird kein zweiter Netzwerkaufruf gemacht"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()
        call_count = 0

        async def fake_list():
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.models = []
            return resp

        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list = fake_list
            mock_cls.return_value = instance
            await probe.check_local()
            await probe.check_local()  # zweiter Aufruf — sollte Cache nutzen

        assert call_count == 1, "Cache hat nicht funktioniert — 2 Netzwerkaufrufe!"

    async def test_cache_invalidated_after_ttl(self):
        """GIVEN TTL-Cache ist abgelaufen (simuliert)
        WHEN check_local() nochmal aufgerufen wird
        THEN wird ein neuer Netzwerkaufruf gemacht"""
        from core.connectivity_probe import ConnectivityProbe
        probe = ConnectivityProbe()

        # Cache manuell als abgelaufen markieren
        probe._local_cache_result = True
        probe._local_cache_time = 0.0  # Epoch = immer abgelaufen

        call_count = 0
        resp = MagicMock()
        resp.models = []
        with patch("core.connectivity_probe.ollama.AsyncClient") as mock_cls:
            instance = AsyncMock()
            instance.list = AsyncMock(return_value=resp)
            mock_cls.return_value = instance
            await probe.check_local()
            call_count = instance.list.call_count

        assert call_count == 1, "Nach TTL-Ablauf sollte neu geprüft werden"

"""
◑ MiMi Nox – test_client_factory.py

TDD Tests für core/client_factory.py

Given / When / Then — dreifache Tiefenabdeckung:
  Tiefe 1: build(config) — richtiger Client für lokale Config
  Tiefe 2: build(config) — richtiger Client für Remote-Config
  Tiefe 3: build_for_tier() + Integration in chat_with_tools
"""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


# ── Tiefe 1: Lokale Config → lokaler Client ─────────────────────────────────

class TestBuildLocal:
    """GIVEN eine lokale ModelConfig (localhost:11434)"""

    def test_local_config_creates_default_client(self):
        """WHEN factory.build(local_config) aufgerufen wird
        THEN wird ollama.AsyncClient() OHNE host-Argument erstellt"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)

        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaClientFactory.build(cfg)
            # Muss ohne 'host' keyword argument aufgerufen worden sein
            call_kwargs = mock_cls.call_args
            assert call_kwargs is None or "host" not in (call_kwargs.kwargs or {})

    def test_local_config_returns_client_instance(self):
        """WHEN factory.build(local_config) aufgerufen wird
        THEN gibt es ein ollama.AsyncClient Objekt zurück"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:12b", tier=ModelTier.FAST)

        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            fake_client = MagicMock()
            mock_cls.return_value = fake_client
            result = OllamaClientFactory.build(cfg)
            assert result is fake_client

    def test_offline_tier_creates_local_client(self):
        """WHEN build() mit OFFLINE-Config aufgerufen wird
        THEN wird kein Remote-Client erstellt"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(name="gemma4:e2b", tier=ModelTier.OFFLINE)

        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaClientFactory.build(cfg)
            kwargs = mock_cls.call_args.kwargs if mock_cls.call_args else {}
            assert "host" not in kwargs


# ── Tiefe 2: Remote Config → DGX Client ────────────────────────────────────

class TestBuildRemote:
    """GIVEN eine Remote-ModelConfig (DGX Host)"""

    def test_remote_config_creates_client_with_host(self):
        """WHEN factory.build(remote_config) aufgerufen wird
        THEN wird ollama.AsyncClient(host=...) MIT Host aufgerufen"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelConfig, ModelTier
        cfg = ModelConfig(
            name="gemma4:26b",
            tier=ModelTier.POWER,
            host="192.168.1.50:11434",
        )
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            OllamaClientFactory.build(cfg)
            mock_cls.assert_called_once_with(host="http://192.168.1.50:11434")

    def test_remote_host_uses_base_url(self):
        """WHEN host='dgx.local:11434'
        THEN wird 'http://dgx.local:11434' als host-Parameter übergeben"""
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
            call_host = mock_cls.call_args.kwargs.get("host", "")
            assert call_host == "http://dgx.local:11434"


# ── Tiefe 3: build_for_tier() Convenience ──────────────────────────────────

class TestBuildForTier:
    """GIVEN build_for_tier() als Shortcut"""

    def test_build_for_tier_returns_tuple(self):
        """WHEN build_for_tier(FAST) aufgerufen wird
        THEN gibt es ein (client, config) Tuple zurück"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelTier
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            result = OllamaClientFactory.build_for_tier(ModelTier.FAST)
            assert isinstance(result, tuple)
            assert len(result) == 2

    def test_build_for_tier_config_matches_tier(self):
        """WHEN build_for_tier(OFFLINE) aufgerufen wird
        THEN hat die zurückgegebene Config tier=OFFLINE"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelTier
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            _client, config = OllamaClientFactory.build_for_tier(ModelTier.OFFLINE)
            assert config.tier == ModelTier.OFFLINE
            assert "e2b" in config.name

    def test_build_for_power_tier_uses_power_config(self):
        """WHEN build_for_tier(POWER) aufgerufen wird
        THEN hat die zurückgegebene Config tier=POWER"""
        from core.client_factory import OllamaClientFactory
        from core.model_config import ModelTier
        with patch("core.client_factory.ollama.AsyncClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            _client, config = OllamaClientFactory.build_for_tier(ModelTier.POWER)
            assert config.tier == ModelTier.POWER

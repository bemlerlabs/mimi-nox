"""
◑ MiMi Nox – OllamaClientFactory
core/client_factory.py

Baut den richtigen ollama.AsyncClient für eine ModelConfig:
  - Lokale Config (localhost)  → ollama.AsyncClient()
  - Remote Config (DGX-Host)  → ollama.AsyncClient(host="http://...")

Trennt die Client-Erstellung sauber von der Business-Logik.
Alle anderen Module (chat.py, swarm_v2.py, etc.) nutzen diese Factory
statt ollama.AsyncClient() direkt aufzurufen.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import ollama

from core.model_config import ModelConfig, ModelTier, get_model_config


class OllamaClientFactory:
    """
    Statische Factory für ollama.AsyncClient-Instanzen.

    Beispiel:
        config = get_model_config(ModelTier.POWER)
        client = OllamaClientFactory.build(config)
        # → AsyncClient(host="http://dgx.local:11434")
    """

    @staticmethod
    def build(config: ModelConfig) -> ollama.AsyncClient:
        """
        Erstellt einen AsyncClient passend zur ModelConfig.

        Args:
            config: ModelConfig mit host und is_remote

        Returns:
            ollama.AsyncClient (lokal oder remote konfiguriert)
        """
        if config.is_remote:
            return ollama.AsyncClient(host=config.base_url)
        return ollama.AsyncClient()

    @staticmethod
    def build_for_tier(tier: ModelTier) -> tuple[ollama.AsyncClient, ModelConfig]:
        """
        Shortcut: gibt (client, config) für einen Tier zurück.

        Args:
            tier: ModelTier.OFFLINE | FAST | POWER

        Returns:
            Tuple aus (ollama.AsyncClient, ModelConfig)
        """
        config = get_model_config(tier)
        client = OllamaClientFactory.build(config)
        return client, config

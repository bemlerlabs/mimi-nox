"""
◑ MiMi Nox – Connectivity Probe
core/connectivity_probe.py

Prüft in max. PROBE_TIMEOUT Sekunden ob lokales Ollama und/oder
der DGX Remote-Server erreichbar sind.

Enthält einen TTL-Cache (CACHE_TTL Sekunden) damit schnelle Aufrufe
hintereinander keinen Netzwerk-Overhead produzieren.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import asyncio
import time

import ollama

from core.model_config import ModelTier

PROBE_TIMEOUT: float = 2.0   # Sekunden bis Timeout
CACHE_TTL:     float = 10.0  # Sekunden Gültigkeit des Cache


class ConnectivityProbe:
    """
    Prüft die Erreichbarkeit von lokalem Ollama und DGX Remote-Server.

    Beispiel:
        probe = ConnectivityProbe(dgx_host="192.168.1.50:11434")
        tier  = await probe.best_available_tier()
        # → ModelTier.POWER wenn DGX erreichbar
    """

    def __init__(self, dgx_host: str | None = None) -> None:
        self._dgx_host = dgx_host

        # TTL-Cache für check_local
        self._local_cache_result: bool | None = None
        self._local_cache_time:   float       = 0.0

        # TTL-Cache für check_remote
        self._remote_cache_result: bool | None = None
        self._remote_cache_time:   float       = 0.0

    # ── Lokaler Ollama ──────────────────────────────────────────────────────

    async def check_local(self) -> bool:
        """
        Prüft ob der lokale Ollama-Server erreichbar ist.
        Ergebnis wird für CACHE_TTL Sekunden gecacht.

        Returns:
            True wenn erreichbar, False bei jedem Fehler.
        """
        now = time.monotonic()
        if (
            self._local_cache_result is not None
            and (now - self._local_cache_time) < CACHE_TTL
        ):
            return self._local_cache_result

        result = await self._probe_host(host=None)  # None = localhost default
        self._local_cache_result = result
        self._local_cache_time   = now
        return result

    # ── Remote / DGX ───────────────────────────────────────────────────────

    async def check_remote(self, host: str | None = None) -> bool:
        """
        Prüft ob ein Remote-Ollama-Server (z.B. DGX) erreichbar ist.
        Nutzt host-Parameter oder den konfigurierten DGX-Host.
        Ergebnis wird für CACHE_TTL Sekunden gecacht.

        Args:
            host: Optionaler Override, z.B. "10.0.0.1:11434"

        Returns:
            True wenn erreichbar, False wenn nicht konfiguriert oder Fehler.
        """
        effective_host = host or self._dgx_host
        if not effective_host:
            return False  # Kein DGX konfiguriert → sofort False

        now = time.monotonic()
        # Cache nur für den konfigurierten Standard-Host nutzen
        if host is None:
            if (
                self._remote_cache_result is not None
                and (now - self._remote_cache_time) < CACHE_TTL
            ):
                return self._remote_cache_result

        result = await self._probe_host(host=effective_host)

        if host is None:
            self._remote_cache_result = result
            self._remote_cache_time   = now

        return result

    # ── Tier-Entscheidung ───────────────────────────────────────────────────

    async def best_available_tier(self) -> ModelTier:
        """
        Entscheidet automatisch den besten verfügbaren Tier:
          - POWER  wenn DGX + lokal erreichbar
          - FAST   wenn nur lokal erreichbar
          - OFFLINE wenn nichts erreichbar

        Returns:
            ModelTier: bester verfügbarer Tier
        """
        local_ok  = await self.check_local()
        remote_ok = await self.check_remote()

        if local_ok and remote_ok:
            return ModelTier.POWER
        if local_ok:
            return ModelTier.FAST
        return ModelTier.OFFLINE

    # ── Interner Helper ─────────────────────────────────────────────────────

    async def _probe_host(self, host: str | None) -> bool:
        """
        Führt den eigentlichen Ollama .list() Call durch.

        Args:
            host: None für localhost, ansonsten "ip:port"

        Returns:
            True wenn erfolgreich, False bei jedem Fehler.
        """
        try:
            if host:
                client = ollama.AsyncClient(host=f"http://{host}")
            else:
                client = ollama.AsyncClient()

            await asyncio.wait_for(client.list(), timeout=PROBE_TIMEOUT)
            return True
        except Exception:
            return False

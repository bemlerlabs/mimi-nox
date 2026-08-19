"""
◑ MiMi Nox – Telegram-Channel Pairing-Allowlist (Sprint 3 G1).

On-Device-Gateway (kein Cloud-Relay): der Bot antwortet NUR auf User-IDs in
einer STATISCHEN Allowlist. Default-Empty = antwortet auf niemanden. Kein
Chat-Kommando darf die Allowlist ändern. Persistiert 0600 (Dir 0700, atomar).

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

PAIRING_FILE = "tg_pairing.json"
ALLOWLIST_ENV = "MIMI_NOX_TG_ALLOWLIST"
_CONFIG_DIR_ENV = "MIMI_NOX_CONFIG_DIR"


def _config_dir() -> Path:
    """Kanonische Config-Dir (Default ~/.mimi-nox), env-override testbar."""
    return Path(os.environ.get(_CONFIG_DIR_ENV, str(Path.home() / ".mimi-nox")))


def default_pairing_path() -> Path:
    """Pfad der Allowlist-Datei unter der Config-Dir."""
    return _config_dir() / PAIRING_FILE


def _norm(user_id: str | int) -> str:
    """Normalisiert eine User-ID auf einen trimmten String-Key."""
    return str(user_id).strip()


@dataclass
class TGGatewayConfig:
    """Pairing-Konfiguration des Telegram-Gateways.

    `allowlist` ist die STATISCHE Liste erlaubter User-IDs (Strings).
    `is_allowed` führt einen exakten, normalisierten String-Match aus —
    kein Prefix-/Teilstring-Match, kein dynamisches Pairing.
    """

    bot_token: str
    allowlist: list[str]
    config_dir: str | None = None

    def _effective_allowlist(self) -> list[str]:
        """Env-Override (CSV) hat Vorrang; sonst die statische Liste.

        Der Env-Weg ist ein statischer Override für Betrieb/Tests, kein
        Chat-Pfad: er wird einmalig beim Konfig-Aufbau gelesen.
        """
        raw_env = os.environ.get(ALLOWLIST_ENV, "").strip()
        if raw_env:
            return [p.strip() for p in raw_env.split(",") if p.strip()]
        return [_norm(u) for u in self.allowlist if _norm(u)]

    def is_allowed(self, user_id: str | int) -> bool:
        """True, wenn die User-ID in der statischen Allowlist steht."""
        return _norm(user_id) in self._effective_allowlist()


def load_pairing(path: Path | None = None) -> list[str]:
    """Lädt die Allowlist. Fehlend/beschädigt/nicht-Liste → [] (nie crashen)."""
    p = path or default_pairing_path()
    try:
        if not p.exists():
            return []
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return [str(x).strip() for x in data if str(x).strip()]
    except Exception:
        return []


def save_pairing(allowlist: list[str], path: Path | None = None) -> Path:
    """Persistiert die Allowlist atomar (0700-Dir + 0600-Datei). Deduped."""
    p = path or default_pairing_path()
    # Dedup + Trim, Reihenfolge stabil (erste Sicht gewinnt).
    seen: list[str] = []
    for u in allowlist:
        k = _norm(u)
        if k and k not in seen:
            seen.append(k)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.parent.chmod(0o700)
    except OSError:
        pass
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return p


def clear_pairing(path: Path | None = None) -> None:
    """Entfernt die Allowlist-Datei (Reset)."""
    p = path or default_pairing_path()
    try:
        if p.exists():
            p.unlink()
    except OSError:
        pass


__all__ = [
    "TGGatewayConfig",
    "default_pairing_path",
    "load_pairing",
    "save_pairing",
    "clear_pairing",
    "ALLOWLIST_ENV",
    "PAIRING_FILE",
]

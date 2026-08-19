"""
◑ MiMi Nox – Telegram-Bot-Token via Keyring/0600 (Sprint 3 G1).

SPECK-DoD (Ziffer 3, 5): Token ist NIEMALS im Log oder in einer committen
Konfig-Datei. Speicherung: Env-Override > Keyring (optional) > 0600-Datei
unter der Config-Dir (Dir 0700, Datei 0600, atomar). `redact_token` maskiert
das Token in jeder Log-/Fehler-String.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import os
from pathlib import Path

TOKEN_FILE = "tg_token"
_TOKEN_ENV = "MIMI_NOX_TG_TOKEN"
_TOKEN_FILE_ENV = "MIMI_NOX_TOKEN_FILE"
_CONFIG_DIR_ENV = "MIMI_NOX_CONFIG_DIR"

_KEYRING_SERVICE = "mimi-nox"
_KEYRING_ACCOUNT = "telegram-bot-token"


def _config_dir() -> Path:
    return Path(os.environ.get(_CONFIG_DIR_ENV, str(Path.home() / ".mimi-nox")))


def default_token_path() -> Path:
    """Pfad der Token-Datei: env-override oder unter der Config-Dir."""
    override = os.environ.get(_TOKEN_FILE_ENV, "").strip()
    if override:
        return Path(override)
    return _config_dir() / TOKEN_FILE


def _keyring_get() -> str:
    """Optioneller Keyring-Read (Keychain auf macOS). Fehlt → ''."""
    try:
        import keyring  # type: ignore
    except Exception:
        return ""
    try:
        return keyring.get_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT) or ""
    except Exception:
        return ""


def _keyring_set(token: str) -> bool:
    """Optioneller Keyring-Write. Fehlt/schlägt fehl → False (kein Hard-Fail)."""
    try:
        import keyring  # type: ignore
    except Exception:
        return False
    try:
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT, token)
        return True
    except Exception:
        return False


def resolve_token() -> str:
    """Löst den Bot-Token auf: Env > Keyring > 0600-Datei. Fehlend → ''."""
    env = os.environ.get(_TOKEN_ENV, "").strip()
    if env:
        return env
    kr = _keyring_get().strip()
    if kr:
        return kr
    p = default_token_path()
    try:
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return ""


def save_token(token: str, path: str | None = None) -> bool:
    """Persistiert den Token atomar (Keyring bevorzugt, sonst 0600-Datei)."""
    token = (token or "").strip()
    if not token:
        return False
    # Keyring zuerst (System-Zustand, nie eine Datei im Repo).
    if _keyring_set(token):
        return True
    p = Path(path) if path else default_token_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        p.parent.chmod(0o700)
    except OSError:
        pass
    tmp = p.with_suffix(p.suffix or ".tmp")
    tmp.write_text(token, encoding="utf-8")
    tmp.replace(p)
    try:
        p.chmod(0o600)
    except OSError:
        pass
    return True


def clear_token() -> None:
    """Entfernt den Token aus Datei + Keyring (best effort)."""
    try:
        p = default_token_path()
        if p.exists():
            p.unlink()
    except OSError:
        pass
    try:
        import keyring  # type: ignore
        keyring.delete_password(_KEYRING_SERVICE, _KEYRING_ACCOUNT)
    except Exception:
        pass


def _current_token() -> str:
    return resolve_token()


def redact_token(text: str) -> str:
    """Ersetzt ein bekanntes Token in `text` durch einen Mask-Platzhalter.

    Ohne bekanntes Token bleibt `text` unverändert (keine falsche Maskierung).
    Der Platzhalter ist nicht leer und enthält nicht das rohe Token.
    """
    tok = _current_token()
    if not tok:
        return text
    masked = "TOKEN_REDACTED:" + tok[:3] + "…"
    return text.replace(tok, masked)


__all__ = [
    "resolve_token",
    "save_token",
    "clear_token",
    "redact_token",
    "default_token_path",
    "TOKEN_FILE",
]

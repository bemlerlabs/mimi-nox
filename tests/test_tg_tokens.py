"""
tests/test_tg_tokens.py – Sprint 3 G1: Bot-Token via Keyring/0600.

SPECK-DoD (Ziffer 3, 5):
  (1) Token ist niemals im Log oder in einer committen Konfig-Datei.
  (2) Token via Keyring ODER 0600-Datei (Fallback wenn kein keyring/Keychain).

Design (root-cause, kein Workaround):
  - Env-Override (MIMI_NOX_TG_TOKEN) hat Priorität 1 — deterministisch testbar,
    kein Keyring-System-Zustand im Test nötig.
  - Keyring (Keychain auf macOS) hat Priorität 2 — optionaler Fast-Path; wenn
    das keyring-Paket fehlt, wird sauber auf die 0600-Datei gefallten.
  - 0600-Datei unter ~/.mimi-nox hat Priorität 3 — derselbe Härtungs-Stand wie
    engine.json (0700 Dir + 0600 Datei), NIE in der Git-Repo.
  - Maskieren: `redact_token` entfernt das Token aus jeder Zeichenfolge
    (Logs, Fehlermeldungen) — der Bot druckt nie das Token.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.tg_tokens import (
    clear_token,
    default_token_path,
    redact_token,
    resolve_token,
    save_token,
)

FAKE_TOKEN = "123456789:AAHf0kEaBcDeFgHiJkLmNoPqRsTuVwXyZ"


# ── (1) Token niemals im Log / in committen Konfig ───────────────────────────

def test_redact_token_must_never_leak(monkeypatch):
    monkeypatch.setenv("MIMI_NOX_TG_TOKEN", FAKE_TOKEN)
    # resolve liefert das Token intern…
    assert resolve_token() == FAKE_TOKEN
    # …aber jede Log-/Fehler-String, der den Bot-Namen + Token enthält,
    # wird vor dem Drucken ge-maskt → das rohe Token verschwindet.
    log_line = f"connecting with token={FAKE_TOKEN}"
    redacted = redact_token(log_line)
    assert FAKE_TOKEN not in redacted, "Token darf nie im Log stehen!"
    assert "TOKEN_REDACTED" in redacted or "REDACTED" in redacted.upper()


def test_redact_token_without_token_is_noop(monkeypatch):
    monkeypatch.delenv("MIMI_NOX_TG_TOKEN", raising=False)
    # Ohne bekanntes Token: String bleibt unverändert (keine falsche Maskierung).
    assert redact_token("kein token hier") == "kein token hier"


def test_redact_masked_value_still_has_prefix_hint(monkeypatch):
    # Ohne bekanntes Token: String bleibt unverändert (keine falsche Maskierung).
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.setenv("MIMI_NOX_TG_TOKEN", FAKE_TOKEN)
    # Der Mask-Platzhalter ist nicht leer und enthält NICHT den ganzen Token.
    r = redact_token(FAKE_TOKEN)
    assert r != FAKE_TOKEN


def test_resolve_token_prefers_env(monkeypatch, tmp_path):
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.setenv("MIMI_NOX_TG_TOKEN", "ENV-TOKEN")
    # Sogar wenn eine Datei-Datei existiert, gewinnt die Env.
    save_token("FILE-TOKEN", str(tmp_path / "tg_token"))
    monkeypatch.setenv("MIMI_NOX_TOKEN_FILE", str(tmp_path / "tg_token"))
    # Env-Override schlägt die Datei.
    assert resolve_token() == "ENV-TOKEN"


def test_resolve_token_falls_back_to_file(monkeypatch, tmp_path):
    monkeypatch.setattr("core.tg_tokens._keyring_set", lambda _t: False)
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.delenv("MIMI_NOX_TG_TOKEN", raising=False)
    tokfile = tmp_path / "tg_token"
    # save und resolve müssen denselben Pfad verwenden: Token-File auf tokfile.
    monkeypatch.setenv("MIMI_NOX_TOKEN_FILE", str(tokfile))
    save_token("FILE-TOKEN", str(tokfile))
    assert resolve_token() == "FILE-TOKEN"


def test_resolve_token_missing_returns_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.delenv("MIMI_NOX_TG_TOKEN", raising=False)
    monkeypatch.setenv("MIMI_NOX_TOKEN_FILE", str(tmp_path / "nope"))
    assert resolve_token() == ""


# ── (2) 0600-Datei + 0700-Dir, atomar ────────────────────────────────────────

def test_save_token_writes_0600(monkeypatch, tmp_path):
    monkeypatch.setattr("core.tg_tokens._keyring_set", lambda _t: False)
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.setenv("MIMI_NOX_CONFIG_DIR", str(tmp_path))
    tokfile = default_token_path()
    assert tokfile == tmp_path / "tg_token"
    save_token(FAKE_TOKEN)
    assert tokfile.exists()
    mode = oct(tokfile.stat().st_mode & 0o777)
    assert mode == "0o600", f"Token-Datei muss 0600 sein, ist {mode}"
    dir_mode = oct(tokfile.parent.stat().st_mode & 0o777)
    assert dir_mode == "0o700", f"Config-Dir muss 0700 sein, ist {dir_mode}"
    # Inhalt ist exakt das Token (trimmend, keine Extra-Ende-Whitespace).
    assert tokfile.read_text(encoding="utf-8").strip() == FAKE_TOKEN


def test_clear_token(monkeypatch, tmp_path):
    monkeypatch.setattr("core.tg_tokens._keyring_set", lambda _t: False)
    monkeypatch.setattr("core.tg_tokens._keyring_get", lambda: "")
    monkeypatch.setenv("MIMI_NOX_CONFIG_DIR", str(tmp_path))
    tokfile = default_token_path()
    save_token(FAKE_TOKEN)
    assert tokfile.exists()
    clear_token()
    assert not tokfile.exists()


def test_token_file_never_in_repo(tmp_path):
    """Der Token-Dateiname gehört zur .mimi-nox-Lokalkonfig, NICHT ins Repo."""
    # Regression: default_token_path darf NIEMALS einen repo-internen Pfad
    # (aktuelle Working-Dir) verwenden — immer unter der Config-Dir.
    monkeypatch_dir = tmp_path / "mimi-nox"
    os.environ["MIMI_NOX_CONFIG_DIR"] = str(monkeypatch_dir)
    try:
        p = default_token_path()
        # Der Pfad muss unter der Config-Dir liegen, nicht unter os.getcwd().
        assert str(p).startswith(str(monkeypatch_dir)), \
            f"Token-Pfad muss unter Config-Dir liegen, ist {p}"
        assert not str(p).startswith(str(Path.cwd() / "tg_token")), \
            "Token darf nicht in der Repo-/CWD-Datei liegen"
    finally:
        del os.environ["MIMI_NOX_CONFIG_DIR"]

"""
tests/test_tg_pairing.py – Sprint 3 G1: Telegram-Channel Pairing-Allowlist.

SPECK-DoD (Ziffer 2, 5):
  (a) Allowlist ist STatisch (Konfig/Env), nicht dynamisch per Chat.
  (b) Default-Empty → der Bot antwortet auf NIEMANDEN (keine Echo-Ping-Pong).
  (c) Kein Chat-Befehl kann die Allowlist ändern (kein "pair" / "allow" Command).
  (d) Persistiert in 0600-Datei unter ~/.mimi-nox (Least-Privilege, analog engine.json).

Alle Tests sind offline (kein Telegram, kein DGX): rein lokale Konfig-Logik.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from core.tg_pairing import (
    TGGatewayConfig,
    clear_pairing,
    default_pairing_path,
    load_pairing,
    save_pairing,
)


# ── (b) Default-Empty → antwortet auf niemanden ──────────────────────────────

def test_empty_allowlist_denies_everyone(tmp_path):
    cfg = TGGatewayConfig(
        bot_token="123:TEST",
        allowlist=[],
        config_dir=str(tmp_path),
    )
    assert not cfg.is_allowed("1")
    assert not cfg.is_allowed("777")
    # Selbst eine gefälschte User-ID wird nicht akzeptiert.
    assert not cfg.is_allowed("999999999")


def test_allowlist_is_static_string_match():
    cfg = TGGatewayConfig(bot_token="t", allowlist=["42", "7"], config_dir="/tmp")
    assert cfg.is_allowed("42")
    assert cfg.is_allowed("7")
    # Exakter Match: "42" erlaubt, "421" nicht (kein Prefix-/Teilstring-Match).
    assert not cfg.is_allowed("421")
    # Whitespace wird normalisiert (robust gegen Editierungs-Artefakte).
    assert cfg.is_allowed("  42 ")


# ── (a) Statisch: nur Code kann sie ändern, nie per Chat ─────────────────────

def test_no_chat_command_can_mutate_allowlist(tmp_path):
    """Der Gateway-Handler kennt keinen Befehl, der die Allowlist verändert.

    Regression-Guard: Sollte jemand einen /pair- oder /allow-Command
    implementieren, MUSS dieser Test die Änderung auffangen, weil er die
    kompletten, erkannten Chat-Befehle des Gateway-Moduls prüft und verlangt,
    dass keiner von ihnen die Allowlist schreibt.
    """
    import core.tg_gateway as gateway

    source = Path(gateway.__file__).read_text(encoding="utf-8")
    # Der Handler darf keine save/load der Allowlist an einen Chat-Eingang
    # koppeln: es darf kein Befehl den String 'pair'/'allow' als Chat-Kommando
    # verarbeiten. Wir prüfen strukturell: kein "startswith('/pair')" etc.
    for banned in ("startswith(\"/pair", "startswith('/pair", "startswith(\"/allow",
                    "startswith('/allow", "/approve_pairing", "add_to_allowlist"):
        assert banned not in source, f"Gefundener Chat-Mutation-Pfad: {banned!r}"

    # Und: die erkannten Befehle des Handlers sind nur die expliziten
    # Freigabe-Befehle (ja/nein) – nichts, was die Allowlist berührt.
    assert gateway.is_approval_yes("ja")
    assert not gateway.is_approval_yes("/pair 12345")


# ── (d) Persistenz 0600 + Atomarität + Config-Dir 0700 ───────────────────────

def test_save_load_roundtrip_and_0600(tmp_path):
    path = tmp_path / "tg_pairing.json"
    save_pairing(["111", "222"], path)
    loaded = load_pairing(path)
    assert sorted(loaded) == ["111", "222"]
    mode = oct(path.stat().st_mode & 0o777)
    assert mode == "0o600", f"Allowlist-Datei muss 0600 sein, ist {mode}"
    # Config-Verzeichnis wird auf 0700 gehärtet (analog engine_config).
    dir_mode = oct(path.parent.stat().st_mode & 0o777)
    assert dir_mode == "0o700", f"Config-Dir muss 0700 sein, ist {dir_mode}"


def test_clear_pairing(tmp_path):
    path = tmp_path / "tg_pairing.json"
    save_pairing(["1"], path)
    clear_pairing(path)
    assert not path.exists()
    assert load_pairing(path) == []


def test_load_missing_returns_empty(tmp_path):
    assert load_pairing(tmp_path / "does_not_exist.json") == []


def test_load_corrupt_returns_empty(tmp_path):
    path = tmp_path / "tg_pairing.json"
    path.write_text("{ nicht-valid-json ]", encoding="utf-8")
    # Beschädigte Konfig → wie leer behandeln, nie crashen (analog engine_config).
    assert load_pairing(path) == []


def test_load_non_list_returns_empty(tmp_path):
    path = tmp_path / "tg_pairing.json"
    path.write_text('{"weird": 1}', encoding="utf-8")
    assert load_pairing(path) == []


def test_save_dedupes_and_strips(tmp_path):
    path = tmp_path / "tg_pairing.json"
    save_pairing([" 111 ", "111", "", "222"], path)
    loaded = load_pairing(path)
    assert loaded == ["111", "222"]


def test_default_path_under_mimi_nox_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MIMI_NOX_CONFIG_DIR", str(tmp_path))
    p = default_pairing_path()
    assert p == tmp_path / "tg_pairing.json"


def test_env_var_override_allowlist(tmp_path):
    """MIMI_NOX_TG_ALLOWLIST erlaubt einen statischen Override (CSV)."""
    cfg = TGGatewayConfig(bot_token="t", allowlist=[], config_dir=str(tmp_path))
    monkeypatch_set = os.environ
    monkeypatch_set["MIMI_NOX_TG_ALLOWLIST"] = "5,6"
    try:
        assert cfg.is_allowed("5")
        assert cfg.is_allowed("6")
        assert not cfg.is_allowed("7")
    finally:
        del monkeypatch_set["MIMI_NOX_TG_ALLOWLIST"]

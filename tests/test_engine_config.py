"""◑ MiMi Nox – Tests für Engine-Auswahl/Onboarding in der TUI-CLI.

Deckt die neue Capability ab: `miminox tui` startbar ohne Modell-Flag,
interaktive Engine-Auswahl (Onboarding) und Persistenz nach engine.json.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

import core.engine_config as ec
import miminox_cli as cli

ROOT = Path(__file__).resolve().parents[1]


def _fake_input(*values: str):
    """Erzeugt eine input_fn, die die übergebenen Antworten nacheinander liefert."""
    queue = list(values)

    def fn(prompt: str) -> str:
        assert queue, f"input_fn wurde öfter aufgerufen als Antworten vorhanden: {prompt}"
        return queue.pop(0)

    return fn


def test_onboarding_local_ollama_default_model_persists(tmp_path):
    """GIVEN User wählt Engine 1 (lokale Ollama)
    WHEN das Onboarding läuft (leeres Modell → Default)
    THEN wird local_ollama mit Default-Modell persistiert und wiedergefunden."""
    choice = cli._run_engine_onboarding(
        input_fn=_fake_input("1", ""), config_path=tmp_path / "engine.json"
    )

    assert choice.provider == "local_ollama"
    assert choice.model == cli.DEFAULT_MODEL
    assert choice.api_url is None

    reloaded = ec.load_engine_config(tmp_path / "engine.json")
    assert reloaded is not None
    assert reloaded.provider == "local_ollama"
    assert reloaded.model == cli.DEFAULT_MODEL
    assert reloaded.api_url is None


def test_onboarding_dgx_spark_requires_url_and_model(tmp_path):
    """GIVEN User wählt Engine 3 (DGX-Spark ds4)
    WHEN URL und Modell eingegeben werden
    THEN wird openai_compatible mit URL und Modell persistiert."""
    choice = cli._run_engine_onboarding(
        input_fn=_fake_input("3", "http://spark-...:8000/v1", "deepseek-v4-flash"),
        config_path=tmp_path / "engine.json",
    )

    assert choice.provider == "openai_compatible"
    assert choice.model == "deepseek-v4-flash"
    assert choice.api_url == "http://spark-...:8000/v1"

    reloaded = ec.load_engine_config(tmp_path / "engine.json")
    assert reloaded is not None
    assert reloaded.provider == "openai_compatible"
    assert reloaded.api_url == "http://spark-...:8000/v1"


def test_onboarding_invalid_choice_retries_until_ok(tmp_path):
    """GIVEN User tippt eine ungültige Engine-Wahl (9)
    WHEN das Onboarding das nächste Mal mit gültiger Wahl antwortet
    THEN läuft es mit der gültigen Wahl weiter."""
    choice = cli._run_engine_onboarding(
        input_fn=_fake_input("9", "1", ""), config_path=tmp_path / "engine.json"
    )

    assert choice.provider == "local_ollama"


def test_engine_config_roundtrip_and_clear(tmp_path):
    """GIVEN eine Engine-Auswahl gespeichert wird
    WHEN sie geladen und anschließend entfernt wird
    THEN ist der Roundtrip identisch und clear liefert None."""
    cfg = tmp_path / "engine.json"
    assert ec.save_engine_config(
        ec.EngineChoice(provider="local_ollama", model="gemma4:12b"), cfg
    )

    loaded = ec.load_engine_config(cfg)
    assert loaded is not None
    assert loaded.model == "gemma4:12b"

    assert ec.clear_engine_config(cfg)
    assert ec.load_engine_config(cfg) is None


def test_cmd_tui_without_flags_uses_persisted_config(tmp_path):
    """GIVEN eine Engine-Konfig existiert (DGX-Spark)
    WHEN `cmd_tui` ohne Modell-/URL-Flags läuft
    THEN werden Modell und URL als Flags an `miminox.main()` weitergeleitet."""
    cfg = tmp_path / "engine.json"
    ec.save_engine_config(
        ec.EngineChoice(
            provider="openai_compatible",
            model="deepseek-v4-flash",
            api_url="http://spark-...:8000/v1",
        ),
        cfg,
    )

    args = argparse.Namespace(model=None, api_url=None, configure=False, reset=False,
                              dry_run=False, yes=False, no=False)
    captured: list[list[str]] = []
    with patch("miminox.main", side_effect=lambda: captured.append(sys.argv.copy())):
        cli.cmd_tui(args, config_path=cfg)

    assert captured == [
        ["mimi-nox", "--model", "deepseek-v4-flash", "--api-url", "http://spark-...:8000/v1"]
    ]


def test_cmd_tui_explicit_flags_skip_onboarding(tmp_path):
    """GIVEN der User übergibt explizit --model und --api-url
    WHEN `cmd_tui` läuft (auch mit --configure)
    THEN gewinnen die Flags und kein Onboarding wird ausgelöst."""
    args = argparse.Namespace(
        model="gemma4:12b",
        api_url="http://custom:8000/v1",
        configure=True,
        reset=False,
        dry_run=False,
        yes=False,
        no=False,
    )
    captured: list[list[str]] = []
    with patch("miminox.main", side_effect=lambda: captured.append(sys.argv.copy())), patch(
        "miminox_cli._run_engine_onboarding"
    ) as onboarding:
        cli.cmd_tui(args, config_path=tmp_path / "engine.json")

    assert captured == [
        ["mimi-nox", "--model", "gemma4:12b", "--api-url", "http://custom:8000/v1"]
    ]
    onboarding.assert_not_called()


# ── Phase 0: Security-Gate (AppSec/Least-Privilege) ───────────────────────────
import stat


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_saved_engine_config_file_permissions_0600(tmp_path):
    """GIVEN eine Engine-Auswahl gespeichert wird
    WHEN die Datei angelegt ist
    THEN hat engine.json 0600 (nur Owner les-/schreibbar) – Least-Privilege."""
    cfg = tmp_path / "engine.json"
    assert ec.save_engine_config(
        ec.EngineChoice(provider="openai_compatible", model="deepseek-v4-flash", api_url="http://x/v1"), cfg
    )
    assert _mode(cfg) == 0o600


def test_saved_engine_config_dir_permissions_0700(tmp_path):
    """GIVEN eine Engine-Auswahl gespeichert wird
    WHEN das Konfig-Verzeichnis angelegt wird
    THEN hat es 0700 (nur Owner) – keine Side-Channels für andere Prozesse."""
    cfg_dir = tmp_path / "cfg"
    cfg = cfg_dir / "engine.json"
    assert ec.save_engine_config(ec.EngineChoice(provider="local_ollama", model="gemma4:12b"), cfg)
    assert _mode(cfg_dir) == 0o700


def test_saved_engine_config_never_persists_api_key(tmp_path):
    """GIVEN eine OpenAI-kompatible Engine mit API-Key gespeichert wird
    WHEN die Datei geschrieben wird
    THEN enthält engine.json KEIN Key-/Secret-Feld (Keys bleiben Session-Env)."""
    cfg = tmp_path / "engine.json"
    assert ec.save_engine_config(
        ec.EngineChoice(
            provider="openai_compatible", model="custom-model", api_url="https://api.example/v1"
        ),
        cfg,
    )
    raw = cfg.read_text(encoding="utf-8").lower()
    for forbidden in ("api_key", "apikey", "secret", "token", "key"):
        assert forbidden not in raw, f"engine.json darf kein '{forbidden}'-Feld enthalten: {raw}"

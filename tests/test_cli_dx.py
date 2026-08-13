"""Phase 1 DX-Gate: Shell-Completions, --version, Exit-Codes, JSON-Error-Härtung."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "miminox_cli.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    """Führt die echte CLI aus (Integration)."""
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": ""},
    )


def test_completion_bash():
    r = _run("completion", "bash")
    assert r.returncode == 0
    assert "complete -F _miminox_complete miminox" in r.stdout
    for cmd in ("start", "doctor", "update", "tui", "completion"):
        assert cmd in r.stdout


def test_completion_zsh():
    r = _run("completion", "zsh")
    assert r.returncode == 0
    assert "_describe 'command' cmds" in r.stdout
    assert "compdef _miminox miminox" in r.stdout


def test_completion_fish():
    r = _run("completion", "fish")
    assert r.returncode == 0
    assert "complete -c miminox" in r.stdout


def test_completion_bad_shell_usage_error():
    r = _run("completion", "tcsh")
    assert r.returncode == 2
    assert "invalid choice" in r.stderr


def test_version_flag():
    r = _run("--version")
    assert r.returncode == 0
    assert "mimi-nox" in r.stdout


def test_unknown_subcommand_usage_error():
    r = _run("nonsense")
    assert r.returncode == 2


def test_update_accepts_json_flag():
    r = _run("update", "--json")
    # Flag wird akzeptiert (kein usage error wegen unbekanntem Flag).
    assert r.returncode in (0, 1)


def test_main_hardening_returns_exit_1_with_json_error(monkeypatch, capsys):
    """Unerwartete Exception in einer cmd-Funktion → Exit 1, --json liefert stabiles Error-JSON."""
    import miminox_cli

    def boom(_args):
        raise RuntimeError("kaputt")

    monkeypatch.setattr(miminox_cli, "cmd_doctor", boom)
    monkeypatch.setattr(sys, "argv", ["miminox", "doctor", "--json"])
    with pytest.raises(SystemExit) as exc:
        miminox_cli.main()
    assert exc.value.code == 1
    # JSON-Error-Feedback ist auf stdout; keine Secrets, klare Cause+Fix.
    data = json.loads(capsys.readouterr().out)
    assert data["error"]["code"] == 1
    assert "kaputt" in data["error"]["message"]


def test_cli_keeps_heavy_imports_lazy():
    """
    Startup-Budget-Gate (Phase 1 Item 4): die CLI muss beim Import schnell
    starten (< 100 ms). Schwere Module (fastapi, uvicorn, ollama, rich,
    textual, server) dürfen NICHT beim Top-Level-Import geladen werden —
    sie bleiben lazy (nur in cmd_serve/cmd_start).
    """
    code = (
        "import sys; import miminox_cli; "
        "print(' '.join(m for m in "
        "['fastapi','uvicorn','ollama','rich','textual','server'] "
        "if m in sys.modules))"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": ""},
    )
    assert r.returncode == 0
    # Kein schweres Modul darf beim Load importiert worden sein.
    assert r.stdout.strip() == ""

"""Tests für `miminox session ...` (Phase 2 Item 7, CLI-Integration).

Nutzt das etablierte subprocess-Pattern aus test_cli_dx.py.
MIMI_NOX_SESSIONS_DIR isoliert die Sessions von der echten ~/.mimi-nox.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "miminox_cli.py"


def _run(*args: str, sessions_dir: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = ""
    env["MIMI_NOX_SESSIONS_DIR"] = str(sessions_dir)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir(parents=True)
    return d


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


def test_session_list_empty(sessions_dir: Path):
    r = _run("session", "list", sessions_dir=sessions_dir)
    assert r.returncode == 0
    assert "Keine Sessions" in r.stdout


def test_session_list_json_structure(sessions_dir: Path):
    r = _run("session", "list", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list)
    assert data == []


# ---------------------------------------------------------------------------
# new
# ---------------------------------------------------------------------------


def test_session_new_creates_and_sets_active(sessions_dir: Path):
    r = _run("session", "new", "--title", "Test", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["title"] == "Test"
    assert len(entry["id"]) == 8

    # Die Session taucht in der Liste auf und ist aktiv
    r2 = _run("session", "list", "--json", sessions_dir=sessions_dir)
    lst = json.loads(r2.stdout)
    assert len(lst) == 1
    assert lst[0]["id"] == entry["id"]
    assert lst[0]["title"] == "Test"


def test_session_new_without_title_usage_error(sessions_dir: Path):
    r = _run("session", "new", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 2
    data = json.loads(r.stdout)
    assert data["error"]["code"] == 2
    assert "Titel" in data["error"]["message"]


# ---------------------------------------------------------------------------
# switch
# ---------------------------------------------------------------------------


def test_session_switch_changes_active(sessions_dir: Path):
    a = json.loads(_run("session", "new", "--title", "A", "--json", sessions_dir=sessions_dir).stdout)
    b = json.loads(_run("session", "new", "--title", "B", "--json", sessions_dir=sessions_dir).stdout)
    # B ist jetzt aktiv (new setzt aktiv)
    r = _run("session", "switch", "--id", a["id"], "--json", sessions_dir=sessions_dir)
    assert r.returncode == 0
    assert json.loads(r.stdout)["active_id"] == a["id"]


def test_session_switch_unknown_id_usage_error(sessions_dir: Path):
    r = _run("session", "switch", "--id", "deadbeef", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 2
    data = json.loads(r.stdout)
    assert data["error"]["code"] == 2


def test_session_switch_without_id_usage_error(sessions_dir: Path):
    r = _run("session", "switch", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 2


# ---------------------------------------------------------------------------
# rm
# ---------------------------------------------------------------------------


def test_session_rm_deletes(sessions_dir: Path):
    a = json.loads(_run("session", "new", "--title", "Gone", "--json", sessions_dir=sessions_dir).stdout)
    r = _run("session", "rm", "--id", a["id"], "--json", sessions_dir=sessions_dir)
    assert r.returncode == 0
    # Nicht mehr in der Liste
    r2 = _run("session", "list", "--json", sessions_dir=sessions_dir)
    lst = json.loads(r2.stdout)
    assert all(s["id"] != a["id"] for s in lst)
    # Die Message-Datei ist weg
    assert not (sessions_dir / f"{a['id']}.json").exists()


def test_session_rm_unknown_id_usage_error(sessions_dir: Path):
    r = _run("session", "rm", "--id", "deadbeef", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 2


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------


def test_session_rename_updates_title(sessions_dir: Path):
    a = json.loads(_run("session", "new", "--title", "Before", "--json", sessions_dir=sessions_dir).stdout)
    r = _run("session", "rename", "--id", a["id"], "--title", "After", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 0
    entry = json.loads(r.stdout)
    assert entry["title"] == "After"


def test_session_rename_missing_args_usage_error(sessions_dir: Path):
    r = _run("session", "rename", "--json", sessions_dir=sessions_dir)
    assert r.returncode == 2


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------


def test_session_help_lists_actions(sessions_dir: Path):
    r = _run("session", "--help", sessions_dir=sessions_dir)
    assert r.returncode == 0
    for action in ("list", "new", "switch", "rm", "rename"):
        assert action in r.stdout


def test_main_help_lists_session_subcommand(sessions_dir: Path):
    r = _run("--help", sessions_dir=sessions_dir)
    assert r.returncode == 0
    assert "session" in r.stdout

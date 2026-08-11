"""
Tests for CLI UX polish — MiMi Nox CLI state-of-the-art surface.

Covers: --version flag, --help epilog (examples + exit codes),
doctor summary line, and a single source of truth for the version string.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "miminox_cli.py"), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )


# ---------------------------------------------------------------------------
# --version
# ---------------------------------------------------------------------------


def test_cli_version_flag_prints_version():
    """
    GIVEN the CLI
    WHEN --version is requested
    THEN a version string is printed and exit code is 0.
    """
    result = _run_cli("--version")
    assert result.returncode == 0
    assert "mimi-nox" in result.stdout
    assert "v" in result.stdout.lower() or result.stdout.count(".") >= 1


def test_cli_version_matches_pyproject():
    """
    GIVEN the packaged project
    WHEN the version source is read
    THEN core._version.__version__ agrees with pyproject [project].version.
    """
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    import core._version as v

    assert v.__version__ == pyproject["project"]["version"]


# ---------------------------------------------------------------------------
# --help epilog
# ---------------------------------------------------------------------------


def test_cli_help_documents_examples_and_exit_codes():
    """
    GIVEN the CLI
    WHEN --help is shown
    THEN the epilog documents examples and exit-code semantics.
    """
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "start" in result.stdout
    assert "doctor" in result.stdout
    assert "update" in result.stdout
    assert "Examples" in result.stdout
    assert "Exit codes" in result.stdout


def test_cli_subcommand_help_has_usage():
    """
    GIVEN a subcommand parser
    WHEN doctor --help is shown
    THEN it documents the fix mode and key flags.
    """
    result = _run_cli("doctor", "--help")
    assert result.returncode == 0
    assert "--fix" in result.stdout
    assert "--json" in result.stdout


# ---------------------------------------------------------------------------
# doctor summary line
# ---------------------------------------------------------------------------


def test_doctor_prints_summary_line(capsys):
    """
    GIVEN a fully healthy local setup
    WHEN miminox doctor runs
    THEN a final Summary line reports the number of checks that pass.
    """
    import miminox_cli

    args = miminox_cli.build_parser().parse_args(["doctor", "--model", "gemma4:12b"])
    # Simulate a healthy setup: ollama present, model installed + loadable,
    # server responding.
    import miminox_cli as m
    from unittest.mock import patch

    with (
        patch.object(m, "_ollama_binary", return_value="/usr/local/bin/ollama"),
        patch.object(m, "_model_installed", return_value=True),
        patch.object(m, "_json_get", return_value={"models": [{"name": "gemma4:12b"}]}),
        patch.object(m, "_model_loadable", return_value=(True, "test generation ok")),
    ):
        exit_code = miminox_cli.cmd_doctor(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Summary:" in captured.out
    assert "checks OK" in captured.out

#!/usr/bin/env bash
# run-tests.sh — Kanonischer Test-Einstieg für MiMi Nox.
#
# Härtet die Umgebung gegen Dev-Umgebungs-Kontamination:
#   - leert PYTHONPATH (verhindert, dass der Hermes/System-venv mit python3.11
#     ins lokale pytest reinspielt und pydantic_core-Mismatch auslöst)
#   - nutzt explizit das lokale .venv (`.venv/bin/python -m pytest`)
# Übergibt alle Argumente unverändert an pytest.
#
# Beispiele:
#   ./scripts/run-tests.sh                                  # komplette Suite
#   ./scripts/run-tests.sh tests/test_installer_cli.py -q   # fokussiert
set -euo pipefail
cd "$(dirname "$0")/.."   # Projekt-Root

# PYTHONPATH hart leeren — die Root-Cause des pydantic_core-Mismatchs
export PYTHONPATH=
unset PYTHONPATH 2>/dev/null || true

# Release-Bar Standard-Env (überschreibbar von außen)
export MIMI_NOX_MODEL="${MIMI_NOX_MODEL:-mock}"
export MIMI_NOX_OFFLINE="${MIMI_NOX_OFFLINE:-1}"
export MIMI_NOX_MEMORY_DIR="${MIMI_NOX_MEMORY_DIR:-/tmp/mimi-nox-test-memory}"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "❌ .venv fehlt — bitte einmalig:" >&2
  echo "   python -m venv .venv && .venv/bin/pip install -e '.[dev]'" >&2
  exit 1
fi

echo "▶ run-tests.sh: PYTHONPATH geleert, venv=$PWD/$PY"
exec "$PY" -m pytest "$@"

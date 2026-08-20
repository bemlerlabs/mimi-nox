#!/usr/bin/env bash
# Launch-Demo-GIF: MiMi Nox — Trust (Approval-Gate) + deterministischer Tool-Modus
# + LIVE Qwen 3.8 27B (DGX-Spark) + On-Device-Gateway (Telegram, kein Cloud-Relay).
# Pipeline: tmux + asciinema -> agg (Skill: terminal-ui-demo-recording).
set -euo pipefail

REPO=/Users/sanji/mimi-nox
SESSION=mimidemo
CAST=/tmp/mimidemo.cast
OUT="$REPO/docs/media/miminox-demo-launch.gif"

# Projekt-Venv bevorzugen, sonst die Arbeits-Interpretern (alle Deps installiert).
if [ -x "$REPO/.venv/bin/python" ]; then PY="$REPO/.venv/bin/python"; else PY="$(command -v python)"; fi

# Preflight: Qwen-Smoke muss LIVE grün sein (sonst wäre die Engine-Demo Fake).
"$PY" -m pytest "$REPO/tests/test_dgx_qwen_smoke.py" -q >/tmp/preflight.log 2>&1 \
  || { echo "PREFLIGHT FAILED: $(tail -3 /tmp/preflight.log)"; exit 1; }
echo "preflight ok: $(tail -1 /tmp/preflight.log)"

rm -f "$CAST"
tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" -x 110 -y 32 "bash -i"

send() { tmux send-keys -t "$SESSION" "$1" Enter; }

# asciinema startet den inneren TTY-Recorder
send "cd $REPO && asciinema rec --idle-timeout 2 $CAST bash"
sleep 2

send "clear"
sleep 1
send "echo '=== MiMi Nox — Approval-Gate (Diff + --dry-run + --yes) ==='"
sleep 1

# 1) DRY-RUN: Diff-Vorschau, KEINE Datei
send "$PY miminox_cli.py tool create_svg --arg filename=preview_miminox_demo.svg --arg 'svg_code=<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 400 200\"><rect width=\"400\" height=\"200\" fill=\"#1a1a2e\"/><text x=\"20\" y=\"60\" fill=\"#4ecdc4\" font-size=\"28\">MiMi Nox</text></svg>' --dry-run"
sleep 4

# 2) --yes: explizite Freigabe, Datei wird geschrieben
send "$PY miminox_cli.py tool create_svg --arg filename=preview_miminox_demo.svg --arg 'svg_code=<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 400 200\"><rect width=\"400\" height=\"200\" fill=\"#1a1a2e\"/><text x=\"20\" y=\"60\" fill=\"#4ecdc4\" font-size=\"28\">MiMi Nox</text></svg>' --yes"
sleep 3
send "ls -l ~/Downloads/preview_miminox_demo.svg"
sleep 2

# 3) LIVE Qwen 3.8 27B via DGX-Spark (3 reale Completions im Test)
send "echo '=== Qwen 3.8 27B (DGX-Spark) — LIVE e2e-Smoke ==='"
sleep 1
send "$PY -m pytest tests/test_dgx_qwen_smoke.py -v"
sleep 10

# 4) On-Device-Gateway (Telegram, kein Cloud-Relay)
send "echo '=== On-Device-Gateway: Telegram-Channel (kein Cloud-Relay) ==='"
sleep 1
send "$PY miminox_cli.py tg --help"
sleep 3

# 5) Aufräumen: Demo-Datei weg, Recorder beenden
send "rm -f ~/Downloads/preview_miminox_demo.svg"
sleep 1
send "exit"
sleep 2
tmux kill-session -t "$SESSION" 2>/dev/null || true

agg "$CAST" "$OUT" --font-size 13 --theme dracula --speed 1.0
rm -f "$CAST"
echo "GIF: $OUT ($(du -h "$OUT" | cut -f1))"

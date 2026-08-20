#!/usr/bin/env bash
# Launch-Demo: MiMi Nox — Trust (Approval-Gate) + LIVE Qwen 3.8 27B (DGX-Spark)
# + On-Device-Gateway. Wird von asciinema als PTY-Sitzung aufgenommen (GIF-Qualität).
set -uo pipefail
REPO=/Users/sanji/mimi-nox
if [ -x "$REPO/.venv/bin/python" ]; then PY="$REPO/.venv/bin/python"; else PY="$(command -v python)"; fi
cd "$REPO"

step() { echo; echo "\$ $1"; sleep 0.6; }

clear
step "echo 'MiMi Nox — Sprint 3 Launch Demo: Trust + Qwen 3.8 (DGX) + Gateway'"
echo "MiMi Nox — Sprint 3 Launch Demo: Trust + Qwen 3.8 (DGX) + Gateway"
sleep 1.5

step "$PY miminox_cli.py tool create_svg --arg filename=preview_miminox_demo.svg --arg 'svg_code=<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 400 200\"><rect width=\"400\" height=\"200\" fill=\"#1a1a2e\"/><text x=\"20\" y=\"60\" fill=\"#4ecdc4\" font-size=\"28\">MiMi Nox</text></svg>' --dry-run"
"$PY" miminox_cli.py tool create_svg \
  --arg filename=preview_miminox_demo.svg \
  --arg 'svg_code=<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#1a1a2e"/><text x="20" y="60" fill="#4ecdc4" font-size="28">MiMi Nox</text></svg>' \
  --dry-run
sleep 2

step "$PY miminox_cli.py tool create_svg --arg filename=preview_miminox_demo.svg --arg 'svg_code=<svg>…</svg>' --yes   # explizite Freigabe"
"$PY" miminox_cli.py tool create_svg \
  --arg filename=preview_miminox_demo.svg \
  --arg 'svg_code=<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 200"><rect width="400" height="200" fill="#1a1a2e"/><text x="20" y="60" fill="#4ecdc4" font-size="28">MiMi Nox</text></svg>' \
  --yes
sleep 1
step "ls -l ~/Downloads/preview_miminox_demo.svg"
ls -l "$HOME/Downloads/preview_miminox_demo.svg"
sleep 1.5

step "$PY -m pytest tests/test_dgx_qwen_smoke.py -v   # LIVE: Qwen 3.8 27B via DGX-Spark"
"$PY" -m pytest tests/test_dgx_qwen_smoke.py -v
sleep 2.5

step "$PY miminox_cli.py tg --help   # On-Device-Gateway: Telegram, kein Cloud-Relay"
"$PY" miminox_cli.py tg --help
sleep 2

step "rm -f ~/Downloads/preview_miminox_demo.svg"
rm -f "$HOME/Downloads/preview_miminox_demo.svg"
echo
echo "✓ Demo fertig: Approval-Gate (dry-run → yes) · Qwen 3.8 LIVE · On-Device-Gateway"
sleep 2

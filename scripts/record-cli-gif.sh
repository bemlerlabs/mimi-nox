#!/usr/bin/env bash
# CLI-Demo-GIF-Aufzeichnung für MiMi Nox (Textual TUI)
# Voraussetzungen: asciinema + agg installiert (siehe README unten)
#   pip install asciinema
#   cargo install agg  (oder: brew install agg)
#
# Die TUI läuft nur im TTY. asciinema zeichnet die Session auf, agg macht daraus ein GIF.
set -euo pipefail
cd "$(dirname "$0")/.."
# venv-Binaries (asciinema, miminox) in den PATH holen — Skript läuft ohne aktiviertes venv
export PATH="$(pwd)/.venv/bin:$PATH"

MODEL="${1:-gemma4:e4b}"
OUT_DIR="docs/media"
OUT="${OUT_DIR}/mimi-nox-cli-demo.gif"

command -v asciinema >/dev/null || { echo "asciinema fehlt (pip install asciinema)"; exit 1; }
command -v agg     >/dev/null || { echo "agg fehlt (cargo install agg)"; exit 1; }
command -v tmux    >/dev/null || { echo "tmux fehlt"; exit 1; }

echo "Starte Aufzeichnung von 'miminox tui --model $MODEL' …"
# asciinema: 2s idle-timeout, max 120s
asciinema rec "${OUT_DIR}/_rec.cast" --overwrite -i 2 -q -c '
  tmux new-session -d -s miminox "exec .venv/bin/miminox tui --model '"${MODEL}"'"
  tmux send-keys -t miminox "/post Zeig mir die 5 wichtigsten Best Practices für lokale LLMs" Enter
  sleep 8
  tmux send-keys -t miminox "/swarm Vergleiche lokale vs. cloud LLM inference" Enter
  sleep 6
  tmux send-keys -t miminox q
  tmux wait-for miminox || true
'

echo "Konvertiere zu GIF …"
agg "${OUT_DIR}/_rec.cast" "${OUT}" --font-size 16 --theme dracula --speed 1.2
rm -f "${OUT_DIR}/_rec.cast"
echo "Fertig: ${OUT}"
ls -lh "${OUT}"

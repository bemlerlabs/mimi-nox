#!/bin/bash
# ◑ MiMiNox — Schnellstart
# Ein Befehl. 15 Minuten. Läuft dann offline.
#
# Voraussetzung: Linux/macOS mit curl und Node.js 18+
# Ausführen: bash setup.sh

set -e

echo ""
echo "◑  MiMiNox — Offline-Assistent"
echo "   Kein Abo. Kein Internet danach. Keine Cloud."
echo ""

# ── 1. Ollama prüfen / installieren ────────────────────────────
if ! command -v ollama &>/dev/null; then
  echo "► Ollama wird installiert..."
  curl -fsSL https://ollama.ai/install.sh | sh
else
  echo "✅ Ollama vorhanden ($(ollama --version 2>/dev/null | head -1))"
fi

# ── 2. Gemma 4 12B laden ───────────────────────────────────────
echo ""
echo "► Gemma 4 12B wird geladen (einmalig)..."
echo "  Das dauert je nach Internetverbindung 5-15 Minuten."
ollama pull gemma4:12b && echo "✅ Gemma 4 12B bereit"

# ── 3. Node.js-Abhängigkeiten ──────────────────────────────────
echo ""
echo "► Node.js-Pakete installieren..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/v2"
cd "$SCRIPT_DIR"
npm install --silent && echo "✅ Pakete bereit"

cd dashboard && npm install --silent && echo "✅ Frontend-Pakete bereit"

# ── 4. Frontend bauen ──────────────────────────────────────────
echo ""
echo "► Frontend wird gebaut..."
npm run build --silent && echo "✅ Frontend gebaut"
cd ..

# ── 5. Starten ─────────────────────────────────────────────────
echo ""
echo "◑  FERTIG — MiMiNox startet jetzt"
echo ""
echo "  Öffne im Browser:  http://localhost:5173"
echo "  Auf dem Handy:     http://$(hostname -I | awk '{print $1}'):5173"
echo ""
echo "  Tipps zum Start:"
echo "  → \"Merke dir: Mein Name ist [dein Name]\""
echo "  → \"Merke dir: Meine Blutgruppe ist [X]\""
echo "  → \"Ich lebe in Österreich\" (oder Schweiz/Deutschland)"
echo ""

# Backend starten
node server/index.js &
BACKEND_PID=$!
echo "  ◑ Backend läuft (PID $BACKEND_PID)"

# Frontend dev server
cd dashboard && npm run dev &
FRONTEND_PID=$!
echo "  ◑ Frontend läuft (PID $FRONTEND_PID)"

echo ""
echo "  Beenden mit: Ctrl+C"
echo ""

# Sauber beenden
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'MiMiNox beendet.'" EXIT
wait

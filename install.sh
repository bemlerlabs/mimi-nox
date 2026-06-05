#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
DIM='\033[2m'
BOLD='\033[1m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="${MIMI_NOX_REPO_URL:-https://github.com/MimiTechAi/mimi-nox.git}"
INSTALL_DIR="${MIMI_NOX_INSTALL_DIR:-$HOME/Documents/MiMi-Nox}"
MODEL="${MIMI_NOX_MODEL:-gemma4:12b}"
EMBED_MODEL="${MIMI_NOX_EMBED_MODEL:-nomic-embed-text}"
PORT="${MIMI_NOX_PORT:-8765}"
NO_START="${MIMI_NOX_NO_START:-0}"
SKIP_MODEL="${MIMI_NOX_SKIP_MODEL:-0}"
DRY_RUN="${MIMI_NOX_DRY_RUN:-0}"

for arg in "$@"; do
  case "$arg" in
    --no-start) NO_START=1 ;;
    --skip-model) SKIP_MODEL=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --help|-h)
      echo "Usage: ./install.sh [--no-start] [--skip-model] [--dry-run]"
      echo "Env: MIMI_NOX_INSTALL_DIR, MIMI_NOX_MODEL, MIMI_NOX_PORT"
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { echo -e "${GREEN}▶${NC} ${BOLD}$1${NC}"; }
info() { echo -e "  ${DIM}$1${NC}"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1" >&2; exit 1; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  DRY-RUN: $*"
  else
    "$@"
  fi
}

is_project_root() {
  [[ -f "pyproject.toml" && -d "app/src" && -f "run_server.py" ]]
}

echo ""
echo -e "${GREEN}${BOLD}MiMi Nox offline-first installer${NC}"
echo -e "${DIM}Local Ollama + ${MODEL} by default. Online/API is optional.${NC}"
echo ""

if ! is_project_root; then
  step "Installationsordner vorbereiten"
  command -v git >/dev/null 2>&1 || fail "Git fehlt. Installiere Git und starte den Befehl erneut."
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [[ -d "$INSTALL_DIR/.git" ]]; then
    ok "Vorhandenes Repository gefunden: $INSTALL_DIR"
    cd "$INSTALL_DIR"
    run git pull --ff-only
  elif [[ -e "$INSTALL_DIR" ]]; then
    fail "$INSTALL_DIR existiert bereits, ist aber kein Git-Repository. Setze MIMI_NOX_INSTALL_DIR auf einen anderen Pfad."
  else
    run git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
  fi
  exec bash ./install.sh "$@"
fi

PROJECT_DIR="$(pwd)"
OS_NAME="$(uname -s)"

step "System prüfen"
case "$OS_NAME" in
  Darwin|Linux) ok "$OS_NAME unterstützt" ;;
  *) fail "Automatischer Installer unterstützt macOS und Linux. Für Windows nutze install.ps1." ;;
esac
command -v curl >/dev/null 2>&1 || fail "curl fehlt. Installiere curl und starte den Installer erneut."

FREE_KB=$(df -Pk "$PROJECT_DIR" | awk 'NR==2 {print $4}')
if [[ "${FREE_KB:-0}" -lt 16000000 ]]; then
  fail "Mindestens 16 GB freier Speicher empfohlen. Aktuell verfügbar: $((FREE_KB / 1024 / 1024)) GB."
fi
ok "Speicherplatz OK"

step "Python 3.10+ prüfen"
find_uv() {
  for candidate in \
    "$(command -v uv 2>/dev/null || true)" \
    "$HOME/.local/bin/uv" \
    "$HOME/.cargo/bin/uv"; do
    [[ -n "$candidate" && -x "$candidate" ]] && { echo "$candidate"; return 0; }
  done
  return 1
}

find_python() {
  uv_bin="$(find_uv || true)"
  if [[ -n "$uv_bin" ]]; then
    uv_python="$("$uv_bin" python find 3.12 2>/dev/null || true)"
    if [[ -n "$uv_python" && -x "$uv_python" ]]; then
      echo "$uv_python"
      return 0
    fi
  fi

  for candidate in \
    python3.13 python3.12 python3.11 python3.10 python3 python \
    /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 /opt/homebrew/bin/python3 \
    /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10 /usr/local/bin/python3; do
    if [[ "$candidate" == */* ]]; then
      [[ -x "$candidate" ]] || continue
      bin="$candidate"
    else
      command -v "$candidate" >/dev/null 2>&1 || continue
      bin="$(command -v "$candidate")"
    fi
    if "$bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
      echo "$bin"
      return 0
    fi
  done
  return 1
}

install_uv_python() {
  info "Installiere eine lokale Python-Runtime mit uv."
  uv_bin="$(find_uv || true)"
  if [[ -z "$uv_bin" ]]; then
    run sh -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
    uv_bin="$(find_uv || true)"
  fi
  if [[ -z "$uv_bin" && "$DRY_RUN" == "1" ]]; then
    uv_bin="$HOME/.local/bin/uv"
  fi
  [[ -n "$uv_bin" ]] || return 1
  run "$uv_bin" python install 3.12
}

install_python() {
  info "Python 3.10+ fehlt. Installation startet."
  if [[ "$OS_NAME" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      run brew install python@3.12 || run brew install python
    else
      install_uv_python || fail "Python 3.10+ konnte nicht automatisch installiert werden."
    fi
  elif install_uv_python; then
    return 0
  elif command -v apt-get >/dev/null 2>&1; then
    run sudo apt-get update
    run sudo apt-get install -y python3 python3-venv python3-pip
  elif command -v dnf >/dev/null 2>&1; then
    run sudo dnf install -y python3 python3-pip
  elif command -v yum >/dev/null 2>&1; then
    run sudo yum install -y python3 python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    run sudo pacman -Sy --noconfirm python python-pip
  else
    fail "Python 3.10+ fehlt. Installiere Python und python3-venv mit deinem Paketmanager und starte ./install.sh erneut."
  fi
}

PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then
  install_python
  PYTHON="$(find_python || true)"
fi
if [[ -z "$PYTHON" && "$DRY_RUN" == "1" ]]; then
  PYTHON="python3"
  ok "Python 3.10+ würde installiert"
else
  [[ -n "$PYTHON" ]] || fail "Python 3.10+ fehlt. Installiere Python und starte den Installer erneut."
  ok "$("$PYTHON" -c 'import sys; print(sys.version.split()[0])') gefunden"
fi

find_ollama() {
  for candidate in \
    "/Applications/Ollama.app/Contents/Resources/ollama" \
    "/usr/local/bin/ollama" \
    "/opt/homebrew/opt/ollama/bin/ollama" \
    "/opt/homebrew/bin/ollama" \
    "$(command -v ollama 2>/dev/null || true)"; do
    [[ -n "$candidate" && -x "$candidate" ]] && { echo "$candidate"; return 0; }
  done
  return 1
}

step "Ollama prüfen"
OLLAMA_BIN="$(find_ollama || true)"
if [[ -z "$OLLAMA_BIN" ]]; then
  info "Ollama CLI fehlt. Installation startet."
  if [[ "$OS_NAME" == "Darwin" ]]; then
    if command -v brew >/dev/null 2>&1; then
      run brew install --cask ollama || run brew install ollama
    else
      fail "Homebrew fehlt. Installiere Ollama von https://ollama.com/download und starte danach ./install.sh erneut."
    fi
  else
    run sh -c "curl -fsSL https://ollama.com/install.sh | sh"
  fi
  OLLAMA_BIN="$(find_ollama || true)"
fi
[[ -n "$OLLAMA_BIN" ]] || fail "Ollama wurde nicht gefunden."
ok "$OLLAMA_BIN"

step "Ollama Service starten"
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  if [[ "$OS_NAME" == "Darwin" && -d "/Applications/Ollama.app" ]]; then
    run open -a Ollama
  fi
  run "$OLLAMA_BIN" serve >/tmp/mimi-nox-ollama.log 2>&1 &
  sleep 3
fi
for _ in $(seq 1 30); do
  curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1 || fail "Ollama Service antwortet nicht."
ok "Ollama läuft"

if [[ "$SKIP_MODEL" != "1" ]]; then
  step "KI-Modell installieren: ${MODEL}"
  if "$OLLAMA_BIN" show "$MODEL" >/dev/null 2>&1; then
    ok "$MODEL bereits installiert"
  else
    info "Gemma 4 12B: 16GB RAM/Unified Memory empfohlen, 256K Kontext. Abbruch ist sicher, erneuter Start setzt fort."
    run "$OLLAMA_BIN" pull "$MODEL"
    ok "$MODEL bereit"
  fi

  step "Memory-Modell installieren: ${EMBED_MODEL}"
  if "$OLLAMA_BIN" show "$EMBED_MODEL" >/dev/null 2>&1; then
    ok "$EMBED_MODEL bereits installiert"
  else
    run "$OLLAMA_BIN" pull "$EMBED_MODEL"
    ok "$EMBED_MODEL bereit"
  fi
fi

step "Lokale Python-Umgebung einrichten"
if [[ ! -d ".venv" ]]; then
  run "$PYTHON" -m venv .venv
fi
run .venv/bin/python -m pip install --upgrade pip
run .venv/bin/pip install -e ".[gui,voice]"
ok "Dependencies installiert"

step "Lokale Datenordner anlegen"
mkdir -p "$HOME/.mimi-nox/memory" "$HOME/.mimi-nox/skills" "$HOME/.mimi-nox/sessions/audio" "$HOME/.mimi-nox/sessions/images"
ok "$HOME/.mimi-nox bereit"

echo ""
echo -e "${GREEN}${BOLD}Setup fertig.${NC}"
echo "Projekt: $PROJECT_DIR"
echo "Start:   .venv/bin/miminox start --open"
echo "Check:   .venv/bin/miminox doctor"
echo "URL:     http://127.0.0.1:${PORT}"
echo ""

if [[ "$NO_START" != "1" && "$DRY_RUN" != "1" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Jetzt starten? [J/n] " reply
    reply="${reply:-J}"
    [[ "$reply" =~ ^[JjYy]$ ]] || exit 0
  fi
  exec .venv/bin/miminox start --port "$PORT" --model "$MODEL" --open
fi

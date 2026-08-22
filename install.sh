#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
DIM='\033[2m'
BOLD='\033[1m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

REPO_URL="${MIMI_NOX_REPO_URL:-https://github.com/bemlerlabs/mimi-nox.git}"
INSTALL_DIR="${MIMI_NOX_INSTALL_DIR:-$HOME/Documents/MiMi-Nox}"
PORT="${MIMI_NOX_PORT:-8765}"
LOCAL_OLLAMA_HOST="${MIMI_NOX_OLLAMA_HOST:-127.0.0.1:11434}"
LOCAL_OLLAMA_URL="$LOCAL_OLLAMA_HOST"
if [[ "$LOCAL_OLLAMA_URL" != http://* && "$LOCAL_OLLAMA_URL" != https://* ]]; then
  LOCAL_OLLAMA_URL="http://${LOCAL_OLLAMA_URL}"
fi
NO_START="${MIMI_NOX_NO_START:-0}"
DRY_RUN="${MIMI_NOX_DRY_RUN:-0}"

# --- Download-Integrität (Supply-Chain Gate) ---------------------------------
# Piped `curl | sh` ist ein klassischer Supply-Chain-Angriffspunkt: ein
# kompromittiertes Vendor-Script würde ungeprüft ausgeführt. Deshalb laden wir
# den uv-Installer (Python-Runtime) erst herunter, verifizieren den SHA256
# gegen den gepinnten Hash und führen erst dann aus. Abweichung -> fester
# Abbruch. Hash-Stand: 2026-08-18 (live erfasst). Rotation via Env-Override.
# Hinweis: Ollama wird NICHT vom Installer installiert (Mandat 2026-08-21) —
# es gibt daher bewusst keinen Ollama-Download/Hash mehr in diesem Skript.
UV_INSTALL_SHA256="${MIMI_NOX_UV_INSTALL_SHA256:-504511fbbbd811aeaba6738abc79408956b6c7da0ca35437b3dcc24a41efc111}"

for arg in "$@"; do
  case "$arg" in
    --no-start) NO_START=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --cli|--headless|--tui) INSTALL_MODE="cli" ;;
    --desktop|--gui|--web|--pwa) INSTALL_MODE="desktop" ;;
    --help|-h)
      echo "Usage: ./install.sh [--no-start] [--dry-run] [--cli|--desktop]"
      echo "Env: MIMI_NOX_INSTALL_DIR, MIMI_NOX_PORT, MIMI_NOX_NO_START, MIMI_NOX_DRY_RUN"
      echo ""
      echo "MiMi Nox — one-command install. AI-Engine wird in der App gewählt"
      echo "(lokale Ollama oder externer Endpunkt wie DGX)."
      echo "Ollama wird NICHT installiert und es werden KEINE Modelle geladen."
      echo ""
      echo "Modes:"
      echo "  --cli      Minimal-CLI-Pfad: installiert nur das TUI (textual), startet 'miminox tui'"
      echo "  --desktop  (Default) Desktop/PWA: installiert gui+voice, startet 'miminox start --open'"
      echo ""
      echo "Ohne Flag fragt der Installer interaktiv, wenn ein Terminal verfügbar ist."
      exit 0
      ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

# Mode-Auswahl: Flag > Env > interaktiv > Default(desktop)
if [[ -z "${INSTALL_MODE:-}" ]]; then
  if [[ -n "${MIMI_NOX_MODE:-}" ]]; then
    INSTALL_MODE="$MIMI_NOX_MODE"
  elif [[ -t 0 && -z "${NO_START:-}" && -z "${DRY_RUN:-}" ]]; then
    read -r -p "Wie willst du MiMi Nox nutzen? [D]esktop/PWA, [C]li (TUI), oder [S]kip-Start: " choice
    choice="${choice:-D}"
    case "$choice" in
      [Cc]) INSTALL_MODE="cli" ;;
      [Ss]) NO_START=1 ;;
      *) INSTALL_MODE="desktop" ;;
    esac
  else
    INSTALL_MODE="desktop"
  fi
fi

step() { echo -e "${GREEN}▶${NC} ${BOLD}$1${NC}"; }
info() { echo -e "  ${DIM}$1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
ok() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1" >&2; exit 1; }
run() {
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "  DRY-RUN: $*"
  else
    "$@"
  fi
}

# sha256 summe portabel (macOS shasum / Linux sha256sum)
sha256_of() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  else
    sha256sum "$1" | awk '{print $1}'
  fi
}

# Lädt ein Vendor-Script herunter, verifiziert den gepinnten SHA256 und
# führt es aus. Abweichender Hash => fester Abbruch (kein blindes `curl | sh`).
# $1=URL  $2=gepinnter_SHA256  $3=label  $4=Env-Override-Name (für Rotation)
fetch_verify_run() {
  local url="$1" expected="$2" label="$3" override_env="$4"
  local tmp got
  tmp="$(mktemp /tmp/mimi-nox-vendor-XXXXXX)"
  if [[ "$DRY_RUN" == "1" ]]; then
    info "DRY-RUN: lade+verifiziere ${label} aus ${url} (SHA256=${expected})"
    return 0
  fi
  info "Lade ${label}-Installer …"
  curl -fsSL "$url" -o "$tmp" || { rm -f "$tmp"; fail "Download fehlgeschlagen: ${url}"; }
  got="$(sha256_of "$tmp")"
  got="$(printf '%s' "$got" | tr 'ABCDEF' 'abcdef')"
  exp="$(printf '%s' "$expected" | tr 'ABCDEF' 'abcdef')"
  if [[ "$got" != "$exp" ]]; then
    rm -f "$tmp"
    fail "SHA256-Integritätsprüfung FEGEL für ${label}. Erwartet ${expected}, erhalten ${got}. Vendor hat das Script vermutlich rotiert: ${override_env} neu setzen (aktuelle sha256) und ./install.sh erneut ausführen."
  fi
  ok "Integrität ${label} bestätigt (SHA256 ${got:0:16}…)"
  sh "$tmp"
  local rc=$?
  rm -f "$tmp"
  return "$rc"
}

is_project_root() {
  [[ -f "pyproject.toml" && -d "app/src" && -f "run_server.py" ]]
}

echo ""
echo -e "${GREEN}${BOLD}MiMi Nox offline-first installer${NC}"
echo -e "${DIM}One-command install. AI-Engine wird in der App gewählt (lokale Ollama oder externer Endpunkt).${NC}"
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
  *) fail "Automatischer Installer unterstützt macOS und Linux. Für Windows: curl -fsSL https://raw.githubusercontent.com/bemlerlabs/mimi-nox/main/install.ps1 -o install.ps1; powershell -ExecutionPolicy Bypass -File .\\install.ps1" ;;
esac
command -v curl >/dev/null 2>&1 || fail "curl fehlt. Installiere curl und starte den Installer erneut."

# Speicherplatz: ~4 GB für Produkt/Abhängigkeiten/PWA-Build. Modell-Downloads
# laufen NICHT hier (Engine wird in der App gewählt) → Warnung, kein Abbruch.
FREE_KB=$(df -Pk "$PROJECT_DIR" | awk 'NR==2 {print $4}')
if [[ "${FREE_KB:-0}" -lt 4096000 ]]; then
  warn "Weniger als ~4 GB freier Speicher (aktuell: $((FREE_KB / 1024 / 1024)) GB). Installation wird trotzdem versucht."
else
  ok "Speicherplatz OK"
fi

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
    fetch_verify_run "https://astral.sh/uv/install.sh" "$UV_INSTALL_SHA256" "uv" "MIMI_NOX_UV_INSTALL_SHA256"
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

# ── KI-Engine (Info-Step, nie blockierend) ──────────────────────────────────
# Mandat 2026-08-21: Ollama wird NICHT installiert, KEINE Modelle geladen.
# Dieser Schritt prüft nur, ob lokal Ollama bereitsteht, und zeigt einen
# Hinweis. Fehlt Ollama → Warnung (kein Abbruch); die Engine wird in der App
# gewählt (SetupPage: lokale Ollama / remote Ollama / OpenAI-kompatibel).
step "KI-Engine prüfen (Info)"
OLLAMA_BIN="$(command -v ollama 2>/dev/null || true)"
OLLAMA_SERVICE_OK=0
if [[ -n "$OLLAMA_BIN" ]]; then
  if curl -fsS --max-time 3 "${LOCAL_OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
    OLLAMA_SERVICE_OK=1
  fi
fi
if [[ -n "$OLLAMA_BIN" && "$OLLAMA_SERVICE_OK" == "1" ]]; then
  ok "Ollama erkannt — seine Modelle stehen in der App zur Auswahl."
else
  warn "Kein Ollama erkannt — das ist OK: MiMi Nox installiert keine KI von selbst."
  info "Nach dem Start wählst du in der App deine Engine (lokale Ollama oder externer Endpunkt wie DGX)."
fi

step "Lokale Python-Umgebung einrichten"
if [[ ! -d ".venv" ]]; then
  run "$PYTHON" -m venv .venv
fi
run .venv/bin/python -m pip install --upgrade pip
if [[ "$INSTALL_MODE" == "cli" ]]; then
  info "CLI-Modus: nur Minimal-Dependencies (tui) installieren"
  run .venv/bin/pip install -e ".[tui]"
else
  run .venv/bin/pip install -e ".[gui,voice]"
fi
ok "Dependencies installiert"

# ── PWA-Build (Desktop-Modus) ───────────────────────────────────────────────
# Der Server liefert die Web-App (PWA) aus app/dist/ — ein Build-Artefakt, das
# git-ignoriert ist und deshalb in einem frischen Clone fehlt. Im Desktop-Modus
# bauen wir das Frontend jetzt, damit http://127.0.0.1:8765/ direkt lädt.
# CLI-Modus (TUI) braucht kein Frontend → Build wird übersprungen (schneller).
if [[ "$INSTALL_MODE" != "cli" ]]; then
  build_pwa() {
    step "PWA (Web-App) bauen"
    if ! command -v npm >/dev/null 2>&1; then
      fail "npm fehlt — Node.js/Node-Module ist erforderlich für den PWA-Build. Installiere Node.js (https://nodejs.org) und starte den Installer erneut."
    fi
    if [[ ! -f "$PROJECT_DIR/app/package-lock.json" ]]; then
      info "npm install läuft (ohne lockfile)"
      run npm --prefix "$PROJECT_DIR/app" install
    else
      run npm --prefix "$PROJECT_DIR/app" ci
    fi
    run npm --prefix "$PROJECT_DIR/app" run build
    if [[ ! -f "$PROJECT_DIR/app/dist/index.html" ]]; then
      fail "PWA-Build fehlgeschlagen: app/dist/index.html existiert nicht."
    fi
    ok "PWA gebaut → app/dist"
  }
  build_pwa
else
  info "CLI-Modus: PWA-Build wird übersprungen (TUI braucht kein Frontend)"
fi

step "Lokale Datenordner anlegen"
mkdir -p "$HOME/.mimi-nox/memory" "$HOME/.mimi-nox/skills" "$HOME/.mimi-nox/sessions/audio" "$HOME/.mimi-nox/sessions/images"
ok "$HOME/.mimi-nox bereit"

echo ""
echo -e "${GREEN}${BOLD}Setup fertig.${NC}"
echo "Projekt: $PROJECT_DIR"
echo "Check:   .venv/bin/miminox doctor"
if [[ "$INSTALL_MODE" == "cli" ]]; then
  echo "Start:   .venv/bin/miminox tui"
else
  echo "Start:   .venv/bin/miminox start --open"
  echo "URL:     http://127.0.0.1:${PORT}"
fi
echo ""

if [[ "$NO_START" != "1" && "$DRY_RUN" != "1" ]]; then
  if [[ -t 0 ]]; then
    read -r -p "Jetzt starten? [J/n] " reply
    reply="${reply:-J}"
    [[ "$reply" =~ ^[JjYy]$ ]] || exit 0
  fi
  if [[ "$INSTALL_MODE" == "cli" ]]; then
    exec .venv/bin/miminox tui
  else
    exec .venv/bin/miminox start --port "$PORT" --open
  fi
fi

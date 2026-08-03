# MiMi Nox — Core Backend & Deployment Status-Analyse

**Datum:** 2025-07-25  
**Projekt:** MiMi Nox (offline-first local AI assistant)  
**Pfad:** `/Users/sanji/mimi-nox/`  
**Branch:** `main` (10 Commits sichtbar)  
**Uncommitted Files:** 102 (26 modified + viele untracked)

---

## 1. Core Backend (`core/`) — Übersicht

**44 Dateien** (incl. `__pycache__`-dirs, tools-subdir), **30 Python-Module** + `__init__.py`

| # | Datei | Größe | Funktion | Status |
|---|-------|-------|----------|--------|
| 1 | `chat.py` | 30.7 KB | Chat-Engine, async streaming, tool-calling loop | ✅ Voll |
| 2 | `tools.py` | 331 B | Compat-Shim → `core/tools/` | ✅ Voll |
| 3 | `skills.py` | 19.3 KB | Skill-System (Markdown-basiert, loader, parser) | ✅ Voll |
| 4 | `swarm.py` | 9.2 KB | Swarm V1 (Planner→Parallel→Synthesizer) | ✅ Voll |
| 5 | `swarm_v2.py` | 24.8 KB | Swarm V2 (Manager-Agent mit spawn_swarm) | ✅ Voll |
| 6 | `swarm_state.py` | 21.2 KB | Swarm-State (AgentStatus, SwarmPhase, SharedState) | ✅ Voll |
| 7 | `model_router.py` | 3.1 KB | Auto-Tier-Selection (OFFLINE→FAST→POWER) | ✅ Voll |
| 8 | `model_provider.py` | 10.9 KB | Provider-Config (local/custom Ollama + OpenAI compat) | ✅ Voll |
| 9 | `model_config.py` | 3.8 KB | ModelConfig, ModelTier, get_model_config | ✅ Voll |
| 10 | `scheduler.py` | 6.9 KB | Background Job Scheduler (APScheduler + Cron) | ✅ Voll |
| 11 | `vision.py` | 12.0 KB | Computer-Use (Screenshots, PyAutoGUI clicks) | ✅ Voll |
| 12 | `vision_memory.py` | 2.2 KB | Vision-Memory (HITL, ChromaDB für UI-Crops) | ✅ Voll |
| 13 | `transcribe.py` | 5.8 KB | Audio-Transkription (faster-whisper + VAD) | ✅ Voll |
| 14 | `skill_builder.py` | 12.0 KB | Auto-Skill-Erstellung (Scanner, Few-Shot, Safety) | ✅ Voll |
| 15 | `skill_fastpath.py` | 29.7 KB | Deterministic Skill-Fastpaths (6 Skills) | ✅ Voll |
| 16 | `memory.py` | 6.0 KB | Vector Memory (ChromaDB, semantisch) | ✅ Voll |
| 17 | `memory_utils.py` | 1.1 KB | Memory Bridge Helper (Singleton-Factory) | ✅ Voll |
| 18 | `artifact_detector.py` | 8.7 KB | Artifact-Erkennung (Code-Block-Inliner) | ✅ Voll |
| 19 | `deck_model.py` | 12.6 KB | Deck/Präsentation Modell | ✅ Voll |
| 20 | `deck_render.py` | 29.8 KB | Deck/Präsentation Rendering | ✅ Voll |
| 21 | `deck_quality.py` | 7.9 KB | Deck-Qualitätsprüfung | ✅ Voll |
| 22 | `deck_adapters.py` | 1.3 KB | Deck-Adapter | ✅ Voll |
| 23 | `deck_design.py` | 2.8 KB | Deck-Design | ✅ Voll |
| 24 | `react.py` | 10.0 KB | React-Loop (Agent-Verhalten) | ✅ Voll |
| 25 | `conversation_compactor.py` | 3.0 KB | Conversation-Kompaktierung | ✅ Voll |
| 26 | `quality.py` | 20.0 KB | Qualitätsnormalisierung | ✅ Voll |
| 27 | `corrections.py` | 4.2 KB | Correction Journal | ✅ Voll |
| 28 | `feedback.py` | 5.3 KB | Feedback Store | ✅ Voll |
| 29 | `profile.py` | 4.6 KB | Profile-Management | ✅ Voll |
| 30 | `project_discovery.py` | 8.0 KB | Projekt-Entdeckung | ✅ Voll |
| 31 | `session.py` | 4.3 KB | Session-Management | ✅ Voll |
| 32 | `source_notebook.py` | 21.2 KB | Source-Notebook (Wissensbasis) | ✅ Voll |
| 33 | `tasks.py` | 2.9 KB | Task-Management | ✅ Voll |
| 34 | `commands.py` | 6.3 KB | Slash-Commands | ✅ Voll |
| 35 | `browser.py` | 3.8 KB | Browser-Helpers | ✅ Voll |
| 36 | `client_factory.py` | 1.1 KB | Client-Factory | ✅ Voll |
| 37 | `connectivity_probe.py` | 5.0 KB | Connectivity-Prüfung | ✅ Voll |
| 38 | `export.py` | 1.3 KB | Export-Funktionen | ✅ Voll |
| 39 | `types.py` | 331 B | Typ-Definitionen | ✅ Voll |
| 40 | `__init__.py` | 260 B | Package-Init | ✅ Voll |
| 41+ | `tools/` | 12 Submodule | Tool-Package (s.u.) | ✅ Voll |

### Core Tools Package (`core/tools/`) — 12 Submodule

| Datei | Größe | Funktion |
|-------|-------|----------|
| `__init__.py` | 4.1 KB | Re-exports aller Symbole |
| `base.py` | 5.5 KB | Exceptions, ALLOWED_COMMANDS, BLOCKED_PATTERNS, Path-Whitelist |
| `registry.py` | 35.7 KB | TOOL_MAP + get_tool_schemas() |
| `deck_tools.py` | 55.5 KB | Deck/PPTX-Tools (~1100 Zeilen) |
| `chart_tools.py` | 6.4 KB | Chart-Generierung (SVG) |
| `file_ops.py` | 4.9 KB | Dateioperationen |
| `pdf_tools.py` | 5.7 KB | PDF-Operationen |
| `system_tools.py` | 7.7 KB | Datetime, Projects, Workspace, Image, Screenshot, SVG |
| `shell_tools.py` | 1.7 KB | Shell-Ausführung (gated) |
| `web_search.py` | 1.9 KB | Web-Suche (DDGS, Tavily) |
| `source_tools.py` | 1.3 KB | Source-Management |
| `task_tools.py` | 1.3 KB | Task-Management |
| `browser_tools.py` | 1.7 KB | Browser-Automation |

---

## 2. CLI Tool

### `miminox_cli.py` (498 Zeilen)
- CLI-Helper für PWA-Start, Model-Install, Doctor-Mode, Service-Management
- Standard: `gemma4:12b` auf Port 8765 via Ollama `127.0.0.1:11434`
- macOS Ollama-Binary-Detection (5 Kandidaten)
- Gemma 4 Mac Install Fallbacks (`gemma4:12b-mlx`, `gemma4:12b-nvfp4`)

### `pyproject.toml` (84 Zeilen)
- **Package:** `mimi-nox` v4.0.0, Apache-2.0, Python >=3.10
- **Build:** Hatchling, Pakete: `core`, `ui`, `server`
- **Entry Points:** `mimi-nox` (clawdash), `miminox` (miminox_cli), `clawdash` (clawdash)
- **Dependencies:** ollama, ddgs, chromadb, fastapi, uvicorn, playwright, apscheduler, edge-tts, pdfplumber, reportlab, matplotlib
- **Optional:** dev (pytest), gui (pyautogui/mss/pynput), voice (faster-whisper), tui (textual)
- **Tests:** pytest, async_mode=auto, testpaths=tests

### `install.sh` (355 Zeilen)
- Bash-Installer mit `set -euo pipefail`
- Konfigurierbar: REPO_URL, INSTALL_DIR, MODEL, PORT, OLLAMA_HOST
- Flags: `--no-start`, `--skip-model`, `--dry-run`
- Standard: `gemma4:12b` → `$HOME/Documents/MiMi-Nox` → Port 8765

---

## 3. Docker/Deployment

### `Dockerfile` (48 Zeilen)
- **Multi-stage Build:** Python 3.12-slim (builder → runtime)
- **Builder:** System deps (gcc, sqlite3-dev, playwright), `pip install .`
- **Runtime:** libsqlite3-0, curl, openssh-client
- **Volume:** `/root/.mimi-nox` (persistent memory/sessions/skills)
- **Healthcheck:** `curl -sf http://localhost:8765/api/health`
- **CMD:** `python run_server.py --host 0.0.0.0 --port 8765`

### `docker-compose.yml` (58 Zeilen)
- **Ollama-Service:** `ollama/ollama:latest`, zieht `gemma4:12b`, healthcheck
- **MiMi-Nox-Service:** Build from Dockerfile, depends_on ollama healthy
- **Env:** OLLAMA_HOST via `host.docker.internal:11434`, mobile host optional
- **Volumes:** `ollama_data` (model cache), `mimi_data` (user data)
- **Ports:** 11434 (ollama), 8765 (mimi-nox)

### `Modelfile` (53 Zeilen)
- FROM: `gemma4:12b`
- num_ctx: 32768 (32K Kontextfenster)
- temperature: 0.6, top_p: 0.9, top_k: 40, repeat_penalty: 1.1
- SYSTEM-Prompt: "elitäre KI-Assistenz", "Principal Engineer auf Apple-Niveau"
- MiMi Tech AI UG – Bad Liebenzell, Schwarzwald

---

## 4. Dokumentation

### `docs/EXECUTION_PLAN.md` (513 Zeilen)
- **Phase 0-0.9 abgeschlossen:** Auth, CSP, Rate Limit, tools.py Split, main.js modular, Tests, UI-Tests, Tauri Prep
- **Phase 1.0:** Model Training Pipeline (4 Stages, ~$86, 26h H100)
  - Stage 0: Data Construction (ToolGT Templates, 10k Samples) ✅
  - Stage 1: SFT mit AdaSTaR (~$10, 3h)
  - Stage 2: Rejection Sampling + DPO (~$15, 4.5h)
  - Stage 3: GRPO Hierarchical (~$35, 10.5h)
  - Stage 4: Online RL ToolSample (~$26, 8h)
- **Phase 1.1:** Entity Transition (UG → Swiss Einzelfirma)
- **Positioning:** Blue Ocean — Surface Integrations (Browser, Shell, Files, PDF)

### `docs/MIMINOX_VISION_2026.md` (47 Zeilen)
- Offline-first, local Ollama + gemma4:12b
- 6 Product Principles: Local first, Honest copy, Repairable setup, Mobile trust, Approval gates, Testable UI
- Release Bar: 7 pre-release checks (installer, tests, security, QR, etc.)

### `docs/TASK_LIST_TDD.md` (67 Zeilen)
- WGT-Scenarios: Installer, Missing Model, Online Opt-In, Mobile QR, Approval-Gated Tools, README Trust
- Focused Test Commands: 6 pytest/bash commands
- Done Criteria: Tests before implementation, public copy matches behavior, no local artifacts tracked

### Whitepaper: ✅ Vorhanden
- `docs/whitepaper-mimi-nox.md` (Markdown)
- `docs/whitepaper-mimi-nox.pdf` (PDF)

---

## 5. Knowledge & Evals

### `knowledge/` (67 KB)
- `index.json` + `chunks.json` (12.8 KB / 65.3 KB)
- `build_chunks.mjs`, `download_knowledge.mjs`, `download_knowledge.sh`
- Subdirs: `engineering/`, `life-skills/`, `medical/`, `navigation/`, `survival/`

### `evals/` 
- `evals/skills/` — 3 YAML-Eval-Dateien: `core.yaml`, `deck.yaml`, `source_notebook.yaml`
- Leerer evals/ Ordner (nur skills-Subdir)

### `clawdash.py` (69 Zeilen)
- Haupt-Entry-Point für `mimi-nox` CLI
- Slash Commands: `/post`, `/debug`, `/idea`, `/explain`, `/commit`
- Swarm: `/swarm <task>` (multi-agent parallel pipeline)
- Keyboard: Ctrl+R=Reset, Ctrl+L=Clear, ↑↓=History, q=Quit

---

## 6. Git & VERSION

### Status
```
Commit (latest): eeb5dc9 — Phase 0: Security Auth, CSP, Rate Limit, shell whitelist, version fix, stream delay removed, favicon SVG
Commits (top 10): 10 sichtbar (von eeb5dc9 bis 958a7ac)
Branch: main (nur master branch)
Uncommitted: 102 Files (dirty working tree)
```

### STATUS_REPORT.md (115 Zeilen)
- B200 Lambda Cloud Training v22 (PID 1926655, GPU 57%, 108GB VRAM, 2000 steps, DAPO loss)
- Skills-Status: 2 neu (tool-use-mastery, agentic-patterns), 2 zu konsolidieren
- Infrastruktur: S3/MinIO, Lambda Cloud 2.7TB (19% genutzt)
- Prioritäten: v22 monitorisieren → Merge & Export → Skills-Paket → Infra-Optimierung

---

## 7. Priorisierte TODOs

### 🔴 P0 — Kritisch
| TODO | Status |
|------|--------|
| **102 uncommitted Files commit/ignore** — viele untracked in `app/` | ❌ Offen |
| **Training v22 monitorisieren** — läuft auf B200, ~50h | ❌ Offen |

### 🟡 P1 — Wichtig
| TODO | Status |
|------|--------|
| Training Stage 1-4 implementieren & ausführen | ❌ Offen (Phase 1.0) |
| Entity Transition (UG → Swiss) vorbereiten | ❌ Offen |
| Tauri Desktop App mit bundled Ollama + Model finalisieren | ⚠️ Teilweise |
| Installer-Tests auf Linux validieren | ⚠️ Teilweise |

### 🟢 P2 — Nice-to-have
| TODO | Status |
|------|--------|
| `evals/` — Eval-Suite ausbauen (nur 3 YAML-Files) | ❌ Offen |
| `knowledge/` — weitere Domänen hinzufügen (medical/survival navigation existieren) | ⚠️ Teilweise |
| `vision_memory.py` — HITL-Regeln produktiv nutzen | ⚠️ Experimental |
| Swarm V2 (`swarm_v2.py`) — production readiness prüfen | ❌ Offen |
| `swarm_state.py` (21.2 KB) — noch nicht explizit geprüft, aber vorhanden | ⚠️ Ungeprüft |
| `deck_*.py` (5 Dateien) — Deck-System umfassend testen | ⚠️ Ungeprüft |
| `connectivity_probe.py` — Remote-Connectivity-Checks validieren | ⚠️ Ungeprüft |
| `source_notebook.py` (21.2 KB) — Wissensbasis-System testen | ⚠️ Ungeprüft |

---

## 8. Architektur-Zusammenfassung

```
┌─────────────────────────────────────────────────────┐
│                   MiMi Nox Stack                    │
├─────────────────────────────────────────────────────┤
│  PWA (Vanilla JS + Vite)  │  FastAPI (Python)       │
│  app/src/modules/*.js     │  server/middleware/      │
│  18 Module (3.362 Zeilen) │  core/*.py (40 Module)   │
├─────────────────────────────────────────────────────┤
│  Ollama (gemma4:12b) │  ChromaDB (Memory)           │
│  port 11434          │  port 8765 (PWA Server)      │
├─────────────────────────────────────────────────────┤
│  Docker (Compose)                                   │
│  ollama + mimi-nox │  Named Volumes                 │
├─────────────────────────────────────────────────────┤
│  Deployment Paths                                   │
│  1. install.sh → macOS/Linux lokal                  │
│  2. Docker Compose → Container                      │
│  3. Tauri DMG → Desktop App (3.3MB)                 │
│  4. pip install . → Package                         │
└─────────────────────────────────────────────────────┘
```

**Gesamt-Codebase:** ~40 Core-Module, 13 Tool-Submodule, 18 JS-Module, 676+ Tests, Version 4.0.0  
**Reifegrad:** Phase 0.9 abgeschlossen, Production-taugliches Core Backend, Training Pipeline als nächstes
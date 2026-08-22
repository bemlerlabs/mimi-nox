# Changelog

Alle wesentlichen Änderungen an **MiMi Nox** werden hier dokumentiert.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased] – 2026-08-21

### Changed — Installer-Mandat: warn-only (kein Ollama-Install, kein Modell-Pull)

Gemäß Founder-Mandat (2026-08-21, mehrfach bekräftigt) ist der Installer **nicht** mehr
verantwortlich für die AI-Engine. Der One-Command-Install bleibt einwandfrei für das
Produkt selbst (Python-Runtime via uv mit SHA256-Verifikation, PWA-Build, Datenordner,
Server-Start). Die AI-Engine wählt der **End-User** selbst in der App:

- **`install.sh` / `install.ps1`:** Ollama-Autoinstallation + Modell-Pull
  (`gemma4:*`, `nomic-embed-text`) entfernt. Stattdessen: **warn-only** — der Installer
  erkennt eine lokal bereits installierte Ollama (informational) und zeigt an, dass die
  Engine in der App gewählt wird. Kein Ollama-Download mehr, dadurch auch kein
  `OLLAMA_INSTALL_SHA256` mehr (nur `UV_INSTALL_SHA256` für den Python-Installer bleibt).
- **PWA `SetupPage.tsx` (neu):** First-Run-Engine-Auswahl in der App — lokale Ollama,
  remote Ollama (z. B. DGX/LAN), oder OpenAI-kompatibler Endpunkt — mit Live-Probe gegen
  `/v1/models` und Modell-Auswahl. Persistenz unter `~/.mimi-nox/engine.json`.
- **`tests/test_installer_cli.py`:** 9 veraltete Ollama-Install/Pull-Tests durch neue
  Tests des warn-only-Vertrags ersetzt (31/31 grün).

### Fixed

- **DGX-Modell-Drift (Root-Cause):** `core/engine_config.py::DEFAULT_DGX_SPARK_MODEL`
  von `qwen38-27b-unsloth-nvfp4` → `qwen3.8-27b` — die alte ID existiert auf dem
  Live-DGX nicht mehr (verifiziert via `/v1/models`, `max_model_len=262144`). Weitere
  3 Referenzen (ui/app.py, 2 Tests) synchron angepasst.
- **Test-Pollution (Root-Cause, 11 Failures):** `tests/conftest.py` bekommt ein
  `autouse`-Isolations-Fixture — snapshot/restore von `os.environ` und
  `core.model_provider._ACTIVE_OVERRIDE` pro Test. Stellt hermetische Testsicherung
  für die gesamte Provider-Pollution-Klasse her (statt Symptome einzeln zu patchen).
- **CI-Python-Matrix (2 Failures):** `.github/workflows/tests.yml` nutzt jetzt
  `strategy.matrix.python-version: ['3.10','3.11','3.12','3.13']` (Untergrenze =
  `requires-python`) — löst den Hygiene-Test-Paritäts-Verstoß.

### Security / Hygiene

- **Frontend-Lint-Härtung:** 4 ESLint-Errors fixt (`no-self-assign` in
  composerHistory, `no-empty-object-type` in Input, `no-unused-vars` in
  WorkspaceSidebar-Test, `@ts-ignore`→`@ts-expect-error` in Button) + 4
  `react-hooks/exhaustive-deps`-Warnings in ChatLayout (root-cause: `sendViaApi`
  ungebunden + fehlende `setPendingToolCall`-Deps). `npm run lint` → exit 0.
- **Toter Re-Export entfernt:** `SetupPage.tsx` re-exportierte `getSetupStatus`
  (Funktion aus `lib/api`), den niemand von dort importierte (App.tsx nutzt den
  `lib/api`-Import direkt). Removed → löst `react-refresh/only-export-components`.

---

## [1.0.0-sprint2] – 2026-08-19

### Added – Sprint 1 Launch-Trust (P0-1 / P0-2 / P0-3)

- **`miminox tool` — Approval-Gates (P0-1, Threat-Model E1):** deterministischer Tool-Modus (ohne LLM-Loop) mit konservativen Defaults. `SAFE` Tools (read-only) immer erlaubt; `MUTATING`/`NETWORK` Tools erfordern explizite Freigabe. Flags: `--dry-run` (Vorschau, Datei bleibt unangetastet), `--yes` (Freigabe), `--no` (Ablehnung), `--arg K=V` (JSON-parsed), `--json` (maschinenlesbar). Exit-Codes: 0 = ausgeführt/dry-run, 3 = durch Policy blockiert, 2 = Usage. `core/tools/approval.py` + 20/20 approval-Tests (e2e: dry-run/yes/no/non-interactive).
- **Qwen 3.8 27B auf DGX Spark als Standard-Engine (P0-2):** `core/engine_config.py::default_engine_choice()` — Mimi Tech AI Standard-Engine (Qwen 3.8 27B, `qwen38-27b-unsloth-nvfp4`), kein Ollama-Bundling/Download. Provider-Wahl (eigener Endpoint, Ollama, OpenRouter) = END-USER-Onboarding via `miminox tui --configure`. Persistenz unter `~/.mimi-nox/engine.json`; explizite `--model`/`--api-url`-Flags gewinnen immer; API-Keys werden nie persistiert. 22 passed inkl. 3 LIVE DGX-Smoke-Tests.
- **Security Release Gate (P0-3):** `docs/SECURITY_GATE_REPORT.md` — 0 install-hygiene-Treffer, `npm audit` = 0, Lighthouse 7/7 Security-Audits = 1.0.

### Added

- **`miminox serve`** — OpenAI-kompatible Engine (Phase 3): `server/openai.py` (`create_openai_app`: `/v1/models`, `/v1/chat/completions` mit SSE-Stream + `[DONE]`, Auth-Token, localhost-Bind default); `cmd_serve` (`--host/--port/--lan/--token/--model`, `--lan` generiert Token, `0.0.0.0`). JCode/Codex/OpenCode nutzen die Engine als OpenAI-Provider (Interop, e2e: `tests/test_jcode_e2e.py`).
- **Hardware-adaptiver Model Router** (`core/model_router.py`): single source of truth für `gemma4:12b ↔ ds4`, transparent pro Session + `X-Model-*` Transparenz-Header; Router in serve verdrahtet (fehlendes Modell → resolve, explizites Modell → skip).
- **Engine-Start/Onboarding für `miminox tui`**: Default = Qwen-DGX-Standard-Engine (Sprint 1); `--configure` startet das END-USER-Onboarding (Ollama / eigener Endpoint / OpenAI-kompatibel); Auswahl persistiert nach `~/.mimi-nox/engine.json`, explizite Flags gewinnen immer.
- `core/engine_config.py`: `EngineChoice` + atomare `load/save/clear_engine_config`; API-Keys werden nie persistiert (nur Session-Env).
- **Observability** (Phase 4, Item 15): `core/observability.py` — Request-ID-Middleware (`X-Request-ID`), strukturierte Error-Payloads mit stabilen `code_id` (usage/validation/auth/stream/runtime/not_found), HTTP-Exception-Handler; in `miminox serve` (OpenAI-Engine) UND im PWA-Server (`server/main.py`) verdrahtet. Tests: `tests/test_observability.py` (11 Tests).

### Security

- **install.sh: SHA256-Supply-Chain-Integrität (P0-2):** alle Vendor-Downloads (uv, Ollama-Installer) werden vor Ausführung gegen gepinnte SHA256-Hashes verifiziert — Abweichung bricht den Installer fest ab (kein blindes `curl | sh`). Rotation via `MIMI_NOX_UV_INSTALL_SHA256` / `MIMI_NOX_OLLAMA_INSTALL_SHA256`.
- **Docker Compose: LAN-Auth aktiv by default** (`MIMI_NOX_LAN=1`) — Container bindet auf die Host-Interface, dadurch wird Auth-Token + Security-Header + Rate-Limit aktiviert (konservativ: nie offenes LAN-Hosting ohne Auth).

### Planned

- Multi-Session-Verwaltung (parallele Chats)
- Plugin-API für externe Skill-Pakete
- Lokales Embedding-Modell (statt ChromaDB default)

---

## [4.0.0] – 2026-04-03

### Added – Artifacts Panel
- `core/artifact_detector.py`: Regex-Engine erkennt Code-Blöcke (≥ 5 Zeilen) in LLM-Output automatisch
- 14 Sprachen unterstützt: Python, Bash, JS/TS, Rust, Go, SQL, HTML, SVG, JSON, YAML, Diff, Markdown
- `app/src/artifact.js`: `ArtifactStore` (Versionierung) + `ArtifactPanel` (Sliding Side Panel)
- Panel-Features: Syntax-Highlighting (highlight.js), HTML-Preview (sandboxed iframe), Copy/Download, Drag-to-Resize (320–800px), Session-Verlauf als Navigations-Dots
- SSE-Events: `artifact` und `replace_text` in der Chat-Stream-Pipeline
- `main.js` auf ES-Module (`type="module"`) umgestellt
- TDD-Suite: 11 BDD-Tests (Given-When-Then) in `tests/test_artifact_detector.py`

### Added – Visual Computer Use
- `core/vision.py`: `vision_click` und `vision_type` (PyAutoGUI + Llama-Vision)
- Screenshot → Koordinaten-Berechnung → Maus-Klick-Ausführung
- HITL (Human-in-the-Loop) Lernmodus: bei Unsicherheit nach manuellem Klick fragen
- `core/vision_memory.py`: Koordinaten-Lerngedächtnis per Element-Label

### Added – Headless Browser
- `core/browser.py`: Playwright-Integration (Chromium, headless)
- Cookie-Banner-Erkennung via Vision + automatische Akzeptierung
- 15.000-Zeichen-Truncation gegen OOM/Context-Flooding
- `PlaywrightBrowserManager`: Singleton mit Concurrency-Safety

### Added – Hintergrund-Scheduler
- `core/scheduler.py`: APScheduler-Integration (cron-basiert, persistent)
- `server/routes/schedule.py`: REST-API (`/api/schedule`)
- Job-Ergebnisse persistent in `scheduled_jobs.json`
- Bugfix: Route-Reihenfolge `/results` vor `/{job_id}` (verhindert Konflikte)

### Added – PWA & Mobile
- `manifest.json`: Dark-Theme (`#020504`), Shortcuts, Display-Overrides
- `service-worker.js` v5: Cache-First für Statics, Network-Only für API/Audio
- Auto-Update-Mechanismus: "🔄 Jetzt aktualisieren"-Toast bei neuem SW
- Mobile Zen-Modus: CSS `mobile-pwa-mode` blendet Desktop-UI auf `≤768px` aus
- QR-Code-Pairing mit Desktop-Bestätigungs-Toast
- PWA-Icons: echte PNG-Icons (192×512px)

### Added – Voice UX
- `core/transcribe.py`: Faster-Whisper STT (lokal)
- `/api/audio/transcribe`: WAV-Upload → Transkript
- `/api/audio/tts`: Native macOS-TTS (kein Cloud)
- Walkie-Talkie-Modus: Automatisches Vorlesen nach Voice-Input
- Waveform-Visualisierung während Aufnahme

### Added – Skills CRUD
- `server/routes/skills.py`: GET/POST/PUT/DELETE `/api/skills`
- Skills-Tab im Browser: GUI-Editor für eigene Skills
- `core/skill_builder.py`: Auto-Skill-Generierung via `/learn <Thema>`
- Skill-Chips im Chat-Bereich (klickbar → Trigger in Input)

### Fixed
- `main.js` `_queryElements()`: fehlende `chatArea`- und `bottombar`-Referenzen → Crash aller Event-Handler auf Desktop behoben
- Null-Guards für alle optionalen DOM-Elemente in `_bindEvents()`
- Service Worker Cache-Invalidierung: automatischer Versionsbump erzwingt saubere Aktualisierung

---

## [3.1.0] – 2026-04-02

### Added
- Web-Interface als primäres Frontend (FastAPI + HTML/JS/CSS)
- SSE-Streaming-Endpunkt (`POST /api/chat/stream`)
- ReAct-Loop mit Reflexion (automatische Qualitätsprüfung + Revision)
- ChromaDB Vektorspeicher (semantisches Langzeitgedächtnis)
- User-Profil (Name, Expertise, Sprache, Kommunikationsstil)
- Fehler-Journal (`core/corrections.py`)
- 👍/👎 Feedback-Store (`core/feedback.py`)
- Thinking-Mode-Visualisierung (Gemma 4 native reasoning)
- Swarm-Pipeline: `/swarm` Multi-Agent-Ausführung
- Mobile-Pairing-Modal mit QR-Code

### Architecture
- Single-Codebase: `core/` vollständig UI-unabhängig
- FastAPI-Server als dünner SSE-Layer über `core/`
- Frontend kommuniziert ausschließlich via REST/SSE

---

## [3.0.0] – 2026-04-01

### Added – ClawDash v3 BlackForest Edition (Initial Release)
- Async-Streaming via Ollama AsyncClient
- TUI-Frontend (Textual): `HistoryInput`, `ChatView`, `StatusBar`
- Slash-Commands: `/post`, `/debug`, `/idea`, `/explain`, `/commit`
- Erweiterbare Command-Registry (`COMMANDS` Dict in `core/commands.py`)
- Session-Persistence mit atomic writes (`tmpfile + rename()`)
- `--model` und `--reset` CLI-Flags
- Schwarzwald-Edition-Farbpalette (`#39ff14` auf `#080b08`)
- `Message` TypedDict als Shared-Contract zwischen allen Modulen
- `pytest-asyncio`-Test-Suite (`asyncio_mode = auto`)

### Architecture
- Modulare Struktur: `core/` (rein async, kein UI) + `ui/` (Textual)
- Workers kommunizieren via `post_message()` (thread-safe)

---

*MiMi Tech AI UG – Bad Liebenzell, Schwarzwald*  
*No cloud. No tracking. Straight from the Black Forest. 🌲*

# MiMi Nox — Kompletter Audit & Vergleichsanalyse (Hermes + OpenClaw + OpenCode/OpenClone/Pi)

**Datum:** 2026-08-07 | **Git:** `039b79f` | **Status:** Audit-Phase — noch keine Implementierung
**Methode:** 3 parallele Analyse-Agents (Hermes-Doku, Coding-Agent-Ökosystem, MiMi-Codebase) via Live-Transcript-Fallback (Sub-Agents timeout-ten nach 3600s; Befunde aus Transkripten + Rohdaten extrahiert).

---

## 1. Feature-Inventar MiMi Nox (IST, mit Belegen)

### Backend — Agent-Stack (bereits sehr stark, die Basis für den Coding-Agent)
| Baustein | Beleg |
|---|---|
| ReAct-Loop mit Reflexion/Selbstkorrektur (MAX_REVISIONS=2) | `core/react.py` (280 Zeilen) |
| Tool-Registry, 20+ Tools | `core/tools/registry.py` |
| Shell-Tool mit Sicherheits-Whitelist + BLOCKED_PATTERNS + Timeout | `core/tools/shell_tools.py` |
| File-Tools (file_search/read_file/list_directory, MAX_FILE_CHARS) | `core/tools/file_ops.py` |
| Lokale Projekt-Erkennung (Marker-Gewichte) | `core/project_discovery.py` |
| Multi-Agent-Swarm-Pipeline (`/swarm <task>` — Planer + parallele Agents) | `core/swarm.py` |
| Skills, Memory (mit Query), Feedback | `core/skills.py`, `core/memory.py`, `core/feedback.py` |
| Model-Config (3 Tiers: OFFLINE/FAST/POWER, RAM-adaptiv) | `core/model_config.py` |
| Browser-Automation (vision_click/type/go/screenshot) | `core/tools/browser_tools.py` |
| Deck/PDF/Chart-Generierung (Pitch-Deck, PPTX, PDF) | `core/tools/deck_tools.py`, `pdf_tools.py`, `chart_tools.py` |
| Server-Routen (chat, tasks, skills, vision, memory, audio, schedule, model_provider) | `server/routes/*.py` |
| CLI: start/doctor/update/tui | `miminox_cli.py:453,470-496` |
| Installer: One-Liner + RAM-adaptives Modell | `install.sh:12-25,90,153,244,301`, `install.ps1` |

### Frontend (React 19 + Vite + TS)
| Baustein | Beleg |
|---|---|
| Sessions persistiert in IndexedDB (nicht localStorage) | `chatStore.ts:57-67,105`, `lib/db.ts` |
| Session-Switch/Create/Delete | `chatStore.ts:80,95` |
| Onboarding-Wizard (ollama-check → model-pull → welcome) | `OnboardingWizard.tsx:7,64,100` |
| Chat-Split, Code-Highlight, Tool-Call-Display, AttachmentPreview | `ChatLayout.tsx`, `MessageBubble.tsx` |
| Landingpage (Hero, Features, CTASection, Plattform-Karten + One-Liner) | `components/landing/*` |

---

## 2. Hermes-Referenz (Feature-Matrix aus Doku `/tmp/hermes-docs/llms-full.txt`)

### Install-Flow (exakte Befehle)
```bash
# macOS/Linux/WSL2/Android
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
# Windows (native)
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
# Desktop nach CLI-Install
hermes desktop
```
**Kern:** Installer macht alles automatisch (Python, Node, ripgrep, ffmpeg, Repo-Clone, venv, globales `hermes`-Binary, LLM-Provider-Config). → **GAP A1/A2 bei uns: kein CLI-vs-Desktop-Wahl, kein Windows-One-Liner.**

### Desktop-UI (chat-first)
- **Linke Sidebar** für Navigation
- **Rechte Preview-Rail** — Web-Pages/Files/Tool-Outputs side-by-side beim Chatten → **GAP B1 (uns fehlt komplett)**
- **Artifacts** — Dateien/Worktrees/Preview (eigenes Konzept) → **GAP B1**
- **Timeline-Rail** — schmale Marker-Leiste am Transkript-Rand, hover → Prompt-Liste, klick → Jump-to-Point → **GAP B2 (neu)**
- **Composer-History & Queue-Editing** — ↑/↓ recall, Queue edit/pause/resume → **GAP B3 (neu)**
- **Find in page** — Cmd/Ctrl+F im gerenderten Transcript → **GAP B4 (neu)**
- **Status-Bar** — per-Session YOLO-Toggle, Context-Meter (% full, token-breakdown), custom Items → **GAP B5 (neu)**

### Agent-System
- Sub-Agents/Delegation (`delegate_task`, isolierter Kontext + Tools) → **uns: swarm.py vorhanden, aber UI/CLI-Zugang fehlt**
- Agent-created Skills (`skill_manage`) → uns: skills.py vorhanden
- Persistent Memory über Sessions → uns: memory.py vorhanden
- **MCP** (Model Context Protocol — externe Tool-Server) → **GAP C (fehlt)**
- **Messaging Gateway** (21+ Plattformen: Telegram, Discord, Slack, SMS, Matrix…) → **GAP D (fehlt komplett)**
- **Cron** (recurring Agent-Tasks) → uns: schedule.py-Route vorhanden, aber kein Cron-Frontend
- **Checkpoints & Rollback** (Sicherheit) → **GAP E (fehlt)**
- **YOLO-Mode** (per-session auto-approve, mit Warnung) → uns: Tool-Approval existiert, YOLO fehlt

---

## 3. Coding-Agent-Ökosystem (OpenClaw / OpenCode→Crush / Pi)

| Projekt | Sterne (GitHub) | Kern | Relevanz |
|---|---|---|---|
| **OpenClaw** | ~385k | Persönlicher AI-Assistant, Gateway auf eigenen Geräten, Channels (WhatsApp/Telegram/Slack/Discord/…), Companion-Apps (voice/canvas/camera/screen), `openclaw onboard --install-daemon` | Gateway-Konzept validiert |
| **OpenCode → Crush** | OpenCode archiviert; Crush ~27k (Go) | Agentic Coding CLI, Glamourous UI, **MCP-Support (http/stdio/sse)**, LSP, Multi-Model | MCP ist Standard → GAP C |
| **Pi (earendil-works)** | ~85k (TypeScript) | AI-Agent-Toolkit: unified LLM API, Agent-Loop, TUI, **Coding-Agent-CLI** | Best-Practice für Coding-Agent-CLI |

**Strategische Erkenntnis:** Lokale/offline Coding-Agents sind der 2026er-Trend. MCP ist der De-facto-Standard für Tool-Integration. Gateway-Multi-Platform ist der Differenzierungs-Trend (OpenClaw).

---

## 4. Gap-Analyse & priorisierter Implementierungs-Plan

### P2 — Hermes-Parity (schließt die größten Lücken, Reihenfolge nach Impact)
| # | Gap | Maßnahme | Ziel |
|---|---|---|---|
| **P2-1** | **Rechte Preview-Rail + Artifacts fehlen** | Persistentes Right-Panel: Sessions-Liste, Artifact-Ansicht (Dateien/Worktrees/Preview), Split-View im Chat | Kern-Hermes-Feature |
| **P2-2** | **CLI-vs-Desktop-Wahl im Installer** | `--cli`/`--desktop`/`--gui`-Flags + interaktive Wahl, Minimal-CLI-Pfad ohne `[gui,voice]` | One-Line-Install wie Hermes |
| **P2-3** | **Windows-One-Liner** | `curl \| powershell`-Bootstrap + RAM-Erkennung in `install.ps1` | Windows-Parity |
| **P2-4** | **MCP-Client** | MCP-Server-Anbindung (http/stdio/sse) ins Tool-Registry | Standard-Tool-Integration |
| **P2-5** | **Context-Meter + Status-Bar** | Live %-full-Meter, Token-Breakdown, YOLO-Toggle | Hermes-Parity |
| **P2-6** | **Timeline-Rail + Composer-History** | Marker-Leiste + ↑/↓ Recall + Queue-Editing | Hermes-Parity |
| **P2-7** | **Checkpoints & Rollback** | Snapshot/Rollback für Sessions | Sicherheit |
| **P2-8** | **Cron-Frontend** | schedule.py → UI für recurring Tasks | Hermes-Parity |

### P3 — Differenzierung (eigener Coding-Agent + Gateway)
| # | Maßnahme | Ziel |
|---|---|---|
| **P3-1** | **Coding-Agent-CLI** (nach Pi/OpenCode-Vorbild) | Terminal-basierten Agent auf react.py + Registry |
| **P3-2** | **Gateway-Multi-Platform** (nach OpenClaw) | Telegram/Discord/Slack/SMS-Channels, Companion-Apps (voice/canvas) |
| **P3-3** | **Swarm-UI-Zugang** | `/swarm` ins Frontend bringen (Multi-Agent-Visualisierung) |
| **P3-4** | **Skill-Auto-Creation** (nach Hermes `skill_manage`) | Agent-created Skills über UI |

---

## 5. Transparenz & Validierung
- Sub-Agents timeout-ten nach 3600s → Befunde aus Live-Transcripts + gesammelten Rohdaten extrahiert.
- Hermes-Befunde direkt aus `llms-full.txt` (3.5MB) verifiziert; GitHub-Sternzahlen aus API-Responses der Transkripte.
- **Keine Implementierung vor Design-Freigabe** (Brainstorming-Gate per Projektregel).

# 🚀 MiMi Nox — Open-Source Launch Playbook (2026)

> **Ziel:** Launch diese Woche / nächste Tage als öffentliches Open-Source-Startup (50M+ Vision).
> **Methode:** Evidenzbasiert — jeder Befund aus Repo/GitHub/Training verifiziert, jede Empfehlung mit Begründung + Quelle.
> **Stand:** 2026-08-02 · Git `main` (ahead 2) · GitHub-Repo `MimiTechAi/mimi-nox` (public).

---

## 0. Executive Summary

MiMi Nox ist **funktionsfähig und public**, aber unsichtbar: GitHub-Repo hat **1 Star, 0 Forks, 2 Watchers, keine Description, letzter Push 2026-06-05** (2 Monate). Es wurde **keine Werbung gemacht**. Das Kern-Asset — das **tool-optimierte Gemma-Modell `MimiTechAi/miminox-stage4-e4b`** — ist auf HF hochgeladen, aber das Training (`stage4 GRPO v22`) ist bei Step **742/2000 BLOCKED** (NaN-Instabilität, fehlendes Remote-Dataset + Checkpoint, CUDA-Mismatch).

**Die Launch-These:** Der Markt (OpenClaw: 150k Stars in 10 Wochen) zeigt — ein **lokal laufender, offline-first, tool-fähiger AI-Assistant mit eigenem fein-tunablem Modell** ist genau das, was 2026 skaliert. MiMi Nox hat die Bausteine. Der Weg: **P0-Blocker räumen → Repo launch-ready machen → gezielter Go-to-Market (Show HN + Product Hunt + X) → Modell-Training finalisieren als Feature-Hook.**

---

## 1. IST-ZUSTAND (verifiziert)

### 1.1 GitHub-Repo (öffentlich) — [API-Check 2026-08-02]
| Metrik | Wert | Beleg |
|---|---|---|
| Stars | **1** | GitHub API `stargazers_count` |
| Forks | **0** | GitHub API |
| Watchers | **2** | GitHub API `subscribers_count` |
| Description | **keine** | GitHub API `description: None` |
| Created | 2026-04-03 | GitHub API |
| Letzter Push | **2026-06-05** (2 Monate) | GitHub API `pushed_at` |
| Workflows | `frontend-build.yml`, `tests.yml` | `.github/workflows/` |

**Befund:** Repo existiert seit April, aber keiner weiß davon. Kein Description, kein About, kein Release, kein Trailer. Der „Beobachter" mit Ahnung kann nur auf eine stille Repo schauen.

### 1.2 Repo-Zustand (Working Tree) — `git status --short`
- **80 Dateien untracked** (gesamte React-App `app/src/`, `core/`, `server/`, Tauri-Rust-Quellen, Whitepaper-PNGs/PDF)
- **17 modified, 21 deleted**
- Getrackt: `v2` 114, `tests` 65, `core` 40, `skills` 27, `app` 25, `server` 17, `docs` 16, `knowledge` 15, `.github` 5, `ui` 4, `scripts` 3, `evals` 3, `utils` 2 + Root-Singles
- **Hygiene ✅:** 0 getrackte Hygiene-Dateien (`node_modules`, DB, WAL/SHM, Secrets, Caches)

**Befund:** Der eigentliche Produkt-Code (`app/`, `core/`, Tauri-Rust) ist **nicht versioniert**. Nur `src-tauri/tauri.conf.json` ist getrackt. → Build nicht reproduzierbar, kein sauberer Release.

### 1.3 Frontend (React PWA) — [aus vorheriger 3-Kopf-Analyse, verifiziert]
- **Build ✅** `npm run build` exit 0, **3225 Module** transformiert; `tsc --noEmit` exit 0 (keine Typ-Fehler)
- **Bundle 🔴 P0:** Haupt-Chunk **860.21 KB (gzip 267.92 KB)** — über der 500-KB-PWA-Schwelle; CSS 69.30 KB (gzip 11.13 KB), Source-Map 4.37 MB
- **State:** `chatStore.ts` (zustand) ohne Streaming-Logik; Streaming/`onChunk` in `ChatLayout.tsx`; Store persistiert via IndexedDB (`db.ts`, debounced)
- **Backend-Connect ✅ echte Produktion:** `ChatLayout.tsx` → `WSClient(useRef)` + `connect()` + `sendMessage(...)` mit `onChunk`; `api.ts` → `POST /api/chat/send` SSE-Parse; `websocket.ts` → `ws://localhost:8765/ws/chat` + Reconnect + Tool-Approval-Callback
- **Dead-Code ⚠️ P1:** `api.ts` (`getSessions/createSession/deleteSession/getMessages`) nirgends aufgerufen — Sessions laufen client-seitig via IndexedDB
- **PWA ✅** manifest/icon/favicon/SW in `main.tsx` registriert
- **SW-Duplikat ⚠️ P1:** `public/service-worker.js` (statisch) UND `src/service-worker.ts` (kompiliert) → Risiko veralteter Cache-Keys

### 1.4 Backend / Core
- **venv 🔴 P0:** `.venv` = **Python 3.9.6** vs `pyproject.toml requires-python >=3.10` → Mismatch
- **Lokale Tests 🔴 P0:** nicht lauffähig — kein `pytest` im venv, `import ollama` → ModuleNotFoundError
- **Security ✅ konservativ:** Binding `127.0.0.1:8765`; LAN `0.0.0.0` nur via `--lan` opt-in; `AuthMiddleware` schützt alle `/api/*` (außer health); CSP-Header + `RateLimitMiddleware` (60 req/min/IP) nur im LAN-Mode
- **Tool-Safety ✅ strict:** `ALLOWED_COMMANDS`-Whitelist (`ls/cat/python/git/docker/…`) + `BLOCKED_PATTERNS` (`rm -rf`, `sudo`, `shutdown`, `| sh`, `> /`, …) + `ALLOWED_ROOTS`-Restriktion
- **Modell-Integration ✅:** `model_provider.py` unterstützt `local_ollama` / `custom_ollama` / `openai_compatible`; `DEFAULT_LOCAL_MODEL = "gemma4:12b"`; Env `MIMI_NOX_MODEL`, `MIMI_MODEL_PROVIDER`, `MIMI_OPENAI_COMPAT_BASE_URL`

### 1.5 Modell-Training (Kern-Asset)
| Status | Detail |
|---|---|
| **Modell** | `MimiTechAI/miminox-stage4-e4b` — Gemma-4-7.9B-it, LoRA dim=32 alpha=64, **auf HF hochgeladen & bereit** |
| **Training** | `stage4 GRPO v22` — **BLOCKED bei Step 742/2000** (SIGTERM-Kill, keine Checkpoints gerettet) |
| **Dataset (remote)** | `/home/ubuntu/miminox-data/…curated_v2.jsonl` (6228 Samples) — **existiert NICHT auf H100** |
| **Checkpoint-Basis (remote)** | `/home/ubuntu/checkpoints/stage4_grpo_v15_fp32_lora_merged_fixed` — **existiert NICHT** |
| **Stabilität** | **Kritisch:** negative Losses (−0.25), KL-Spitzen (bis 4746), Grad-Norm-Spitzen (4.75e6), Completion-Collapse (2048-Token-Clipping bei `clipped_ratio=1.0`) |
| **GPU (H100)** | ✅ frei (0 MiB, 0% util) — Lambda Cloud |

**Befund:** Das Modell existiert und ist public. Aber das RL-Training, das es „perfekt für Tool-Calls" machen soll, ist **stabilisierungsbedürftig und remote-blockiert**.

---

## 2. Die Launch-These (evidenzbasiert)

**Warum dieser Markt:**
- OpenClaw (Open-Source AI-Assistant, lokal, keine Server-Daten): **9k Stars am Launch-Day (Jan 2026) → 150k Stars in 10 Wochen**, 416k npm-Downloads. [Quelle: arturmarkus.com, medium.com/aftab001x, techriseups]
- GitHub Octoverse 2025: **4.3M AI-Repos, +178% YoY bei LLM-Projekten** — der Agentic-AI-Space skaliert massiv. [Quelle: ODSC/Medium]
- **Positionierungs-Gap:** Die meisten lokalen Agenten nutzen kleine Modelle, die in Tool-Use schwach sind. MiMi Nox' Differenzierung ist **ein fein-getuntes Gemma-4-Modell, das lokal auf dem Mac läuft** und für Tool-Calls optimiert wird. Das ist ein „bespoke function-calling to the edge"-Narrativ (siehe Googles FunctionGemma 270M, Dec 2025). [Quelle: blog.google, ai.google.dev]

**Die 3 Moves:**
1. **P0-Blocker räumen** (venv, Bundle, Versionierung) → Repo launch-ready.
2. **Repo public ausstellen** (Description, About, Release, README-CI-Badge, Demo-GIFs).
3. **Go-to-Market:** Show HN (technical audience) + Product Hunt (day-one visibility) + X/LinkedIn (founder reach). Das fein-getunte Modell ist der Feature-Hook.

---

## 3. Nächste logische Schritte (Wochen-Plan)

### Woche 1 — „Launch-ready" (2–3 Tage, P0 zuerst)

| # | Aufgabe | Begründung | Quelle |
|---|---|---|---|
| 1 | **venv rehabilitieren:** `.venv` auf Python ≥3.10 neu bauen (`python -m venv .venv`, `pip install -e ".[dev]"`), `pytest` + `ollama` installieren | P0: Lokale Tests lauffähig = Qualitäts-Gate vor public Release | `pyproject.toml` requires-python ≥3.10 |
| 2 | **Backend-Tests grün:** `pytest tests/test_installer_cli.py tests/test_offline_first_positioning.py tests/test_repo_hygiene.py` + Security/Offline-Tests | Release-Bar: CI-safe pytest-Subset | AGENTS.md Release-Bar |
| 3 | **Bundle splitten:** `manualChunks`/Lazy-Routing für React, Radix, framer-motion → Haupt-Chunk < 500 KB | P0: PWA-Performance-Schwelle; 860 KB→268 KB gzip ist zu groß für „instant load" | Vite docs; PWA-Budgets |
| 4 | **Versionierung sichern:** `app/`, `core/`, `server/`, Tauri-Rust, Whitepaper committen | P0: Build reproduzierbar, sauberer Release, Contributor-Basis | `git status --short` 80 untracked |
| 5 | **SW-Duplikat auflösen:** eine Quelle (`src/service-worker.ts`), Cache-Keys versionieren | P1: veraltete Cache-Keys = stale UI nach Update | `public/service-worker.js` + `src/service-worker.ts` |
| 6 | **Dead-Code entfernen:** `api.ts` (`getSessions/createSession/...`) | P1: Bundle + Wartbarkeit | `rg` keine Aufrufe |
| 7 | **README launch-ready:** Badges (CI), Demo-GIFs, One-Command-Install (`curl … install.sh`), „Tool-Calls lokal" als Kern-Message | Beschreibung + About + Release setzen | README.md; GitHub Release-API |

### Woche 2 — „Training finalisieren" (2–4 Tage, parallel)

| # | Aufgabe | Begründung | Quelle |
|---|---|---|---|
| 8 | **Remote-Dataset kopieren:** `scp -r training/dataset … ubuntu@68.209.73.120:/home/ubuntu/miminox-data/` | P0: Training kann ohne Dataset nicht starten | STATUS_REPORT_NeMo_RL: Blocker #1 |
| 9 | **Checkpoint-Basis sicherstellen:** v15 FP32-LoRA-Merged auf H100 kopieren | P0: Base-Modell fehlt remote | STATUS_REPORT_NeMo_RL: Blocker #2 |
| 10 | **NaN-Stabilität fixen:** `normalize_rewards=True` + Leave-One-Out-Baseline in GRPO; `stop_token_ids` für `<|eot_id|>`/`<|end_of_turn|>`; Completion-Length-Bell-Curve validieren | P0: negative Losses/KL-Spitzen/Collapse = numerische Instabilität | TRL GRPO-Docs; STATUS_REPORT_NeMo_RL Blocker #4/#5 |
| 11 | **Training restarten mit Auto-Resume**, TensorBoard live, Checkpoints alle 25 steps | P0: Modell „perfekt für Tool-Calls" ist der Feature-Hook | STATUS_REPORT_NeMo_RL |

### Woche 2–3 — „Go-to-Market"

| # | Aufgabe | Begründung | Quelle |
|---|---|---|---|
| 12 | **Show HN posten** (`Show HN: MiMi Nox – lokaler AI-Assistant mit tool-getuntem Gemma-4`) | 50k–200k technische Leser, 500–2k Stars in 24h | gingiris.show-hn-guide 2026 |
| 13 | **Product Hunt Launch** (Tag 1: Upvotes, Maker-Comment, Demo-Video) | Day-One-Visibility + Long-Tail-Directories | tooljunction PH-Playbook 2026 |
| 14 | **X/LinkedIn founder-reach** (1-Minute-Demo, „eigene lokale Tool-Call-Modelle") | Founder-Reach = compounding | aitoolscapital „best places to launch" |
| 15 | **GitHub Release v1.0** mit Asset-Anhang (Modell-Card-Link zu `miminox-stage4-e4b`) | Release = sichtbares Meilenstein + Modell-Hook | GitHub Release-API |

---

## 4. Empfehlungen (mit Begründung + Quelle)

1. **P0-Reihenfolge strikt:** venv → Tests → Bundle → Versionierung. Ein public Release mit rotem CI oder 860-KB-Chunk kostet Vertrauen. *(AGENTS.md Release-Bar; Vite/PWA-Budgets)*
2. **Modell-Training ist der Differenzierungs-Hook, nicht der Blocker:** Das public Modell `miminox-stage4-e4b` existiert schon. Launch kann mit dem aktuellen Modell; das RL-Finetune „perfekt für Tool-Calls" wird als **Coming-Feature** kommuniziert, während es remote stabilisiert wird. *(Google FunctionGemma-Narrativ als Benchmark)*
3. **„Tool-Calls lokal" ist die Message:** Nicht „Chat-App", sondern „dein lokaler Agent mit eigenem, für Tools fein-getuntem Gemma-4-Modell" — das adressiert genau den Gap, den OpenClaw skaliert hat. *(arturmarkus/OpenClaw-Anatomie)*
4. **CI als öffentliches Vertrauenssignal:** `tests.yml` + `frontend-build.yml` grün + Badges im README, bevor Show HN. *(GitHub Actions; Repo-API)*
5. **Versionierung vor Release:** Ohne `app/`+`core/`+Tauri-Rust im Git gibt es keinen sauberen Release-Tag und keine Contributor-Basis. *(git status: 80 untracked)*
6. **Release v1.0 mit Modell-Card-Link:** Der Release-Tag ist der „Proof of Production" und trägt direkt zur Modell-Card `miminox-stage4-e4b` (HF) als Asset. *(GitHub Release-API)*

---

## 5. Risiken / Mitigations

| Risiko | Impact | Mitigation |
|---|---|---|
| RL-Training instabil (NaN, Collapse) | Feature-Hook verzögert | Launch mit aktuellem Modell; Training als Coming-Feature; GRPO-Fixes (#10) |
| 860-KB-Bundle | PWA-Performance-Vertrauen | Code-Splitting (#3) |
| 80 untracked Files | kein sauberer Release | Commit-Gate (#4) |
| venv 3.9 vs pyproject ≥3.10 | rote Tests | venv-Rebuild (#1) |
| Kein Description/About | unsichtbar für Beobachter | About+Description+Release (#7, #15) |

---

*Quellen: GitHub API (2026-08-02); git status; Vite/PWA; AGENTS.md; STATUS_REPORT_NeMo_RL; TRL GRPO; blog.google (FunctionGemma); ai.google.dev; gingiris Show-HN-Guide (2026-04); tooljunction PH-Playbook (2026); aitoolscapital „best places to launch"; arturmarkus/OpenClaw (150k Stars); ODSC/Octoverse.*

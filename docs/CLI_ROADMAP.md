# MiMi Nox CLI — Roadmap zur Weltklasse (2026)

> **Stand:** 2026-08-13 · Quelle der Wahrheit für CLI-Verbesserung · Benchmark gegen OpenClaw, Claude Code, Codex CLI, Gemini CLI, OpenCode
> **Review:** Brainstorm mit 5 Rollen — Developer-Tooling, AI-Product-Manager, AppSec, Backend-Architect, Performance-Benchmarker (Sektion 7)

## 1. Vision

MiMi Nox CLI wird eine **agentic-first, lokale, hardware-adaptive CLI** auf Augenhöhe mit den besten Coding-CLIs 2026 — mit drei Differenzierungsachsen:

1. **Lokalität/Privacy** — offline-first, lokale Modelle (gemma4:12b), kein Cloud-Zwang
2. **Hardware-Adaptivität** — ein Routing: lokal (gemma4:12b) ↔ remote (ds4), transparent pro Session
3. **Engine-Interop** — `miminox serve` als OpenAI-kompatible Engine für jede Coding-CLI (JCode/Codex/OpenCode)

JCode/Codex/OpenCode werden **Consumer** der Engine — Interop statt Konkurrenz.

## 2. Benchmark-Matrix (Stand der Kunst 2026)

| CLI | Stärken |
|---|---|
| OpenClaw (~150–180k★) | lokal, offline-first, tool-fähig, Agent-Harness |
| Claude Code | `/plan`, `/review`, `/agent`, Subagents, Hooks, Checkpoints, Diff-UI, Approvals, MCP |
| Codex CLI | YOLO-Modus, Sicherheits-Sandbox, Approval-Gates |
| Gemini CLI | Multi-Tool, native Provider-Integration |
| OpenCode | provider-agnostisch (OpenAI/Anthropic/local), `/commands`, Diffs |

**Gemeinsamer Weltklasse-Kern:**
- Startup **<100ms** (gemessen p50/p95), Lazy-Loading, CI-Gate
- Shell-Completions bash/zsh/fish
- TTY/`--json` Dual-Output + standardisierte Exit-Codes
- Actionable Errors (Cause + Fix, kein roher Stacktrace)
- Streaming + Progress + Status-Bar; TTFB (time-to-first-token) gemessen
- Diff-UI + Approvals + `--dry-run` (safe by default)
- Persistierte Sessions + `/commands` + Checkpoints/Rollback
- MCP-Client + Registry
- Config-Precedence dokumentiert (Flag > Env `MIMI_*` > `~/.mimi-nox/*.json`)

## 3. Ist-Stand `miminox_cli.py`

Subcommands: `start` | `doctor` | `update` | `tui`. Nur `doctor` hat `--json`. Keine Completions, kein Startup-Budget, keine `/commands`, kein Diff/Approval, kein `serve`. MCP-Client-Baustein existiert (`core/tools` registry), aber nicht im TUI verdrahtet. Engine-Config (engine_config.py) ist gebaut: atomar, keine API-Keys persistiert.

## 4. Architektur (Backend-Architect)

- **CLI vs. Engine trennen**: `core/` = Engine-Lib, `miminox_cli.py` = thin Wrapper; `miminox serve` nutzt nur `core/`.
- **`serve`-API-Contract (OpenAPI)**: `/v1/chat/completions`, `/v1/models`, `stream=true`, OpenAI-konformes Error-Format; Versioning + Deprecation-Fenster; Contract-Tests am OpenAPI-Schema.
- **Modell-Router als eigenes Modul** (`core/model_router.py`): single source of truth für Hardware-Adaptivität (gemma4:12b ↔ ds4).
- **Sessions-Persistence-Format stabil** + Expand-Contract-Migration; Backcompat.
- **Reliability**: Timeout/Retry/Backoff + Idempotency für remote (ds4); Request-ID + korrelierte Logs in `serve`.

## 5. Phasen

### Phase 0 — Security & Architecture-Gate (Cross-Cutting, vor allen Features)
1. **Secrets via Keyring** (macOS Keychain) statt Env für ds4/OpenAI-Keys; `engine.json` Permissions `0600`.
 2. **Threat Model (STRIDE)** pro Phase dokumentieren → `docs/SECURITY_THREAT_MODEL.md` (Quelle der Wahrheit; 10 Bedrohungen CLI + Engine + serve-API, Mapping auf diese Items). Security-Regression-Tests (test_security_offline_defaults.py, test_cli_dx.py).
3. **`serve`-Defaults konservativ** (AGENTS.md): localhost-Bind default, CORS default off, Auth-Token required für Remote-Zugriff.
4. **Approval-Gates** für destructive/network-Tools im agentic CLI-Modus (wie Codex); Prompt-Injection-Policy bei MCP/Web-Inhalt.

**DoD:** Keyring-Secrets · 0600-Configs · STRIDE pro Phase · serve localhost-only default · Approval-Gates e2e.

### Phase 1 — DX-Fundament (Developer-Tooling + Performance)
 1. ✅ **Shell-Completions** bash/zsh/fish (`miminox completion bash|zsh|fish`) für Subcommands + Flags.
 2. ✅ **`--json`/TTY Dual-Output** für update/doctor; stabiles JSON-Error-Format (Code/Message/Fix) für Laufzeit-Fehler via main()-Härtung (argparse usage errors liefern noch Text → P2: Custom-JSON-Parser).
 3. ✅ **Exit-Codes standardisiert**: 0 ok, 1 Fehler, 2 Usage (argparse).
4. ✅ **Startup-Budget <100ms**: Baseline gemessen **p50 = 60 ms** (7 Läufe, `/usr/bin/time`); Lazy-Import von TUI/MCP/Engine aus CLI-Pfad (keine schweren Module beim Load); CI-Gate: deterministischer Lazy-Import-Gate-Test in test_cli_dx.py (kein Timing-Flakiness).
5. **TTFB-Metrik** (time-to-first-token) für Streaming; Memory-Budget für lange Sessions.
6. ✅ **`--help`/`--version`** hohe Qualität: Subcommand-`description`-Texte (start/doctor) + Epilog-Beispiele + `serve`-Flags in Help; Tab-Complete der `/commands` → Phase 2.

**DoD:** Completions in 3 Shells · `--json` überall · Exit-Codes 0/1/2 · Startup p50 <100ms mit CI-Gate · TTFB gemessen · Help/Docs geprüft.
**Fortschritt 2026-08-13:** Items 1–6 umgesetzt — tests/test_cli_dx.py mit 9 Gates grün (completion bash/zsh/fish, --version, exit-codes 0/1/2, JSON-Error-Härtung, Lazy-Import-Gate). Startup **p50 = 60 ms** (< 100 ms-Ziel). Offen: TTFB (5).
### Phase 2 — Agentic TUI (Product + Developer-Tooling)
7. **Persistierte Sessions** + Multi-Session-Switch; Resume über Reboots (<200ms).
8. **`/commands`**: `/help /model /engine /configure /swarm /post /plan /review`.
9. **Diff-UI + Approvals + `--dry-run`** (safe by default); Status-Bar mit Context-Meter.
10. **MCP-Client verdrahten** (Baustein existiert) + Registry; Prompt-Injection-Policy aktiv.

**DoD:** Sessions-Switch <50ms · Resume <200ms · `/commands` vollständig · Diff/Approval e2e · MCP e2e mit Policy.

### Phase 3 — Engine-Interop (Backend + AppSec)
11. **`miminox serve`**: OpenAI-kompatible Engine (`/v1/chat/completions`, `/v1/models`, `stream=true`) mit OpenAPI-Contract + Auth-Token + localhost-Bind.
12. ✅ **Modell-Router** (`core/model_router.py`): Hardware-Adaptivität gemma4:12b ↔ ds4, transparent pro Request — Engine löst Modell über den Router auf (fehlendes model → Router.resolve(), explizites model gewinnt), Header `X-Model-Tier`/`X-Model-Name`/`X-Model-Provider`, `/v1/models` listet alle Tiers.
13. **Contract-Tests** am OpenAPI-Schema; Idempotency/Retry für remote.
14. **JCode/Codex/OpenCode e2e validieren** als Consumer der Engine.

**DoD:** serve läuft OpenAI-konform · Auth-Token + localhost-Bind · Contract-Tests green · JCode als erster Consumer e2e green.
**Fortschritt 2026-08-13:** Item 11 + 12 + 13 umgesetzt — `server/openai.py` (`create_openai_app`: `/v1/models`, `/v1/chat/completions` mit SSE-Stream + `[DONE]`, Auth-Token, localhost-Bind default) + `cmd_serve` (`--host/--port/--lan/--token/--model`, `--lan` generiert Token, `0.0.0.0`); tests/test_serve_openai.py mit **13 Contract-Tests green** (Models, non-stream, stream, Auth 401/200, Validierung 400, Router-Integration (fehlendes model → resolve, explizites model → skip, Header-Tiers)). Offen: JCode-Consumer e2e (14).

### Phase 4 — Observability & Release (Backend + Product)
15. **Strukturierte Logs + stabile Error-Codes + Request-ID** in serve/CLI.
16. **Version Single-Source** (bestehende Builds nutzen) + CHANGELOG je Phase.
17. **Perf-Regression in CI** (pytest-benchmark: Startup, TTFB, Memory).

**DoD:** Request-ID überall · Version single-source · CHANGELOG aktualisiert · CI-Benchmark-Gates green.

## 6. MVP-Priorisierung (AI-Product-Manager)

Nicht alles gleichzeitig. Nach User-Wert × Aufwand:
- **Sofort (P0)**: Phase 0 (Security/Architecture-Gate) + Phase 1 (DX) → sofort nutzbar, Trust-Basis.
- **Dann (P1)**: Phase 3 (serve/JCode-Interop) → größter Differenzierungs-Hebel.
- **Später (P2)**: Phase 2 (agentic TUI) + Phase 4 (Observability) → Komfort, wenn Basis steht.

Kritische Frage geklärt: „miminox ohne Flags → sofort nutzbar" ist gebaut (Engine-Auto-Detect); die Differenzierung (serve/JCode) ist der nächste große Hebel, nicht der TUI-Komfort.

## 7. Kritische Experten-Review (Brainstorm)

**AppSec (STRIDE) — Lücken, die geschlossen wurden:**
- Keine explizite Security-Phase im Ursprungsplan → **Phase 0** ergänzt.
- API-Keys: „nur Session-Env" ist leak-fähig → **Keyring + 0600-Configs**.
- serve = neue Angriffsfläche → **localhost-Bind, CORS off, Auth-Token**.
- Agentic Tools (Shell/Browser/File) ohne Policy → **Approval-Gates + Prompt-Injection-Policy**.

**Backend-Architect — Lücken:**
- serve ohne API-Contract → **OpenAPI + Versioning + Contract-Tests**.
- Modell-Routing verstreut → **`core/model_router.py`** single source.
- Remote (ds4) ohne Reliability → **Timeout/Retry/Backoff + Idempotency + Request-ID**.
- CLI/Engine vermischt → **core/ vs. thin Wrapper**.

**Performance-Benchmarker — Lücken:**
- „Startup messen" ohne Baseline/Toleranz → **Baseline erst, dann Gate mit Band** (p50/p95, mehrere Läufe).
- Nur Startup gemessen → **TTFB + Memory** ergänzt; Lazy-Import aus CLI-Pfad.
- Keine CI-Regression → **pytest-benchmark-Gates** (Phase 4).

**Developer-Tooling — Lücken:**
- `--json` nur bei doctor → **`--json`/TTY dual überall + stabiles JSON-Error-Format**.
- Keine Completions/Help-Qualität → **Phase 1 Items 1/6**.
- Fehlerarchitektur (stderr/stdout) → **Exit-Codes 0/1/2 + Code/Message/Fix**.

**AI-Product-Manager — Fokus:**
- Alles-auf-einmal-Risiko → **MVP-Priorisierung P0/P1/P2** (Trust-Basis vor Komfort).
- Differenzierung nicht kommuniziert → **serve/JCode als Hebel P1**; Help/README als Vertriebsfläche.

## 8. Test-Strategie

- **Security-Regression**: test_security_offline_defaults.py erweitern (Bind, CORS, Auth, 0600).
- **Contract-Tests**: OpenAPI-Schema für serve (Phase 3).
- **E2E**: JCode als Consumer (Phase 3); Approval-Gates (Phase 0); Diff/Approval (Phase 2).
- **Perf**: pytest-benchmark (Startup, TTFB, Memory) (Phase 4).

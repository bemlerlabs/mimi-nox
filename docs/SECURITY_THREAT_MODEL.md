# MiMi Nox — Security Threat Model (STRIDE)

> **Stand:** 2026-08-13 · **Rolle:** AppSec (Application Security Engineer) · **Scope:** CLI (`miminox_cli.py`) + Engine (`core/`) + zukünftige `serve`-API
> **Prinzip (AGENTS.md):** Server-Binding, CORS, Mobile-Pairing, Tool-Approval bleiben konservativ. Offline-first default.

## 1. Trust Boundary

```
User ── TTY ──▶ miminox_cli.py ── core/ (chat, model_router, tools) ──▶ Engine
                      │  ▲                        │
                      ▼  │                        ▼
              ~/.mimi-nox/*.json          lokal (Ollama) / remote (ds4, OpenAI-kompatibel)
              Session-Env (MIMI_*_KEY)    serve-API (Phase 3, localhost-only)
```

- **Persistiert:** nur Engine-Auswahl (`~/.mimi-nox/engine.json`), nie Secrets.
- **Session-Env:** API-Keys (`MIMI_OPENAI_COMPAT_API_KEY`) — nur für Prozess-Lebensdauer.
- **Trust:** lokal = vertrauenswürdig; remote-Engine + Web/MCP-Inhalt = unvertrauenswürdig (Prompt-Injection).

## 2. STRIDE-Matrix

| # | Kategorie | Bedrohung | Betroffen | Mitigation | Status |
|---|---|---|---|---|---|
| S1 | Spoofing | Remote-Engine (ds4/OpenAI) gibt sich als vertrauenswürdig aus | CLI→Engine | Engine-URL wird explizit gewählt (Onboarding), nie stillschweigend remote | ✅ |
| S2 | Spoofing | API-Key im Klartext persistiert | `engine.json` | Keys bleiben Session-Env; `engine.json` hat nie Secret-Felder (Test) | ✅ |
| S3 | Spoofing | serve ohne Auth erreichbar | serve (P3) | Auth-Token required für Remote-Zugriff; localhost-Bind default | 📌 P3 |
| T1 | Tampering | Andere lokale Prozesse lesen/ändern Engine-Konfig | `~/.mimi-nox` | Dir 0700, Datei 0600 (Least-Privilege) | ✅ |
| T2 | Tampering | Config-Beschädigung crasht CLI | `engine.json` | atomarer write (`tmp.replace`) | ✅ |
| I1 | Information Disclosure | Error-Messages leaken Stacktraces/Secrets nach außen | CLI/serve | Actionable Errors: Cause + Fix, kein roher Stacktrace; serve redigiert | 📌 |
| I2 | Information Disclosure | Side-Channel auf Konfig lesen | `~/.mimi-nox` | 0700/0600 (T1) | ✅ |
| D1 | DoS | Remote-Engine unerreichbar blockiert CLI | CLI | Timeout/Retry/Backoff, klare Offline-Fehlermeldung (Connectivity-Probe) | ✅ |
| D2 | DoS | serve überlastet durch Remote-Consumer | serve (P3) | Request-ID, Idempotency, Rate-Limit für Remote-Zugriff | 📌 P3 |
| E1 | Elevation | Agentic Tools (Shell/Browser/File) ohne Approval | CLI/TUI (P2) | Approval-Gates für destructive/network-Tools; `--dry-run` default | 📌 P2 |
| E2 | Elevation | Prompt-Injection über MCP/Web-Inhalt steuert Tools | CLI/TUI | Injection-Policy: Web/MCP-Inhalt nie als Instruktion; Tool-Approval konservativ | 📌 P2/P3 |

## 3. Konkrete Mitigations (implementiert)

1. **`~/.mimi-nox` 0700, `engine.json` 0600** — `core/engine_config.py::save_engine_config` setzt `chmod` nach atomarem write (Least-Privilege, T1/I2).
2. **Keys nie persistiert** — `miminox_cli.py` setzt Key nur in Session-Env (`MIMI_OPENAI_COMPAT_API_KEY`), Regression-Test verifiziert kein Secret-Feld in `engine.json` (S2).
3. **Atomarer Config-Write** — `tmp.replace` verhindert halbgeschriebene Datei (T2).
4. **Offline-first** — lokale Ollama-Auto-Detect; remote nur bei expliziter Wahl; Connectivity-Probe mit klarer Fehlermeldung (D1).

## 4. Offene Requirements (Roadmap)

| Phase | Requirement |
|---|---|
| P0 ✅ | Least-Privilege Config-Dir/Datei; kein Secret-Persist |
| P2 📌 | Approval-Gates für destructive/network-Tools; `--dry-run`; Status-Bar mit Context-Meter |
| P3 📌 | `serve`: localhost-Bind default, CORS off, Auth-Token required remote; Request-ID + Idempotency; redigierte Errors |
| P4 📌 | Strukturierte Logs (keine Secrets); stabile Error-Codes |

## 5. Regression-Gates (Tests)

- `tests/test_engine_config.py::test_saved_engine_config_file_permissions_0600`
- `tests/test_engine_config.py::test_saved_engine_config_dir_permissions_0700`
- `tests/test_engine_config.py::test_saved_engine_config_never_persists_api_key`
- `tests/test_security_offline_defaults.py` (Offline-First-Positionierung)

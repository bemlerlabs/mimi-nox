# MiMi Nox — Security Threat Model (STRIDE)

> **Stand:** 2026-08-19 (Sprint3-G2 Channel-Delta §6) · **Rolle:** AppSec (Application Security Engineer) · **Scope:** CLI (`miminox_cli.py`) + Engine (`core/`) + `serve`-API + Channel-Layer (`core/channels/`, Gateway-Alpha)
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
- `tests/test_channel_injection_guard.py` (Injection-Guard: Wrap + Flagging + False-Positive-frei, Outbound-only)
- `tests/test_tg_pairing.py` + `tests/test_tg_tokens.py` (Pairing-Allowlist Default-Empty, Token-Vault 0600/Keyring — geprüfte Implementierung)
- `tests/test_channel_injection_guard_live.py` (LIVE-DoD: injizierte Channel-Message → kein Tool-Call, gegen DGX-Harness Qwen)

## 6. Sprint 3 — Channel-Threat-Model (Gateway-Alpha: Telegram-Channel)

> **Delta-Referenz:** Erweiterung der Matrix um die neue Channel-Fläche
> (Telegram-Channel als On-Device-Gateway, kein Cloud-Relay). Sprint3-G2,
> implementiert in `core/channels/` (Pairing + Token-Vault in core/tg_pairing.py & core/tg_tokens.py, Injection-Guard in core/channels/injection_guard.py).
> **Trust-Boundary-Erweiterung (C4):** Der Channel-Transport ist
> **outbound-only** — der Gateway öffnet KEINEN Inbound-Port (kein
> Webhook-Listener, kein Relay-Prozess, kein zweiter Runtime). Einziger
> Outbound = der Channel-Transport selbst (Bot-API-Polling, `getUpdates`).

### 6.1 Neue Trust-Boundary (Channel-Ebene)

```
Telegram-User (unvertrauenswürdig) ── Outbound-Polling ──▶ core/tg_gateway.py
                                                               │ Pairing-Gate (Allowlist, C1)
                                                               ▼
                                                  core/channels/injection_guard.py
                                                  (Wrap + Flagging, C2)
                                                               │ Approval-Policy (C3, P0-1-Gate)
                                                               ▼
                                                        Engine/Chat-Pipeline (wie PWA)
```

- **Persistiert:** `pairing.json` (nur User-IDs, 0600, C1/C3) und Bot-Token (Keyring, Fallback 0600-Datei, C3).
- **Session:** Bot-Token nie in Logs/Config-Commit; nur in Keyring/0600-Datei.
- **Trust:** Channel-Inhalt = unvertrauenswürdig (Prompt-Injection), analog Web/MCP (E2).

### 6.2 STRIDE-Delta-Matrix (Channel-Fläche)

| # | Kategorie | Bedrohung | Betroffen | Mitigation | Status |
|---|---|---|---|---|---|
| C1 | Spoofing (S3) | Ungepairter Telegram-User steuert den Gateway | Channel-Eingang | Pairing = statische Allowlist Telegram-User-IDs, **Default-Empty** (antwortet niemandem); Fail-Closed bei fehlender/korrupter Config | ✅ |
| C2 | Elevation (E2) | Prompt-Injection über Channel-Text steuert Tools | Channel→Engine | Injection-Guard (VERDRAHTET in core/tg_gateway.py::_run_chat): (1) Quarantäne-Wrap (Untrusted-Data-Block) + Guard-System-Prompt via extra_system_prompt, (2) heuristisches Flagging (Observability), (3) **Approval-Policy als Sicherheitsnetz** (Wiederverwendung P0-1-Gate, non-interactive, conservative) | ✅ |
| C3 | Information Disclosure (I2) + Tampering (T1) | Bot-Token als Klartext persistiert/leaked | Token-Vault | Keyring-first, Fallback 0600-Datei; nie in Log/Config-Commit; `mask_token` für alle Outputs | ✅ |
| C4 | Tampering (T1) / Spoofing (S3) | Inbound-Port/Webhook-Relay öffnet neue Angriffsfläche | Channel-Transport | **Outbound-only Transport**: kein Inbound-Port, kein Webhook, kein Relay-Prozess, kein zweiter Runtime (Test `test_channel_layer_opens_no_inbound_port`) | ✅ |

### 6.3 DoD-Verifikation (Sprint3-G2)

- **Offline (deterministisch):** `tests/test_channel_injection_guard.py` —
  Pairing-Allowlist (Default-Empty), Injection-Guard (Wrap + Flagging +
  False-Positive-frei), Token-Vault (0600/Keyring, kein Klartext),
  Outbound-only-Gate. E2e-Szenario: injizierte Instruktion → MUTATING
  Tool-Call → Approval-Gate **DENY** (keine Side-Effects).
- **LIVE (DGX-Harness Qwen):** `tests/test_channel_injection_guard_live.py` —
  eine injizierte Channel-Message (Guard-wrapped) triggert **kein**
  Tool-Call bei der Qwen-Engine; die Antwort ist eine Ablehnung.
  Endpoint `http://spark-2c73.tail8f685e.ts.net:8000/v1`,
  Modell `qwen38-27b-unsloth-nvfp4`, `enable_thinking=false`.

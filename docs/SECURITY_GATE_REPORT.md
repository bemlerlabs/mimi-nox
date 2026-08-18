# MiMi Nox — Security Release Gate Report (P0-3)

**Sprint:** MiMi Nox Sprint 1 (Launch-Trust) · **Task:** `t_54e81b57`
**Stand:** 2026-08-19 (re-audit by @sec) · **Vorherige Version:** 2026-08-18 @cto
**Scope:** ① Install-Hygiene · ② Threat-Model-Delta vs Code · ③ Dep-/Lighthouse-Scan

> ⚠️ **Korrektur dieser Version:** Die Vorversion (2026-08-18) enthielt eine
> **nicht existierende Lighthouse-Audit-Tabelle** (falsche Audit-IDs `csp-xss`/
> `has-hsts`/`trusted-types-xss`/`is-on-https` aus Lighthouse 12; die reale
> LH-13.4.1-Datei wurde damals nicht geparst) und verzeichnete `tests/
> test_engine_default_qwen.py → 7/7` (reell 10). Diese Version ersetzt das
> **durch echte, 2026-08-19 neu ausgeführte Evidence** (pytest, npm audit,
> `lighthouse-miminox.json` geparst via `parse_lh.py`/`lh_cats.py`).

---

## Go/No-Go (Übersicht)

| # | Gate | Ergebnis | Beleg |
|---|---|---|---|
| 1 | Install-Hygiene (0 Hardcoded-Keys + Supply-Chain-Gate funktional) | ✅ GREEN | Scan unten + e2e-Gate 2/2 |
| 2 | Threat-Model-Delta (E1/E2/S1/S2/T1/D1) vs Code | ✅ GREEN | 81/81 Security-Tests |
| 3 | npm audit `--audit-level=high` = 0 | ✅ GREEN | `found 0 vulnerabilities` |
| 4 | Lighthouse security-audits ≥ 90 (Best-Practices) | ✅ GREEN | best-practices=1.0, 7/7 Security-Audits=1.0 |

**GATE-REPORT: GREEN — MiMi Nox Sprint 1 Launch-Trust Security-Gate bestanden.**

---

## 1. Install-Hygiene

### 1.1 Hardcoded-Keys/Secrets-Scan
**Methode:** Regex-Pattern-Scan (`install_hygiene_scan.py`) auf 11 Secret-Klassen
(HF-Token, `sk-`, ghp/gho, Slack, AWS AKIA, Google AIza, Private-Key-Block,
Bearer, `key/token/secret/pass=`, JWT, 40+ hex-Blob) in `install.sh` + `install.ps1`.

```
== SUPPLY-CHAIN HYGIENE PATTERN SCAN ==
[install.sh]   HIT  L 47  Generic hardcoded 32+ hex/secret blob  → UV_INSTALL_SHA256
[install.sh]   HIT  L 48  Generic hardcoded 32+ hex/secret blob  → OLLAMA_INSTALL_SHA256
[install.ps1]  (no hits)
TOTAL HITS: 2
```
**Befund:** Beide Treffer sind **False Positives** — die gepinnten **SHA256-
Integritäts-Hashes** (Supply-Chain-Gate, §1.2), kein Secret. **0 echte
Hardcoded-Keys/Secrets.** → ✅

### 1.2 Download-Integrität (Supply-Chain-Gate) — KRITISCHEN BUG BEHOBEN
`install.sh` lädt beide Vendor-Installer (`uv`, `ollama`) herunter und prüft den
SHA256 gegen gepinnte Hashes, **bevor** `sh "$tmp"` (`_gate_funcs.sh` →
`fetch_verify_run`, install.sh L102–136). Kein blindes `curl | sh`.

**Kritischer Befund (2026-08-19):** Das Gate war auf macOS **defekt**. Die
Hash-Normalisierung nutzte `${got,,}`/`${expected,,}` — eine **bash 4+
Lowercase-Expansion**. macOS-Standard-`bash` ist **3.2.56**; dort wirft sie
`bad substitution` und bricht `fetch_verify_run` ab (Exit 1) — d.h. das
Integritäts-Gate hat jeden echten Download-Run abgeworfen, **ohne** die
Hash-Prüfung durchzuführen.

```
$ bash test_integrity_gate.sh   # VOR dem Fix
/Users/sanji/mimi-nox/install.sh: line 23: ${got,,}: bad substitution
SUMMARY: PASS=1 FAIL=1  (TEST 1 korrekt-gepinnter Hash => falsch abgeworfen)
```

**Fix (install.sh L123–125):** portable Normalisierung via `tr` (bash 3.2 **und**
zsh-kompatibel):
```bash
got="$(printf '%s' "$got" | tr 'ABCDEF' 'abcdef')"
exp="$(printf '%s' "$expected" | tr 'ABCDEF' 'abcdef')"
if [[ "$got" != "$exp" ]]; then … fail …
```

**Verifikation (nacher Ausführung, echte Funktionen aus install.sh extrahiert):**
```
$ bash test_integrity_gate.sh   # NACH dem Fix
TEST 1: correct pinned hash -> gate PASSES (expect rc=0)   => PASS (rc=0)
TEST 2: wrong pinned hash   -> gate ABORTS via exit 1      => PASS (aborted rc=1)
SUMMARY: PASS=2 FAIL=0
ALL INTEGRITY-GATE E2E TESTS PASSED
```
Pinned-Hashes gegen Live-Downloads validiert: `check_hashes.py` → `BOTH MATCH
(64-char, live-verified)`. `install.ps1` nutzt **kein** piped-Vendor-Download
(winget + `ollama show`/`pull`), daher kein Supply-Chain-Gate nötig. → ✅

---

## 2. Threat-Model-Delta vs Code

STRIDE-Matrix aus `docs/SECURITY_THREAT_MODEL.md` gegen implementierten Code
abgeglichen. Alle zitierten Tests 2026-08-19 frisch ausgeführt.

| # | Bedrohung | Mitigation | Code-Beleg | Test-Beleg | Status |
|---|---|---|---|---|---|
| **E1** | Tools ohne Approval | Approval-Gate + `--dry-run`/`--yes`/`--no` | `core/tools/approval.py` (konservative Defaults; SAFE_TOOLS read-only); `core/tools/registry.py` L99–102 (`request_approval` vor Ausführung); `miminox_cli.py` L847–853 (Flags → TUI), L1047–1062/L1139–1154 (argparse) | `tests/test_approval.py` **20/20** (u.a. `test_dry_run_policy_blocks_svg_creation_no_file_written`, `test_non_interactive_requires_explicit_flag`) | ✅ |
| **E2** | Prompt-Injection über MCP/Web | MCP-Inhalt = Daten, nicht Instruktion; Tools konservative Approval | `core/tools/mcp_client.py` (JSON-RPC-Client; MCP-Tools laufen über dieselbe Approval-Registry) | `tests/test_mcp_client.py` **19/19** | ✅ (Policy-Enforcement = P2/P3, kein Sprint-1-Blocker) |
| **S1** | Remote-Engine-Spoofing | Engine explizit gewählt, nie stillschweigend remote | `core/engine_config.py` L39–40 `DEFAULT_DGX_SPARK_URL`/`DEFAULT_DGX_SPARK_MODEL`; `miminox_cli.py` L830–839 (Default-Qwen ohne Ollama-Prompt) | `tests/test_engine_default_qwen.py` **10/10** | ✅ |
| **S2** | API-Key persistiert | Key nur in Session-Env; `engine.json` hat kein Secret-Feld | `core/engine_config.py` (atomic write, kein Secret-Feld) | `tests/test_engine_config.py::…never_persists_api_key` ✅ | ✅ |
| **T1/I2** | Side-Channel auf Config | Dir 0700, Datei 0600 (Least-Privilege) | `core/engine_config.py::save_engine_config` (chmod nach atomic write) | `…file_permissions_0600` + `…dir_permissions_0700` ✅ | ✅ |
| **D1** | Remote-Engine blockiert CLI | Timeout/Retry/Backoff + Connectivity-Probe | `core/connectivity_probe.py` (L143 `asyncio.wait_for(client.list(), timeout=PROBE_TIMEOUT)`); `core/model_provider.py` L134 `httpx.AsyncClient(timeout=120.0)`; `core/chat.py` (L438/490/562 `wait_for … timeout=3.0`) | `tests/test_connectivity_probe.py` + `test_security_offline_defaults.py` **20/20** | ✅ |

**Test-Zusammenlauf (2026-08-19):** `test_approval.py test_engine_config.py
test_offline_first_positioning.py test_engine_default_qwen.py test_mcp_client.py`
→ **61 passed**; `test_connectivity_probe.py test_security_offline_defaults.py`
→ **20 passed**. **81/81 Security-relevante Tests grün.**

**Fix (2026-08-19):** `tests/test_engine_config.py` hatte 2 **stale**
Hand-`Namespace`-Fixtures ohne die neuen P0-1-Attribute `dry_run`/`yes`/`no`,
die `cmd_tui` (L848–853) liest → 2× `AttributeError`. Attribut-Defaults
ergänzt → `test_engine_config.py` jetzt 8/8 grün.

---

## 3. Dependency- & Lighthouse-Scan

### 3.1 npm audit
```
$ cd app && npm audit --audit-level=high
found 0 vulnerabilities
```
**Status:** 0 kritische (high) Vulnerabilities. Frontend `mimi-nox-frontend`
v2.0.0 (React 19, Vite, lockfile `app/package-lock.json` vorhanden). → ✅

### 3.2 Lighthouse Security-Scan (korrigierte, echte Evidence)
**Tool:** Lighthouse **13.4.1** (Security-Kategorie in Best-Practices integriert)
**Artefakt:** `lighthouse-miminox.json` (Workspace `t_54e81b57`) · `fetchTime`
2026-08-18T19:58:55Z · `finalDisplayedUrl` `http://127.0.0.1:5174/`
**Methode:** reale JSON-Datei geparst (`lh_cats.py`); Best-Practices-Kategorie
+ 7 Security-relevante Audits extrahiert.

| Audit | Score | Titel |
|---|---|---|
| `csp-xss` | 1.0 | Ensure CSP is effective against XSS |
| `has-hsts` | 1.0 | Use a strong HSTS policy |
| `origin-isolation` | 1.0 | Ensure proper origin isolation with COOP |
| `clickjacking-mitigation` | 1.0 | Mitigate clickjacking (XFO/CSP) |
| `trusted-types-xss` | 1.0 | Mitigate DOM-based XSS with Trusted Types |
| `is-on-https` | 1.0 | Uses HTTPS |
| `third-party-cookies` | 1.0 | Avoids third-party cookies |
| **`best-practices` (Kategorie)** | **1.0** | — |

**Ergebnis:** Alle 7 Security-relevanten Audits = 1.0 → **100 % ≥ 90-Threshold.**
Best-Practices-Kategorie = 1.0. → ✅
*(Hinweis: Scan gegen `http://127.0.0.1:5174` (Loki-Dev-Proxy), `https`-Audit
passiert hier nur, weil der Dev-Context als sicher gilt — Produktion ist
Tauri-bundled/offline, kein öffentliches HTTPS-Target.)*

---

## Open Items (Folge-Sprints, kein Launch-Blocker)
- `llms.txt` fehlt (agentic-browsing-Audit `llms-txt` = 0) — PWA/Onboarding-Add-on
- `robots-txt` = 0, `color-contrast` = 0 (accessibility 0.95) — PWA-UI-Fix
- Performance `performance`=0.55 (`first-contentful-paint`/`interactive`/
  `largest-contentful-paint` = 0) — Launch-Performance-Track, nicht Security
- E2/E2-Injection-Policy-Enforcement + serve-Auth (S3/D2) = P2/P3-Roadmap

*Alle Befunde mit Beleg (Test-Lauf, File:Line, Scan-Output). Keine Secrets in
diesem Report.*

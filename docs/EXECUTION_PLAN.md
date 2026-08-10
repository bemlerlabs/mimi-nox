# MiMi Nox Execution Plan

> **Stand:** 2026-07-08 — Phase 0.9 abgeschlossen, Phase 1.0 Stage 0 aktiv
>
> Dieser Plan ist der verbindliche Fahrplan für die Entwicklung von MiMi Nox.
> Agenten und Entwickler arbeiten Phase für Phase ab.

---

## 1. Product Goal

MiMi Nox als offline-first AI Assistant mit Tool-Use (Browser, Shell, File Ops, PDF)
von einer lokalen Einzel-Instanz zu massenmarktfähiger Cloud-Inference skalieren.
Pivot von öffentlicher Cloud zu **Private-Person-Ownership + Swiss IP**.
Monolith JS/JS → modularer Vite-Build.

**Key Differentiator vs. Konkurrenz (Product Hunt 2026):**
Surface Integrations (Browser, Shell, Dateien, PDF) direkt im Chat — lokal und datenschonend.
Kein anderer Player bietet vergleichbares Tool-Use in einer lokalen (optional cloud-verbundenen) PWA.

---

## 2. Constraints & Preferences

### Product
| Aspekt | Entscheidung |
|--------|-------------|
| Name | MiMi Nox (offline-first local AI assistant) |
| Stack | PWA (Vanilla JS) + FastAPI (Python) + Ollama/Gemma 4 |
| Key Diff | Tool-Use (Browser, Shell, File Ops, PDF) + QR Mobile Pairing |
| Default Model | Gemma 4 E4B (4.5B eff., Apache 2.0) |
| Fine-Tune Ziel | `mimi-pro` (tool-use-optimized) |

### Monetization (3 Tiers, kein Enterprise)
| Tier | Preis | Details |
|------|-------|---------|
| **Free** | €0 | Lokal, 10 Sessions/Tag |
| **Cloud Pro** | $9.99/mo | Cloud Inference, unbegrenzt |
| **Premium Download** | $29.99 | Tauri Desktop App mit bundled Ollama + Model (One-Click Install, ~3.2GB DMG) |

### Infrastructure
| Aspekt | Wert |
|--------|------|
| Cloud Compute | Lambda Labs, ~$5.900 Credits remaining |
| Training GPU | 1x H100 PCIe ($3.29/h) |
| Training Cost | ~$86 (26h total) |
| Inference Budget | ~$5.814 verbleibend nach Training |
| Desktop Bundle | Tauri + bundled Ollama + Gemma 4 (~3.2GB DMG), One-Click Install |

### Entity
| Aktuell | Ziel | Grund |
|---------|------|-------|
| MiMi Tech AI UG (DE) | Swiss Einzelfirma (Private Person) | Niedrigere Steuern, kein deutsches KI-Gesetz, einfachere Buchhaltung, IP-Schutz |

### Training Research Base (arxiv 2026)
| Paper | Anwendung |
|-------|-----------|
| **ToolGT** | Strukturierte Reasoning-Templates vor Tool-Calls (schlägt Free-Form CoT um 3-12%) |
| **AdaSTaR** | Adaptives Sampling für SFT-Daten |
| **Expert Failures** | Rejection Sampling aus gescheiterten Trajektorien |
| **Fission-GRPO** | Gruppen-basiertes RL für Tool-Sequenzen |
| **GRPO** | Hierarchisches Reward-Modell |
| **ToolSample** | Curriculum Learning mit progressiver Tool-Schwierigkeit |

### PWA Constraint
Die PWA muss **voll funktional als Vanilla JS** bleiben — der Vite-Build darf
Offline-Funktionalität und Service-Worker nicht brechen.

---

## 3. Abgeschlossene Phasen

### ✅ Phase 0 Quick Wins (Committed)

9 Files, 175 Insertions — Sicherheits- und UX-Sofortmaßnahmen vor dem Split:

- **Auth Middleware** — `server/middleware/auth.py`: Token-basierte API-Auth für externe Zugriffe
- **CSP Header** — Content-Security-Policy in FastAPI responses
- **Rate Limit** — requests/minute pro IP in `server/middleware/rate_limit.py`
- **Shell Whitelist** — `ALLOWED_COMMANDS` + `BLOCKED_PATTERNS` in `core/tools/base.py`
- **SVG Favicon** — Inline-SVG statt externer Datei
- **Stream Delay removed** — Kein künstlicher Delay mehr im SSE-Stream

---

### ✅ Phase 0.6: tools.py Split (Completed)

**Ziel:** 3127-Zeilen Monolith `core/tools.py` in ein modulares Package aufbrechen.

#### Struktur

```
core/tools/
├── __init__.py          # Re-exports aller Symbole
├── base.py              # Exceptions, Constants, Shared Client, Whitelist Helpers
├── web_search.py        # Web-Suche (DDGS, Tavily)
├── file_ops.py          # Dateioperationen (read, write, search, list)
├── source_tools.py      # Source-Management (Speichern, Indizieren)
├── shell_tools.py       # Shell-Ausführung (gated)
├── system_tools.py      # Datetime, Projects, Workspace, Image, Screenshot, SVG
├── browser_tools.py     # Browser-Automation
├── chart_tools.py       # Chart-Generierung
├── pdf_tools.py         # PDF-Operationen
├── deck_tools.py        # Deck/PPTX-Tools (~1100 Zeilen)
├── task_tools.py        # Task-Management
└── registry.py          # TOOL_MAP + get_tool_schemas()
```

#### Details

- `core/tools.py` → 3-Zeilen Compat-Shim: `from core.tools import *`
- Kein Code in den Tools verändert — nur Imports/Exports umgebogen
- **500 Tests grün** (alle tool-bezogenen 81 Tests + Full Suite)
- **6 Test-Files gepatcht** für korrekte `patch()`-Targets:
  - DDGS → `web_search.DDGS`
  - ollama → `base.ollama`
  - subprocess.run → `system_tools.subprocess.run`
  - Path.home → `system_tools.Path.home`
  - Weitere 3 Imports korrigiert

#### base.py im Detail

```python
# Exceptions
class ToolError(Exception): ...
class ToolExecutionError(ToolError): ...
class ToolInputError(ToolError): ...
class ToolSecurityError(ToolError): ...
class ToolTimeoutError(ToolError): ...
class ToolResourceError(ToolError): ...

# Constants
ALLOWED_COMMANDS = {
    'ls', 'dir', 'cat', 'head', 'tail', 'wc', 'echo',
    'pwd', 'whoami', 'uname', 'date', 'cal', 'df', 'du',
    'ps', 'top', 'find', 'grep', 'rg', 'sort', 'uniq',
    'cut', 'tr', 'tee', 'mkdir', 'cp', 'mv', 'rm', 'chmod',
}
BLOCKED_PATTERNS = [
    r'\bsudo\b', r'\bsu\b', r'\bpasswd\b', r'\bchown\b',
    r'\bdd\b', r'\bmkfs\b', r'\bfdisk\b', r'\bparted\b',
    r'>\s*/dev/', r'/\s*etc/\s*passwd', r'/\s*etc/\s*shadow',
    r'rm\s+-rf\s+/\s*$', r':(){ :\|:& };:',
]

# Helper
_get_shared_client()    # HTTPX Client mit Timeout/Retry
_get_allowed_roots()    # Lese-/Schreib-Whitelist
_is_path_allowed(path)  # Path-Traversal-Check
```

#### Ergebnisse

- **10-Person Executive Board Audit** durchgeführt — Competitive Positioning bestätigt (Blue Ocean)
- **Alle 500 Tests grün** nach Refaktor
- Commits: Phase 0 Quick Wins (9 Files) + Phase 0.6 (tools.py Split)

---

### ✅ Phase 0.7: main.js Modular Split + Vite Build (Completed)

**Ziel:** 3469-Zeilen Monolith `app/src/main.js` (136KB) in modulare Struktur mit Vite-Build aufbrechen.

#### Architektur

Jedes Modul exportiert ein `default` Object mit Methoden.
`main.js` (Entry Point) importiert alle Module und macht:

```js
Object.assign(NoxApp.prototype, utils);
Object.assign(NoxApp.prototype, api);
// ... alle 16 Module
```

NoxApp-Klasse selbst enthält nur: `constructor`, `init()`, `clearSession()`,
`exportChat()`, `switchTab()`, `loadProfile()`, `saveProfile()`.

100% Rückwärtskompatibilität — keine Methode umbenannt oder verändert.

#### Modul-Übersicht (18 Dateien)

| # | Modul | Zeilen | Methoden | Funktion |
|---|-------|--------|----------|----------|
| 1 | `constants.js` | 30 | — | API, STORE_KEY_HISTORY, DEFAULT_MODEL, Limits, SKILL_ICONS, SKILL_SCOPES |
| 2 | `utils.js` | 109 | 5 | safeStorage, getServiceWorker, _escHtml, Text-Kompression, _chatDisplayText |
| 3 | `api.js` | 126 | 7 | checkHealth, _showOfflineBanner, _setStatus, _buildTierBadge, _updateProviderBadge, _isMissingModelError, _modelRecoveryHtml |
| 4 | `provider.js` | 181 | 9 | _selectedProviderMode, _setProviderMode, _syncProviderModeFields, _populateLocalModelSelect, _refreshProviderModels, _showProviderModal, _hideProviderModal, _saveProviderSettings |
| 5 | `bindings.js` | 441 | 6 | _queryElements (70+ DOM-Referenzen), _bindEvents (30+ Handler), _autoResize, _clearAttachedImage, _bindModeToggle, _applyModeUI |
| 6 | `chat-engine.js` | 653 | 7 | submitMessage, _requiresOnlineConfirmation, _showDesktopOnlineConfirm, _hideDesktopOnlineConfirm, _handleScheduleCommand, _startStreaming (SSE-Reader mit 20+ Event-Typen), _submitSyntheticMessage |
| 7 | `renderer.js` | 258 | 12 | _hideWelcome, _showLanguagePicker, renderUserBubble, _createAIBubbleWrap, renderAIBubble, _appendChunk (debounced Markdown-Streaming), _finalRender, _appendFileResult, _showBubbleActions, _scrollToBottom, _renderAudioBubble |
| 8 | `history.js` | 97 | 3 | _saveToHistory, _renderHistoryList, _navigateHistory |
| 9 | `memory.js` | 94 | 4 | loadMemoryPanel, _loadMemoryList, searchMemoryFull, _deleteMemoryEntry |
| 10 | `tasks.js` | 60 | 3 | loadTasks, toggleTask, deleteTask |
| 11 | `skills.js` | 311 | 13 | loadSkillChips, _skillIcon, _skillScope, _prepareSkillChip, _selectSkillTrigger, _clearSelectedSkill, _highlightChip, _showSlashMenu, _hideSlashMenu, loadSkillsTab, _renderSkillCard, _openSkillForm, _closeSkillForm, _saveSkill |
| 12 | `audio.js` | 326 | 12 | _initVoices, _speakText, _resetSpeakBtn, _toggleRecording, _startRecording, _stopRecording, _cancelRecording, _onRecordingComplete, _updateWaveform, _renderAudioBubble, _playTone |
| 13 | `feedback.js` | 121 | 3 | handleFeedback, handleDeepen, _showReasonPicker |
| 14 | `clipboard.js` | 42 | 2 | handleCopy, _copyTextToClipboard |
| 15 | `mobile.js` | 77 | 2 | _showMobileModal (QR + Polling), _hideMobileModal |
| 16 | `activity.js` | 74 | 3 | _addActivity (5 Typen), _showMobileToast, toggleActivityPanel |
| 17 | `onboarding.js` | 37 | 2 | _initOnboarding, _completeOnboarding |
| 18 | `app.js` | 285 | 8 | NoxApp-Klasse + bootNoxApp + SW Registration |

**Gesamt:** ~3.322 Zeilen Module + 40 Zeilen Entry = ~3.362 Zeilen
(Original: 3.469 Zeilen — leichte Reduktion durch Wegfall von Duplikaten)

#### Vite Build-Infrastruktur

**`app/vite.config.js`:**
```js
root: 'src'
base: ''
build.outDir: '../dist'
build.emptyOutDir: true
Plugins: copyDir('lib'), copyDir('fonts'), copyFile('service-worker.js'), copyFile('mobile.html')
```

**`app/package.json`:**
```json
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "devDependencies": { "vite": "^6.0.0" }
}
```

**Key Decisions:**
- Kein Framework — Vanilla JS bleibt erhalten
- Vite `root: 'src/'` — `index.html` bleibt in `src/`
- `base: ''` — relative paths für file:// Kompatibilität
- Copy-Plugins für assets, die Vite nicht automatisch bundled (lib/, fonts/, SW, mobile.html)
- Cache-Busting via Vite-Hashes in Asset-Names

#### Build Output

```
dist/
├── index.html              36 kB (Vite-transformiert)
├── assets/
│   ├── index-DVO0QFXL.js  150 kB (43 kB gzip) — 24 Module gebundled
│   ├── index-EJqx98K1.css  57 kB (11 kB gzip)
│   ├── manifest-*.json
│   └── icon-192-*.png
├── lib/                     marked.min.js + purify.min.js
├── fonts/                   Inter (4 WOFF2)
├── service-worker.js
└── mobile.html
```

#### Testing

- **579 Tests grün** (volle Suite)
- 4 Test-Files gepatcht für Module-Scan:
  - `test_export.py` — scannt jetzt `main.js` + alle Module nach `exportChat`, `Blob`, `createObjectURL`
  - `test_mode_toggle.py` — scannt `main.js` + `bindings.js` nach mode-toggle Logik
  - `test_pwa_visual.py` — scannt `main.js` + `app.js` + `utils.js` nach SW-Registrierung
  - `test_tasks_ui.py` — scannt `main.js` + `tasks.js` nach Task-API-Call

---

## 4. Nächste Phasen

### ✅ Phase 0.8: Tests für neue Tool-Module (Completed)

**97 neue Tests** (676 total, 43 skipped) — jedes Tool-Submodul hat gezielte Unit-Tests.
Bestehende `tests/test_tools.py` (24 Tests) + 8 neue Test-Dateien.

#### Neue Test-Dateien

| Datei | Tests | Coverage |
|-------|-------|----------|
| `tests/test_tools_source.py` | 4 | `create_source_notebook`, `query_source_notebook`, `export_source_brief` |
| `tests/test_tools_system.py` | 18 | `discover_projects`, `analyze_project`, `load_workspace`, `analyze_image`, `take_screenshot`, `create_svg` |
| `tests/test_tools_browser.py` | 5 | `browser_go`, `browser_screenshot`, `browser_click`, `browser_type`, `browser_press` |
| `tests/test_tools_chart.py` | 10 | `generate_chart` (SVG bar/line/pie), `_generate_svg_chart`, edge cases |
| `tests/test_tools_pdf.py` | 9 | `create_pdf`, `_apply_pdf_template` (4 templates), sanitize filename |
| `tests/test_tools_deck.py` | 22 | `_safe_download_filename`, `_split_lines`, `_enterprise_clean_text`, `_normalize_enterprise_slides`, `_default_deck_slides`, `_parse_deck_slides`, `_pdf_escape`, `_normalize_hex_color` |
| `tests/test_tools_tasks.py` | 12 | `manage_tasks` (add/update/delete/list, error cases) |
| `tests/test_tools_registry.py` | 9 | `execute_tool`, `TOOL_MAP` completeness (30 tools), `get_filtered_tool_schemas` |

#### Key Fixes
- `patch()`-Targets für lazy imports korrigiert (`discover_project_records` → `core.project_discovery`, `task_manager` → `core.tasks`, `SimpleDocTemplate` → `reportlab.platypus`)
- `patch.dict("core.tools.registry.TOOL_MAP")` verwendet, da `TOOL_MAP` direkte Funktions-Referenzen hält
- Chart-Tests prüfen via `write_text`-Mock den geschriebenen SVG-Inhalt statt Return-Value

---

### ✅ Phase 0.9: UI-Tests + Tauri Prep (Completed)

**Goal:** Visuelle Regression + Tauri Desktop App Setup.

- [x] Playwright Visual Tests — 22 Smoke Tests (Boot, Tabs, Modals, Mobile Viewport)
- [x] Tauri `src-tauri/` Konfiguration geprüft/aktualisiert
- [x] Tauri Build getestet — DMG (3.3MB) + .app generiert (`cargo tauri build`)
- [ ] bundled Ollama + Model in Tauri-Ressourcen (vor Release)

**Details:**
- Playwright v1.59.0, Chromium Browser installiert
- 4 Spec-Files: `app-boot.spec.ts`, `tabs.spec.ts`, `modals.spec.ts`, `mobile-viewport.spec.ts`
- Language-Picker + Onboarding Overlay in `helpers.ts` vor Klicks dismissen
- Erwartete API-404/501-Fehler aus Console-Check gefiltert
- Tauri CLI v2.11.4, `tauri init` generierte `src-tauri/` Structure
- `tauri.conf.json`: `frontendDist: "../app/dist"`, `beforeBuildCommand: "cd ../app && npm run build"`
- Rust 1.95.0, Release Build in 50s

---

### 🔲 Phase 1.0: Model Training Pipeline

**Goal:** `mimi-pro` — Tool-Use-optimiertes Fine-Tune des Gemma 4 E4B auf Lambda H100.

#### ✅ Stage 0: Data Construction (Completed, ~$0)
- ToolGT Template-Format für alle Trainingsdaten
- Strukturiertes Reasoning vor jedem Tool-Call (schlägt Free-Form CoT um 3-12%)
- Template-Schema: `<|tool_use|>\n<reasoning>…</reasoning>\n<tool>…</tool>\n<observation>…</observation>`
- Quellen: 12 Skill-Templates (68 Tests), 5 Multi-Tool-Sequenzen, augmentierte Varianten
- Output: **10.000 Samples** (25MB, JSONL)
  - `training/dataset/toolgt_train.jsonl` (9.000)
  - `training/dataset/toolgt_val.jsonl` (500)
  - `training/dataset/toolgt_test.jsonl` (500)
- **19 Tools** abgedeckt (alle 19 public Tools aus TOOL_MAP)
- **Multi-Tool-Ketten**: 35 Samples mit 2+ Tools (search→chart, read→search, discover→analyze, notebook→query, notebook→deck)
- **Durchschnittliche Länge**: 1.212 Zeichen pro gerendertem Sample
- **Top-Tools**: web_search (3.186), create_pdf (2.148), generate_chart (706), analyze_image (687)
- Pipeline-Code: `training/toolgt_schema.py`, `training/templates.py`, `training/seed_data.py`, `training/generate.py`

#### Stage 1: SFT mit AdaSTaR Sampling (~$10, 3h auf H100)
- Adaptives Sampling: Modell generiert eigene Tool-Use Trajektorien
- Rejection Sampling: nur erfolgreiche Trajektorien behalten
- Loss: Cross-Entropy auf Reasoning + Tool-Call + Response Token
- Learning Rate: 2e-5, Cosine Decay
- Batch Size: 16, Gradient Accumulation: 4
- Output: SFT-Checkpoint

#### Stage 2: Rejection Sampling mit Expert Failures (~$15, 4.5h auf H100)
- Modell generiert 8 Samples pro Prompt
- Expert-Klassifikator bewertet: Tool Selection, Argument Quality, Success
- Gescheiterte Samples → negativem Reward (Expert Failures)
- Erfolgreiche Samples → Preference Pair (gewählt/abgelehnt)
- DPO Loss auf Preference Pairs
- Output: DPO-Checkpoint

#### Stage 3: GRPO mit Hierarchical Reward (~$35, 10.5h auf H100)
- Gruppen-basiertes RL (Group Relative Policy Optimization)
- Reward-Hierarchie:
  1. Task Success (Primary, 0.6 Gewicht)
  2. Tool Selection Accuracy (0.2 Gewicht)
  3. Efficiency (0.1 Gewicht — minimale Schritte)
  4. Safety (0.1 Gewicht — keine unsicheren Befehle)
- KL-Divergenz Penalty gegen SFT-Checkpoint
- GRPO Clip Range: 0.2
- Output: GRPO-Checkpoint

#### Stage 4: Online RL mit ToolSample Curriculum (~$26, 8h auf H100)
- Curriculum Learning: progressive Tool-Komplexität
  1. Level 1: Single Tool (file_read, web_search)
  2. Level 2: Tool Chain (search → read → summarize)
  3. Level 3: Conditional Branching (if/else Tool-Selection)
  4. Level 4: Multi-Step Reasoning + Tools
- Online Sampling: Modell interagiert mit echter Tool-Umgebung
- PPO mit KL-Penalty
- Output: Finales `mimi-pro` Modell

#### Cost Breakdown
| Stage | GPU-Stunden | Kosten | Beschreibung |
|-------|-------------|--------|-------------|
| Stage 0 | — | $0 | Lokale Data Prep |
| Stage 1 | 3h | ~$10 | SFT AdaSTaR |
| Stage 2 | 4.5h | ~$15 | Rejection Sampling + DPO |
| Stage 3 | 10.5h | ~$35 | GRPO Hierarchical |
| Stage 4 | 8h | ~$26 | Online RL ToolSample |
| **Total** | **26h** | **~$86** | |

Verbleibend für Inference nach Training: **~$5.814**

---

### 🔲 Phase 1.1: Entity Transition

**Goal:** MiMi Tech AI UG (DE) → Swiss Einzelfirma (Private Person)

**Gründe für Wechsel:**
| Faktor | UG (DE) | Swiss Einzelfirma |
|--------|---------|-------------------|
| Steuern | ~30% Körperschaftssteuer | ~12% Einkommenssteuer (progressiv) |
| KI-Gesetz | Deutsches KI-Gesetz (streng) | Kein spezifisches KI-Gesetz |
| Buchhaltung | Doppelte Buchführung, Jahresabschluss | Einfache Einnahmen-Überschuss-Rechnung |
| IP | Gesellschaftsvermögen | Privatvermögen |
| Haftung | Beschränkt | Unbeschränkt (aber SaaS-Risiko gering) |
| Gründungskosten | ~€500 (Notar + Handelsregister) | ~CHF 0 (kein Eintrag nötig) |

**Tasks:**
- [ ] Swiss Aufenthaltsstatus klären (Visum/Niederlassung)
- [ ] Einzelfirma beim kantonalen Steueramt anmelden
- [ ] Swiss Bankkonto eröffnen (für Zahlungsabwicklung)
- [ ] Stripe/Subscriptions auf Swiss Entity umstellen
- [ ] Repo Ownership von UG auf Private Person übertragen
- [ ] IP-Assignment: UG → Private Person
- [ ] Steuerberater für CH-Einzelfirma konsultieren
- [ ] UG abwickeln (löschen oder ruhend stellen)

---

## 5. Architektur-Entscheidungen

| Entscheidung | Detail | Begründung |
|-------------|--------|------------|
| **ToolGT Template Format** für Training | `<tool_use>` Block vor jedem Tool-Call | Beat Free-Form CoT um 3-12% (arxiv 2026) |
| **Kein Enterprise Tier** | Nur Free + Cloud Pro + Premium Download | Fokus auf B2C/Power-User; Enterprise-Komplexität vermeiden |
| **Private Person + Swiss IP** | Swiss Einzelfirma statt UG | Niedrigere Steuern, kein deutsches KI-Gesetz, einfachere Buchhaltung |
| **main.js Split Pattern** | `initX(app)` → Methoden-Objekt → `Object.assign(this, ...)` | 100% Rückwärtskompatibilität; keine Methoden-Änderungen nötig |
| **Vite Config minimal** | `root: 'src/'`, `base: ''`, keine Framework-Plugins | Vanilla JS bleibt erhalten; SW bleibt extern; PWA-Kompatibilität |
| **shell=True gated** | (1) User Confirmation, (2) ALLOWED_COMMANDS Whitelist, (3) BLOCKED_PATTERNS Blacklist | Sicherheit ohne Funktionsverlust |
| **Train on Lambda H100** | 4-Stage Pipeline (SFT → Rejection → GRPO → Online RL) | Günstigste Option mit ausreichend VRAM; ~$86 total |
| **Product Hunt Positioning 2026** | Surface Integrations (Browser, Shell, Files, PDF) | Klarer Blue Ocean; kein anderer lokaler Assistant bietet Tool-Use |
| **Tests = Release Bar** | Kein Feature gilt als fertig ohne Tests | Sicherheit durch TDD; 676 Backend-Tests + 22 Playwright UI-Tests |

---

## 6. Critical Context

| Aspekt | Wert |
|--------|------|
| **Lambda Credits** | ~$5.900 remaining. Training ~$86 (26h). Rest ~$5.814 für Inference |
| **GitHub** | `bemlerlabs/mimi-nox` — 1 Star, 59 Commits, main Branch, Apache 2.0, UG-owned |
| **shell=True Risk Mitigation** | Gated by (1) User Confirmation, (2) ALLOWED_COMMANDS Whitelist, (3) BLOCKED_PATTERNS Blacklist |
| **Test Suite** | 676 passing, 43 skipped (Backend) + 22 Playwright (Frontend) |
| **Frontend Lines** | 3.362 Zeilen (Module 3.322 + Entry 40) vs. original 3.469 im Monolith |
| **ToolGT Dataset** | 10.000 Samples (19 Tools, 9k Train / 500 Val / 500 Test, 25MB) |
| **Tauri Build** | `MiMi Nox_1.0.0_aarch64.dmg` (3.3MB) + `MiMi Nox.app` |

---

## 7. Relevante Files

### Backend Core
| Pfad | Beschreibung |
|------|-------------|
| `core/tools.py` | 3-Zeilen Compat-Shim (`from core.tools import *`) |
| `core/tools/__init__.py` | Re-exports aller Symbole aus 12 Submodulen |
| `core/tools/base.py` | 6 Exceptions, ALLOWED_COMMANDS, BLOCKED_PATTERNS, Shared Client, Path Whitelist |
| `core/tools/web_search.py` | Web Search (DDGS + Tavily) |
| `core/tools/file_ops.py` | Dateioperationen |
| `core/tools/source_tools.py` | Source-Management |
| `core/tools/shell_tools.py` | Shell-Ausführung |
| `core/tools/system_tools.py` | System-Tools |
| `core/tools/browser_tools.py` | Browser-Automation |
| `core/tools/chart_tools.py` | Chart-Generierung |
| `core/tools/pdf_tools.py` | PDF-Operationen |
| `core/tools/deck_tools.py` | Deck/PPTX-Tools (~1100 Zeilen) |
| `core/tools/task_tools.py` | Task-Management |
| `core/tools/registry.py` | TOOL_MAP + get_tool_schemas() |

### Frontend
| Pfad | Beschreibung |
|------|-------------|
| `app/src/main.js` | Entry Point (importiert + mixt alle Module) |
| `app/src/modules/app.js` | NoxApp-Klasse + bootNoxApp + SW Registration |
| `app/src/modules/constants.js` | Konstanten |
| `app/src/modules/utils.js` | Utilities |
| `app/src/modules/api.js` | Health Check |
| `app/src/modules/provider.js` | Provider Settings |
| `app/src/modules/bindings.js` | Event Bindings |
| `app/src/modules/chat-engine.js` | Chat + Streaming |
| `app/src/modules/renderer.js` | DOM Rendering |
| `app/src/modules/history.js` | Chat History |
| `app/src/modules/memory.js` | Memory Panel |
| `app/src/modules/tasks.js` | Tasks Tab |
| `app/src/modules/skills.js` | Skills Tab |
| `app/src/modules/audio.js` | Audio Recording + TTS |
| `app/src/modules/feedback.js` | Feedback |
| `app/src/modules/clipboard.js` | Clipboard |
| `app/src/modules/mobile.js` | Mobile Pairing |
| `app/src/modules/activity.js` | Activity Panel |
| `app/src/modules/onboarding.js` | Onboarding |
| `app/vite.config.js` | Vite Build Config |
| `app/package.json` | Dependencies + Scripts |
| `app/src/index.html` | Entry HTML (Vite-kompatibel) |
| `app/src/i18n.js` | Internationalisierung |
| `app/src/artifact.js` | Artifact Store + Panel |
| `app/src/style.css` | Stylesheet (3.163 Zeilen) |
| `app/src/service-worker.js` | Service Worker |
| `app/src/mobile.html` | Mobile Pairing Page |
| `app/src/lib/marked.min.js` | Markdown Parser |
| `app/src/lib/purify.min.js` | XSS Sanitizer |

### Tests
| Pfad | Beschreibung |
|------|-------------|
| `tests/test_tools.py` | Tool Unit Tests (81 Tests) |
| `tests/test_tool_calling.py` | Tool Calling Integration |
| `tests/test_export.py` | Export UI Logic (gepatcht für Module) |
| `tests/test_mode_toggle.py` | Mode Toggle (gepatcht) |
| `tests/test_pwa_visual.py` | PWA Visual Tests (gepatcht) |
| `tests/test_tasks_ui.py` | Tasks UI (gepatcht) |
| `tests/test_vision.py` | Vision Tests |
| `tests/test_finding_*.py` | Finding-basierte Tests |
| `tests/test_installer_cli.py` | Installer Tests |
| `tests/test_offline_first_positioning.py` | Positioning Tests |
| `tests/test_security_offline_defaults.py` | Security Tests |

### Docs
| Pfad | Beschreibung |
|------|-------------|
| `docs/EXECUTION_PLAN.md` | **Dieser Plan** |
| `docs/MIMINOX_VISION_2026.md` | Produktvision & Prinzipien |
| `docs/TASK_LIST_TDD.md` | TDD-Backlog & WGT-Szenarien |
| `docs/superpowers/plans/2026-06-01-workbench-core.md` | Workbench Core Plan (älterer Feature-Plan) |
| `AGENTS.md` | Arbeitsanweisungen für Agenten |
| `README.md` | Public Readme |
| `CHANGELOG.md` | Release Notes |

# MiMi Nox Desktop — UX/Redesign-Plan (KONSOLIDIERT & REFRESHED)

> **EINZIGE WAHRHEIT** — ersetzt `UX-PLAN-DESKTOP-CHAT.md` (Wurzel) und `docs/UX_DESKTOP_DESIGN_PLAN.md`. Beide Alt-Docs gelten als **veraltet** (2025-07-25, geschrieben vor den Native-Features).
> Beleg-Legende: **[IST]** = im Code nachgewiesen · **[PLAN]** = geplant/offen · **[KONFLIKT]** = Docs widersprechen sich oder Code weicht vom Plan ab.
> Konsolidiert am 2026-08-07 durch 2 Sub-Agents (Architektur/Tauri, Strategie/Matrix) + Orchestrator (UI/UX), verifiziert gegen `app/src` + `src-tauri/`.

---

# 1. UI/UX Design (konsolidiert & refreshed)

## 1.1 Design-System

| Token | Ist-Wert im Code | Docs-Plan | Beleg |
|---|---|---|---|
| Hintergrund | `black-forest: 0 0% 2%` (nicht totes #000) + `black-midnight: 220 15% 5%` | Dark-Forest | **[IST]** — `styles/globals.css` `@theme` |
| Primär (Firefly) | `142 65% 55%` (Hue 142°) | Docs: `#22C55E` **vs** `#16A34A` | **[KONFLIKT]** — Code nutzt **HSL-Token-System**, nicht die simplen Hex-Werte der Docs |
| Akzent-Trio | `moss-deep 12% / moss 22% / moss-light 35%` | — | **[IST]** — 3-Tone Moos-System |
| Glow | `firefly-glow: 142 80% 65%` + `forest-glow` Klassen | Glow-Effekt | **[IST]** — `.forest-glow/.forest-glow-subtle/.forest-glow-strong` |
| Glass | `.liquid-glass` / `.liquid-glass-strong` | liquid-glass | **[IST]** — `globals.css` |
| Text | `stone: 0 0% 100%` (Primär), `mist: 210 10% 70%` (Sekundär) | — | **[IST]** |
| Radius | `--radius: 0.75rem` | — | **[IST]** |

> **Empfehlung (Konflikt-Auflösung):** Das implementierte HSL-Token-System (Hue 142°, Moos/Firefly) ist **besser** als die Hex-Vorschläge der Docs — es ist konsistent, semantisch benannt und Tailwind-v4-fähig. **Behalten.** Ein "Professionalisierungs-Polish" (falls gewünscht) ist eine **Feinjustierung der Token-Werte**, kein Farbwechsel auf `#16A34A`.

## 1.2 Screens

| Screen | Ist-Zustand | Beleg |
|---|---|---|
| **Landing** (Hero/Features/Architecture/Skills/CTA/Footer + LivingForest + ForestBackground) | gebaut | **[IST]** — `components/landing/` |
| **CTA = PlatformSelector** (macOS arm64/x86, Windows, Linux, Web/PWA, Download, UA-Detection) | gebaut | **[IST]** — `landing/CTASection.tsx` |
| **Onboarding** (Ollama-Check → Modell-Pull → Welcome) | **Route aktiv + Komponenten-Split** | **[IST]** — `/onboarding` in `App.tsx` (lazy), `components/onboarding/` (`OnboardingWizard`, `OllamaCheck`, `ModelSelector`, `FirstChatSetup`), `OnboardingPage` dünne Route |
| **Chat** (ChatLayout: Sidebar + Header + virtualisierter Message-Stream + EmptyState + Tool-Approval inline) | gebaut, **EmptyState + Tool-Call extrahiert** | **[IST]** — `components/dashboard/ChatLayout.tsx`, `WelcomeEmptyState.tsx`, `ToolCallDisplay.tsx` |
| **ChatInput** (auto-resize, Senden, Modell-Badge, Anhang-Buttons) | gebaut, **Modell-Badge dynamisch + Attachments echt** | **[IST]** — `ChatInput.tsx` lädt Modell aus `getSettings()`; Paperclip → `open_file_picker` (Tauri); `AttachmentPreview.tsx` |
| **Settings** (Appearance, Model, Ollama, Backend-Status, i18n) | gebaut | **[IST]** — `components/dashboard/SettingsPanel.tsx` |
| **Command Palette** (Cmd+K) | gebaut | **[IST]** — `components/ui/CommandPalette.tsx` + `hooks/useCommandPalette.ts` |

---

# 2. Architektur & Native Desktop-Features (konsolidiert & refreshed)

## 2.1 Komponenten-Architektur (`app/src/`)

Ist-Struktur entspricht AGENTS.md-Konventionen (`components/` nach Feature). **Abweichend vom Plan fehlen:** `onboarding/` + `layout/` Verzeichnisse sowie die meisten "NEU"-Chat-Komponenten.

| Pfad | Ist-Zustand im Code | Beleg |
|---|---|---|
| `src/pages/` | `LandingPage.tsx`, `ChatPage.tsx`, `OnboardingPage.tsx` | [IST] |
| `src/components/ui/` | `Button`, `Card`, `Badge`, `Input`, `Dialog`, `Tooltip`, `DropdownMenu`, `CommandPalette`, `ErrorBoundary`, `BlurText`, `index.ts` | [IST] |
| `src/components/landing/` | `HeroSection`, `FeaturesSection`, `ArchitectureSection`, `SkillsSection`, `CTASection`, `Footer`, `LivingForest`, `ForestBackground` | [IST] |
| `src/components/dashboard/` | `ChatLayout`, `Sidebar`, `ChatInput`, `MessageBubble`, `TypingIndicator`, `SettingsPanel`, `WelcomeEmptyState`, `CodeBlock`, `ToolCallDisplay`, `AttachmentPreview` | [IST] |
| `src/components/onboarding/` | `OnboardingWizard`, `OllamaCheck`, `ModelSelector`, `FirstChatSetup` — **gebaut** | [IST] |
| `src/components/layout/` | `AppShell`, `WindowControls` — **nicht vorhanden** (WindowControls inline in `ChatLayout`) | [PLAN] |
| `src/hooks/` | `useInView.ts`, `useLocalStorage.ts`, `useTauriTray.ts`, `useTauriWindow.ts`, `useCommandPalette.ts`, `useToggleLanguage.ts` | [IST] |
| `src/lib/` | `api.ts`, `websocket.ts`, `db.ts`, `utils.ts` | [IST] |
| `src/types/` | `index.ts` (Shared-Types, kanonisch) — **gebaut** | [IST] |
| `src/locales/` + `src/i18n.ts` | `de.json`, `en.json`, `i18n.ts` (DE/EN) | [IST] |

> **KONFLIKT:** Plan (§4) sieht `onboarding/` + `layout/` und 10+ neue Chat-Komponenten vor; im Code existieren nur `ui/`, `landing/`, `dashboard/`. Die Onboarding- und Chat-Overhaul-Features sind offen.

## 2.2 State-Management (`chatStore.ts` + `db.ts`)

| Aussage | Ist-Zustand | Beleg |
|---|---|---|
| Store via **Zustand** (`create`), keine Class Components | `useChatStore = create<ChatStore>` | [IST] |
| State-Slice: `sessions`, `activeSessionId`, `isTyping`, `pendingToolCall`, `currentSession` | vorhanden | [IST] |
| Actions: `setSessions`, `setActiveSession`, `createSession`, `deleteSession`, `addMessage`, `setTyping`, `setPendingToolCall`, `initFromDb` | vorhanden | [IST] |
| Persistenz über **IndexedDB** (`db.ts`): `dbGetAllSessions`, `dbGetSession`, `dbSaveSession`, `dbDeleteSession`, `dbClearAll`, `debouncedSaveSession` (1.5s) | vorhanden (DB `mimi-nox`, Store `sessions`, Index `updatedAt`) | [IST] |
| Plan: `localStorage` via Zustand `persist`-Middleware (§5) | **nicht im Code** — real nutzt die App IndexedDB | [KONFLIKT] |
| Plan: `OnboardingState` (step, ollamaInstalled, selectedModel, memoryEnabled, toolApprovalEnabled, trayEnabled, …) + Actions `completeOnboarding`, `setOnboardingStep`, `setModelSelection` | **nicht im Store** | [PLAN] |

> **KONFLIKT:** Das Quelldoc plant `localStorage`-Persistenz; der implementierte Store persistiert über **IndexedDB mit Debounce**. Onboarding-State fehlt.

## 2.3 Tauri Rust-Commands (`src-tauri/src/lib.rs`)

Alle Commands in **lib.rs** (`tauri::generate_handler!`), `main.rs` nur Entry (`app_lib::run()`).

| Command | Funktion | Beleg |
|---|---|---|
| `check_ollama` | `OllamaStatus { healthy, version, endpoint }`; `which ollama` (macOS), `GET /api/version` auf `http://localhost:11434`; startet `open -a Ollama` und re-checkt | [IST] |
| `pull_model` | Blocking-Pull, emittiert Progress-Events ans Frontend (`.emit`) | [IST] |
| `get_ollama_models` | `GET /api/tags`, parse via `parse_ollama_models` | [IST] |
| `parse_ollama_models` | Helper, parse Model-Namen aus Tags-Response (mit Unit-Tests) | [IST] |
| `minimize_window` / `maximize_window` / `close_window` / `quit_app` / `show_window` / `hide_window` / `get_window_state` | Window-Control-Commands (Tray/Titlebar) | [IST] |
| `navigate` | `window.navigate(parsed)` für interne Route-Steuerung | [IST] |
| `open_file_picker` | Native File-Dialog via `tauri-plugin-dialog` (`app.dialog().file().blocking_pick_file()`), Capability `dialog:default` | [IST] |
| `check_updates` / `install_update` | async Updater-Flow via `tauri-plugin-updater` | [IST] |

> **KONFLIKT (Command-Namen vs Plan):** Ein Quelldoc (§6) plant `check_ollama_installed`, `check_ollama_model`, `ollama_pull_model`, `open_file_picker`, `get_supported_models`. Implementiert: `check_ollama`, `pull_model`, `get_ollama_models` (+ Window/Updater/Navigate). `open_file_picker` (FilePicker) **fehlt**.

## 2.4 Native-Features

| Feature | Status | Beleg |
|---|---|---|
| System-Tray (Show/Hide/New Session/Quit, Tooltip "MiMi Nox — Local AI") | gebaut | [IST] — `create_tray` in `lib.rs` + `useTauriTray` |
| Custom Window-Controls (min/max/close) | gebaut | [IST] — Commands + `useTauriWindow`, inline in `ChatLayout` |
| Auto-Update (Updater, GitHub-Endpoint, hardenedRuntime, macOS ≥ 12.0) | gebaut | [IST] — `tauri-plugin-updater`, `tauri.conf.json` |
| Native FilePicker | gebaut (`open_file_picker` + `tauri-plugin-dialog`) | [IST] |
| Native Menu Bar / globale Shortcuts / Hardware-Info | offen | [PLAN] |

---

# 3. Feature-Matrix, Sync-Strategie & Risiko (konsolidiert & refreshed)

## 3.1 Desktop vs Web/PWA

| Feature | Desktop (Tauri) | Web (PWA) | Beleg |
|---|---|---|---|
| Landing Page + Plattform-Wahl | ✓ | ✓ | [IST] — `CTASection` PlatformSelector |
| Chat (Streaming WS/REST) | ✓ | ✓ | [IST] — `ChatLayout` + `api.ts`/`websocket.ts` |
| Session-Management | ✓ (IndexedDB) | ✓ (IndexedDB) | [IST] — `db.ts` |
| Markdown + GFM | ✓ | ✓ | [IST] — `MessageBubble` |
| Tool-Use + Approval (inline Approve/Deny) | ✓ | ✓ | [IST] — `pendingToolCall` + `approveTool` |
| i18n (DE/EN) | ✓ | ✓ | [IST] — `locales` + `i18n.ts` |
| System-Tray / Window-Controls / Auto-Update | ✓ | ✗ | [IST] — nur Desktop |
| Globale Shortcuts / FilePicker / Hardware-Info / Clipboard / Screenshot | ✗ | ✗ | [PLAN] |

## 3.2 Sync-Strategie (Desktop ↔ Web)

```
Desktop ←→ lokales Filesystem ←→ Backend (localhost:8765)   ↕ (optional: Cloud-Sync)
Web    ←→ Browser-Storage (IndexedDB) ←→ Backend (remote/cloud)
```

- **Phase 1 (MVP):** beide 100% lokal, kein Sync. **[IST]**
- **Phase 2 (optional):** E2E-verschlüsselter Sync über **selbst-gehosteten Server** (User bringt eigenen Server mit); Sessions verschlüsselt; **niemals standardmäßig aktiv**. **[PLAN]**
- Brand-Promise **"Privat. Lokal. Dein."** — bewusst **kein Auto-Sync**, Sync nur bei expliziter Konfiguration. **[PLAN]**

## 3.3 Zeit-Schätzung / Phasen

> **[KONFLIKT]** — die beiden Quelldocs divergieren stark: Doc-1 ≈ 50–55h / ~2–3 Wochen (Overhaul auf bestehendem Kern), Doc-2 ≈ 76 Tage / 10–14 Wochen (Greenfield). Da der Kern **[IST]** gebaut ist, ist das **realistische Rest-Delta deutlich kleiner als Doc-2**.

**Phasen (konsolidiert, auf bestehendem Kern):**
1. **Landing + Plattform-Wahl** — **[IST]** gebaut ✅
2. **Onboarding-Wizard** (Ollama-Check → Modell → Erster Chat) — **[IST]** Route aktiv + Komponenten-Split ✅
3. **Chat-UI-Overhaul** (Welcome/Suggestions, CodeBlock + Syntax-Highlighting, Tool-Call-Display, Attachment-Preview) — **[IST]** gebaut ✅ (`rehype-highlight` + `highlight.css`, `CodeBlock`, `ToolCallDisplay`, `WelcomeEmptyState`, `AttachmentPreview`)
4. **Native-Features** (Tray ✓, Window ✓, Updater ✓, **FilePicker ✓**) + offen: globale Shortcuts, Hardware-Info, Notifications — **[PLAN]**
5. **Polish & Extras** (Theme-Token-Feinjustierung, Light-Mode, Sync opt-in) — **[PLAN]**

## 3.4 Risiko & Mitigation

| Risiko | Auswirkung | Mitigation | Beleg |
|---|---|---|---|
| Ollama nicht installiert / API nicht erreichbar | Onboarding blockiert, Chat ohne Modell | Klare Copy-Paste-Anleitung + `check_ollama` Auto-Start | [IST] |
| Großer Modell-Download (14GB+) | User bricht ab | Progress-Bar im Onboarding, Download im Background (`pull_model` + Progress-Events) | [IST] |
| Windows-Ollama nicht in PATH | Check schlägt fehl | Registry-Prüfung (`HKEY_CURRENT_USER\Software\Ollama`) | [PLAN] |
| Linux-Distro-Vielfalt | Install-Befehl variiert | Distro-Erkennung (`/etc/os-release`), angepasste Befehle | [PLAN] |
| Tauri-2-Plugin-Kompatibilität | Breaking Changes | Nur Tauri-2-kompatible Plugins | [IST] |
| React-Memory-Leaks über Zeit | App wird langsam | Virtualisierung (`useVirtualizer`) für große Chats | [IST] |
| Modell-Discrepanz (UI-Badge `gemma4:e4b` vs Docs `12b`) | falsche Modell-Auswahl | Badge/Default konsistent setzen | **[GELÖST]** — `ChatInput` liest Modell dynamisch aus `getSettings().provider.model` statt hartkodiert |

---

# 4. Offene Entscheidungen (TODO vor Implementierung)

1. **Theme-Polish:** HSL-Token-System behalten; Feinjustierung optional — kein Hex-Wechsel auf `#16A34A`. *(Empfehlung oben)*
2. **Onboarding-Route aktivieren:** `/onboarding` in `App.tsx` + `OnboardingWizard` in `components/onboarding/` splitten. — **✅ erledigt**
3. **Chat "NEU"-Komponenten:** `WelcomeEmptyState`, `CodeBlock` (Syntax-Highlighting via `rehype-highlight` + `highlight.css`), `ToolCallDisplay`, `AttachmentPreview`. — **✅ erledigt**
4. **`src/types/index.ts`:** Shared-Types extrahieren (aktuell in `api.ts`/`chatStore.ts`). — **✅ erledigt** (kanonisch, Module umgestellt, tsc green)
5. **FilePicker:** Tauri-Command `open_file_picker` + `tauri-plugin-dialog` + Capability. — **✅ erledigt**
6. **Modell-Badge konsistent:** `gemma4:e4b` hartkodiert → **✅ erledigt** (dynamisch aus `getSettings().provider.model`)
7. **Sync opt-in** nur bei expliziter Konfiguration (Brand-Promise "Privat. Lokal. Dein.").

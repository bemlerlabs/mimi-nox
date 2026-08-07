> **⚠️ VERALTET (2026-08-07)** — ersetzt durch `docs/UX_DESKTOP_REDESIGN_PLAN.md` (einzige Wahrheit). Dieser Doc ist von 2025-07-25 und deckt die heute gebauten Native-Features (Tray/Window/Updater/Command-Palette) nicht ab. Nicht mehr als Basis für Implementierung verwenden.

# MiMi Nox Desktop App — UX/UI Design Plan
## Hermes Agent / ChatGPT Style Chat UI

> **Ziel:** Desktop-App (macOS, Windows, Linux via Tauri 2), die sich beim ersten Öffnen wie eine premium Chat-App anfühlt — vergleichbar mit Hermes Agent oder ChatGPT.

---

## 1. TECHNOLOGIE-BEGÜNDUNG

### Warum Tauri 2?

| Kriterium | Tauri 2 | Electron | Web PWA |
|-----------|---------|----------|---------|
| Bundle-Größe | ~5-10 MB (Rust binary ~3 MB) | ~150-200 MB | ~0 MB |
| RAM-Usage | ~30-50 MB | ~300-500 MB | ~100-200 MB |
| Native OS APIs | Ja (Shell, Menu, Dialog, Notification, Tray) | Ja (breit) | Nein |
| Signierung (macOS/Win) | Ja (Notarization, EV Code Signing) | Ja (schwerer) | Nein |
| Startup-Zeit | <500ms | 2-5s | 1-3s |
| App-Store Kompatibilität | macOS App Store ✓, Windows MSIX ✓ | macOS App Store ✓ | Nein |

**Begründung:** Tauri 2 ist die einzig sinnvolle Wahl für MiMi Nox, weil:
- Die App soll **offline-first** sein — ein natives Installer-Erlebnis ist essential
- **System-Tray** (Hintergrund-Modus beim Schließen) ist Tauri-only
- **Native Menüs** (macOS Cmd+K shortcut, App-Menüs) brauchen Tauri
- Das Bundle ist **20x kleiner** als Electron — critical für Downloads auf langsamen Verbindungen
- Die **Rust-Bindung** erlaubt zukünftig native Features (Clipboard-Monitoring, Screenshot, Keybindings)
- Der Backend-Server (`run_server.py`) läuft als **Rust-Task**, nicht als Child-Process — zuverlässiger

### Warum dieses Layout-Paradigma?

| Design-Element | Wahl | Begründung |
|----------------|------|------------|
| **3-Spalten-Layout** (Sidebar + Chat + Optional Panel) | Follow ChatGPT/Hermes | User kennen das Pattern. Null Lernkurve. |
| **Fester Sidebar-left, scrollbarer Chat-center** | Wie Hermes Agent | Best-practice für Chat-Apps. Sidebar bleibt visible, Chat scrollt. |
| **Bottom Input mit Auto-resize** | Wie ChatGPT/Hermes | User tippen von unten nach oben — natürlicher Flow |
| **System Tray (Hintergrund-Minimierung)** | Tauri Feature | Mac-Nutzer erwarten `Cmd+W` = Tray, nicht Schließen |
| **Dark-Only (Standard)** | Like Hermes | "Forest Dark" Branding. Light-Mode als späterer Bonus. |
| **Inter Font** | Bereits im Projekt | Web-Safe, Apple-ähnlich, perfekt für UI |

---

## 2. UI/UX DESIGN PLAN — SCREEN-BY-SCREEN

### 2.1 DESIGN-SYSTEM (basierend auf existierendem Forest Dark)

#### Farbpalette (erweitert)

```
Background:     #000000 (pure black — OLED-freundlich)
Surface:        #0A0A0A (card backgrounds)
Surface-hover:  #111111 (hover states)
Border:         rgba(34, 197, 94, 0.12) (subtle green border)
Primary:        #22C55E (Forest Green — CTAs, accents)
Primary-hover:  #16A34A (hover)
Primary-dim:    rgba(34, 197, 94, 0.08) (background fills)
User-bubble:    #166534 (darker green — user messages)
Assistant-bg:   rgba(255,255,255,0.04) (subtle glass)
Text-primary:   #FFFFFF (headings, body)
Text-secondary: #9CA3AF (muted text)
Text-tertiary:  #4B5563 (placeholders, timestamps)
Success:        #22C55E
Warning:        #F59E0B
Error:          #EF4444
Info:           #3B82F6
```

#### Typografie

```
Font Family:  Inter (400, 500, 600, 700)
Code:         JetBrains Mono (oder SF Mono fallback)

Sizes:
  Sidebar:       13px / 12px (labels / timestamps)
  Chat:          15px (body), 14px (code), 12px (metadata)
  Headings:      24px (hero), 18px (section), 14px (card)
  Input:         15px, font-weight 400
  Labels:        12px uppercase, tracking-wide
```

#### Components (erweiterte Library)

| Component | Status | Action |
|-----------|--------|--------|
| `Button` | ✅ Existiert, OK | Leicht anpassen (Radius 0.5rem statt 0.75rem für moderner Look) |
| `Card` | ✅ Existiert | OK |
| `Badge` | ✅ Existiert | OK |
| `Input` | ✅ Existiert | OK |
| `Dialog/Modal` | ✅ Existiert | OK |
| `DropdownMenu` | ✅ Existiert | OK |
| `Tooltip` | ✅ Existiert | OK |
| **`ResizableSidebar`** | ❌ Fehlt | **Neu**: Splitter zum Breiten-Anpassen |
| **`CodeBlock`** | ❌ Fehlt | **Neu**: Syntax-Highlighting mit Copy-Button |
| **`MarkdownRenderer`** | ❌ Fehlt | **Neu**: `react-markdown` + `rehype-highlight` |
| **`WelcomeEmptyState`** | ✅ Existiert (ChatLayout) | **Verbessern**: Zentriertes Design wie ChatGPT |
| **`ToolApprovalPanel`** | ❌ Fehlt | **Neu**: Right-panel für Tool-Approval-Flow |
| **`ModelSelector`** | ❌ Fehlt | **Neu**: Dropdown für Model-Auswahl (wie ChatGPT) |
| **`AttachmentUpload`** | ⚠️ Partiel | **Verbessern**: Drag & Drop zone, file previews |

---

### 2.2 SCREEN: LANDING PAGE (Web — mimiai.de / miminox.app)

```
┌────────────────────────────────────────────────────────────────────┐
│  ◑ MiMi Nox                  Features  Architektur  [GitHub] [▶▶]  │ ← Sticky Header
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ◑ MiMi Nox                                                        │
│  Dein lokaler KI-Assistent                                         │
│  Privat. Lokal. Dein.                                              │
│  100% offline. Kein Cloud. Kein Tracking.                          │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  curl -fsSL https://.../install.sh | bash    [Copy ✓]     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  [▶ Jetzt starten]  [GitHub ↗]                                     │
│                                                                    │
│  [7,000+ Users]  [100% Offline]  [Apache 2.0]                     │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │  ◈ Offline   │  │  ◈ Multimodal│  │  ◈ Tools     │             │
│  │  ...         │  │  ...         │  │  ...         │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Browser PWA → FastAPI Server → Ollama (lokal)             │    │
│  │  :5173         :8765              :11434                    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  STARTE JETZT MIT MIMINOX                                          │
│  Kein Account. Kein Cloud. Kein Tracking.                          │
│                                                                    │
│  ┌───────────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │  🍎 macOS         │  │  🪟 Windows   │  │  🐧 Linux        │  │  ← NEU! Plattform-Wahl
│  │  Universal / Apple │  │  MSIX / EXE   │  │  AppImage / Deb  │  │
│  │  [Download ↓]     │  │  [Download ↓] │  │  [Download ↓]    │  │
│  │  arm64  x86_64    │  │  x64          │  │  x86_64          │  │
│  └───────────────────┘  └───────────────┘  └──────────────────┘  │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  🌐 MiMi Nox Web — Sofort im Browser                        │    │
│  │  [Web öffnen ↗]                                            │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  Footer: ◑ MiMi Nox · GitHub · Twitter · v2.0.0 · Apache 2.0      │
└────────────────────────────────────────────────────────────────────┘
```

**Entscheidungen:**
- Plattform-Wahl **auf der Landing Page** — kein separater Download-Screen. User wählt ihre Plattform und landet sofort beim Download.
- **Web/PWA** als eigene Sektion mit "Sofort im Browser" — für User, die keine App wollen (Quick-Test, shared PCs).
- **Unter-Labels** pro Plattform: arm64/x86_64 für macOS (Silicon vs Intel), x64 für Windows, x86_64 für Linux.
- Die Landing Page bleibt **unverändert** von der aktuellen Struktur, aber die CTA-Sektion wird zur **Plattform-Wahl**.
- **Warum?** 60%+ der macOS-Nutzer auf Apple Silicon werden arm64 bevorzugen. Die Wahl muss **explizit** sein, sonst falsche Architektur.

---

### 2.3 SCREEN: FIRST-BOOT ONBOARDING (Desktop App)

```
┌────────────────────────────────────────────────────────────────────┐
│  ◑ MiMi Nox v2.0.0                              [✕]               │ ← Native Window
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│                       ◑ MiMi Nox                                   │
│                       ─────────                                     │
│                                                                    │
│  Willkomen bei MiMi Nox — deinem                                      │
│  lokalen KI-Assistenten.                                           │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Schritt 1 von 3                                             │    │
│  │                                                            │    │
│  │  ┌────────────────────────────────────────────────────┐    │    │
│  │  │  🔌 Ollama installieren                            │    │    │
│  │  │                                                    │    │    │
│  │  │  MiMi Nox benötigt Ollama als lokale KI-Engine.   │    │    │
│  │  │  Ollama ist der Standard-Server für lokale LLMs.  │    │    │
│  │  │                                                    │    │    │
│  │  │  ┌─────────────────────────────────────────────┐  │    │    │
│  │  │  │  $ curl -fsSL https://ollama.com/install.sh │  │    │    │
│  │  │  │  | bash                                     │  │    │    │
│  │  │  │                                             │  │    │    │
│  │  │  │  [Copy]  [▶ Installieren]                   │  │    │    │
│  │  │  └─────────────────────────────────────────────┘  │    │    │
│  │  │                                                    │    │    │
│  │  │  ✓ Ollama ist bereits installiert (v0.3.x)       │    │    │
│  │  │  [Ollama prüfen]                                  │    │    │
│  │  └────────────────────────────────────────────────────┘    │    │
│  │                                                            │    │
│  │  [Weiter →]                                                 │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ─●────○────○───  1 von 3                                         │
└────────────────────────────────────────────────────────────────────┘
```

**STEP-BY-STEP ONBOARDING-Flow:**

#### Schritt 1: Ollama Install Check

```
Ablauf:
1. Tauri Rust-Backend prüft via Tauri command:
   - `which ollama` (macOS/Linux) oder Registry-Check (Windows)
   - `ollama --version` wenn vorhanden
2. **Fall A: Ollama gefunden** →
   - Zeige "✓ Ollama installiert: v0.3.x"
   - Prüfe: Ist das Modell "gemma4:12b" geladen? → Ja/Nein
   - Wenn Neut: Zeige "gemma4:12b ist nicht geladen — [Modell jetzt herunterladen]"
   - [Weiter →]
3. **Fall B: Ollama NICHT gefunden** →
   - Zeige Installationsanleitung mit Copy/Install Buttons
   - Mac: "curl -fsSL https://ollama.com/install.sh | bash"
   - Windows: Link zu ollama.com/download/windows
   - Linux: Paket-Manager Befehle pro Distro
   - Zeige "✓ Installation prüfen" Button
   - [Weiter →] (aktiviert erst nach Bestätigung)

Entscheidung:
- Wir geben dem User die Wahl: "Automatisch installieren" (Tauri Shell exec) 
  ODER "Manuell installieren, dann weiterklicken"
- Auto-Install auf Mac: Öffnet Terminal-Fenster mit dem curl-Befehl
- Auto-Install auf Windows: Öffnet Download-Seite im Browser
- Begründung: Tauri's `tauri::command` kann Shell-Befehle ausführen, 
  aber wir wollen kein Privilegien-Eskalationsrisiko. Daher: 
  Shell-exec mit User-Confirmation, keine silent-install.
```

#### Schritt 2: Modell-Auswahl

```
┌────────────────────────────────────────────────────────────────────┐
│  ◑ MiMi Nox v2.0.0                              [✕]               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Wähle dein Modell                                                │
│  Welches KI-Modell soll MiMi Nox verwenden?                       │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ◉ gemma4:12b     (Empfohlen)                               │    │
│  │  Schneller, 100% lokal, gut für Alltag                      │    │
│  │  ≈ 8 GB RAM / VRAM                                         │    │
│  │  [▶ Jetzt herunterladen] (14.2 GB)                         │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ○ llama3.3:70b      (Leistungsstark)                             │
│  Stark für komplexe Aufgaben, langsamer                           │
│  ≈ 40 GB RAM / VRAM                                              │
│  [▶ Herunterladen] (42 GB)                                       │
│                                                                    │
│  ○ custom            (Eigenes Ollama-Modell)                      │
│  Gib eine Modell-Namen ein, das bereits auf deinem               │
│  Ollama-Server installiert ist                                    │
│  [────────────────────────────]                                    │
│  [Speichern]                                                      │
│                                                                    │
│  [← Zurück]                  [Weiter →]                            │
│                                                                    │
│  ─○───●────○───  2 von 3                                         │
└────────────────────────────────────────────────────────────────────┘
```

#### Schritt 3: Erster Chat + Customization

```
┌────────────────────────────────────────────────────────────────────┐
│  ◑ MiMi Nox v2.0.0                              [✕]               │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  Fast fertig!                                                     │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ✨ Personalisiere deine Erfahrung                          │    │
│  │                                                             │    │
│  │  Name der Assistentin [MiMi Nox          ]                  │    │
│  │  (Optional: Gib MiMi Nox einen persönlichen Namen)         │    │
│  │                                                             │    │
│  │  System-Prompt (optional):                                 │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │ Du bist MiMi Nox, ein hilfsbereiter lokaler KI-     │   │    │
│  │  │ Assistent. Du antwortest auf Deutsch, es sei denn   │   │    │
│  │  │ der User schreibt auf Englisch.                     │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │  [Standard-Prompt wiederherstellen]                        │    │
│  │                                                             │    │
│  │  ┌─────────────────────────────────────────────────────┐   │    │
│  │  │ Optionen                                            │   │    │
│  │  │                                                     │   │    │
│  │  │  ☑ Memory aktivieren (semantischer Vektorspeicher)  │   │    │
│  │  │  ☑ Tool-Approval (du musst Tools bestätigen)       │   │    │
│  │  │  ☑ Sound-Benachrichtigungen bei Antwort             │   │    │
│  │  │  ☐ System-Tray beim Schließen (Hintergrund-Modus)  │   │    │
│  │  └─────────────────────────────────────────────────────┘   │    │
│  │                                                             │    │
│  │  [▶ MiMi Nox starten]  (öffnet den Chat)                   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ─○───○───●──  3 von 3                                            │
└────────────────────────────────────────────────────────────────────┘
```

---

### 2.4 SCREEN: CHAT UI (Hauptansicht — Hermes Agent Style)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  ◑ MiMi Nox                              Sessions ▾  gemma4:12b  ⚙  ─  ✕  ◻  ☐  │ ← Native Title Bar
├────────┬─────────────────────────────────────────────────────────────────────────┤
│   Sidebar  │  Main Chat Area                                         [◉] Panel  │
│  (280px)   │                                                                     │
│ ─────────  │  ─────────────────────────────────────────────────────────────────  │
│            │                                                                     │
│  [+ Neu]   │  ─────────────────────────────────────────────────────────────────  │
│            │                                                                     │
│  ───────── │  ─── Empty State (keine Nachrichten) ──────────────────────────     │
│  ◉ Projekt │  ┌─────────────────────────────────────────────────────────────┐    │
│  A         │  │                                                             │    │
│  "Neue     │  │                    ◑ MiMi Nox                              │    │
│  Sitzung"  │  │                    Dein lokaler KI-Assistent                │    │
│  0 Nachr.  │  │                    Privat · Lokal · Dein                    │    │
│            │  │                                                             │    │
│  ───────── │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │    │
│  ◉ Allgemein│ │  │ Erkläre mein │  │ Schreibe eine │  │ Analysiere  │     │
│  3 Nachr.  │  │ │ dein Projekt  │  │ E-Mail       │  │ dieses Bild │     │
│  Gestern    │  │ └──────────────┘  └──────────────┘  └──────────────┘     │    │
│            │  │                                                             │    │
│  ◉ Forschung│ │  ┌──────────────┐  ┌──────────────┐                          │    │
│  7 Nachr.  │  │ │ Suche Online │  │ Code Review  │                          │    │
│  Gestern    │  │ └──────────────┘  └──────────────┘                          │    │
│            │  └─────────────────────────────────────────────────────────────┘    │
│  ───────── │                                                                     │
│  └─ Suche  │                                                                     │
│  Sitzung  │  ─── Mit Nachrichten ────────────────────────────────────────────     │
│            │                                                                     │
│  ┌────────┐│  👤  ───────────────────────────────────────────────────────        │
│  ◉ Projekt│ │  [Deine Nachricht erscheint hier als grüne Blase rechts]           │
│  A       │ │  [Time: 14:32]                                                      │
│  └────────┘│                                                                     │
│            │  ◑  ──────────────────────────────────────────────────────           │
│            │  [Antwort von MiMi Nox als subtile glass bubble links]                │
│            │  [Time: 14:32]                                                        │
│            │                                                                     │
│            │  ─── Markdown-Output Beispiel ──────────────────────────────────      │
│            │  ```python                                                            │
│            │  def hello():                                                         │
│            │      print("Hello, World!")                                           │
│            │  ```                                                                  │
│            │  [Copy code]                                                          │
│            │                                                                     │
│            │  ─── Tool Call Beispiel ──────────────────────────────────────────     │
│            │  🔧 Shell: ls -la /Users/sanji/project                               │
│            │  Status: ✓ Completed · [Ergebnis anzeigen]                            │
│            │                                                                     │
│            │                                                                     │
│            │  ─────────────────────────────────────────────────────────────────  │
│            │  ┌─────────────────────────────────────────────────────────────┐    │
│            │  │ 📎 🖼️ 🎤 📄 ✦  Schreibe eine Nachricht...            [Send]│    │
│            │  └─────────────────────────────────────────────────────────────┘    │
│            │  gemma4:12b  ·  Lokal  ·  Connected ✓                              │
│            │                                                                     │
├────────┴─────────────────────────────────────────────────────────────────────────┤
│  [◌ MiMi Nox]  [📊 System]  [⚙ Einstellungen]               [⚿] [✕]           │ ← macOS Traffic Lights
└──────────────────────────────────────────────────────────────────────────────────┘

NOTIZ: Auf macOS sollte die Title Bar **custom** sein (Tauri: `decorations: false` 
oder `titleBarStyle: "Overlay"`), damit das Design konsistent mit dem App-Design ist, 
nicht mit dem OS-Chrome. So verhält es sich wie ChatGPT oder Notion — die Title Bar 
verschmilzt mit dem App-Design.
```

#### Key Layout-Entscheidungen:

| Element | Design | Begründung |
|---------|--------|------------|
| **Title Bar** | Custom (nicht native OS-Bar) | Wie ChatGPT/Notion — versmilzt mit App-Design. macOS `titleBarStyle: "Overlay"` oder `custom`. Zeigt "◑ MiMi Nox" + Model-Selector + Window Controls |
| **Sidebar** | 280px fix, nicht resizebar | ChatGPT tut es auch nicht. Platz reicht. Wenn User mehr Platz will → Sidebar expand/collapse mit `Cmd+B` |
| **Chat Width** | Max 720px (28ch) zentriert | wie ChatGPT — optimale Lesbarkeit. Nicht fullscreen. |
| **Input Height** | Auto-resize 44px → max 200px | Wie ChatGPT. Enter = Senden, Shift+Enter = Newline |
| **Model Selector** | Im Header, dropdown | `gemma4:12b ▾` — klappbar, zeigt alle Ollama-Modelle |
| **Tool-Approval** | Inline im Chat (nicht Panel) | Wie Hermes Agent: Tool-Call erscheint als eigene Message mit Status-Badge |
| **System Tray** | Ja, per Tauri Plugin | Cmd+W → Tray, nicht Close. Rechtsklick-Tray-Menü: "Neuer Chat", "Einstellungen", "Beenden" |
| **Keyboard Shortcuts** | Cmd+N = New Chat, Cmd+B = Sidebar, Cmd+K = Command Palette, Esc = Close panel | Wie ChatGPT — User erwarten diese Shortcuts |
| **Drag & Drop** | Files in Input-Field → Upload | Wie ChatGPT. Zeigt File-Preview Chips im Input |
| **Scroll Behavior** | Auto-scroll to bottom on new message | Wie alle Chat-Apps. Manual scroll-up zum Lesen zeigt "New messages" dot |

---

### 2.5 SCREEN: SETTINGS PANEL

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Settings                                    [✕]                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ────────────────────                                                       │
│                                                                             │
│  ◉ MODEL & API                                    ◉ MEMORY                 │
│  ◊ ATTACHMENTS                                     ◊ APPEARANCE             │
│  ◊ SHORTCUTS                                       ◊ ADVANCED               │
│                                                                             │
│  ──────────────────────────────────────────────────────────────────────      │
│                                                                             │
│  Model                                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  Aktuelles Modell:  gemma4:12b                  [Ändern]        │       │
│  │                                                                 │       │
│  │  Ollama Endpoint:  http://localhost:11434       [Prüfen]        │       │
│  │  (Lokal — kein API-Key nötig)                                   │       │
│  │                                                                 │       │
│  │  OpenAI Kompatibel (optional):                                  │       │
│  │  Endpoint:  [────────────────────────────]                      │       │
│  │  API Key:   [────────────────────────────]                      │       │
│  │  Modell:    [────────────────────────────]                      │       │
│  │  [Test Connection]                                              │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  ──────────────────────────────────────────────────────────────────────      │
│                                                                             │
│  Memory                                                                     │
│  ☑ Semantischen Speicher aktivieren (ChromaDB)                             │
│  ☐ Erinnerungen nach X Tagen automatisch löschen                           │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  Gespeicherte Erinnerungen: 24  │  Alle löschen [──────────]   │       │
│  │                                                                 │       │
│  │  • "Der User arbeitet mit Rust und Tauri"                       │       │
│  │  • "Präferenz: deutsche Antworten wenn nicht anders gefragt"    │       │
│  │  • "Projekt-Stack: React 19 + Vite 6 + Tailwind CSS"            │       │
│  └─────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. FEATUR-MATRIX: DESKTOP vs WEB/PWA

| Feature | Desktop (Tauri) | Web (PWA) | Begründung |
|---------|:-:|:-:|------------|
| **Chat (SSE/WS)** | ✓ | ✓ | Kernfunktionalität, beide Plattformen |
| **Session Management** | ✓ | ✓ | localStorage (Web) / SQLite (Desktop) |
| **Markdown Rendering** | ✓ | ✓ | React-Markdown, universal |
| **Code Blocks + Copy** | ✓ | ✓ | Universal |
| **File Attachments** | ✓ | ✓ | Web: drag-drop. Desktop: file-picker |
| **Image Upload** | ✓ | ✓ | Universal |
| **Voice Input (Mikro)** | ✓ | ✓ | Web Speech API + Tauri audio |
| **Tool Use (Shell/Browser)** | ✓ | ✓ | Backend-API, beide gleich |
| **Tool Approval UI** | ✓ | ✓ | Inline im Chat |
| **Memory (ChromaDB)** | ✓ | ✓ | Backend, beide gleich |
| **Model Selection** | ✓ | ✓ | Ollama API |
| **Custom OpenAI Endpoint** | ✓ | ✓ | Settings |
| **Sidebar (Session List)** | ✓ | ✓ | Zustand/LocalStorage |
| **System Tray** | ✓ | ✗ | Tauri-only: native Tray-Plugin |
| **Cmd+W → Tray** | ✓ | ✗ | Tauri window events |
| **Native Menu Bar** | ✓ | ✗ | Tauri menu plugin |
| **File System Access** | ✓ | ✗ | Tauri fs + open plugin |
| **OS Clipboard Monitoring** | ✓ | ✗ | Tauri clipboard plugin |
| **Screenshot Capture** | ✓ | ✗ | Tauri shell exec |
| **Auto-Update** | ✓ | ✗ | Tauri updater plugin (wird konfiguriert) |
| **Notarization/Signing** | ✓ | ✗ | Tauri build process |
| **PWA Install** | ✗ | ✓ | manifest.json + service worker |
| **Offline Cache** | ✗ | ✓ | Service Worker (PWA-only) |
| **Native Notifications** | ✓ | ✓ |两者 haben Notification API |
| **Keyboard Shortcuts** | ✓ | ✓ | Browser-level |
| **Multi-Window** | ✓ | ✗ | Tauri multi-window |

**Fazit:** Desktop hat **alle Web-Features PLUS** native OS-Features. Web ist die "Minimum Viable Experience".

---

## 4. KOMPONENTEN-ARCHITEKTUR (erweitert)

```
src/
├── main.tsx                          # Entry Point
├── App.tsx                           # Router (Landing / Onboarding / Chat)
├── index.html
├── styles/
│   └── globals.css                   # Design tokens, liquid-glass, animations
│
├── pages/
│   ├── LandingPage.tsx               # Web Landing Page (public)
│   ├── ChatPage.tsx                  # Chat UI (app)
│   └── OnboardingPage.tsx            # NEU: 3-Schritt Setup Wizard
│
├── components/
│   ├── ui/                           # Primitives (Button, Card, Badge, Input, Dialog, Tooltip, DropdownMenu)
│   ├── landing/                      # Web Landing components
│   │   ├── HeroSection.tsx
│   │   ├── FeaturesSection.tsx
│   │   ├── ArchitectureSection.tsx
│   │   ├── SkillsSection.tsx
│   │   ├── CTASection.tsx            # → Wird zu PlatformSelector
│   │   └── Footer.tsx
│   ├── onboarding/                   # NEU: Onboarding components
│   │   ├── OnboardingWizard.tsx      # 3-Schritt Wizard mit Progress
│   │   ├── OllamaCheck.tsx           # Step 1: Ollama detection
│   │   ├── ModelSelector.tsx         # Step 2: Modell-Auswahl
│   │   └── FirstChatSetup.tsx        # Step 3: Name, System-Prompt, Options
│   ├── dashboard/
│   │   ├── ChatLayout.tsx            # Main chat container
│   │   ├── Sidebar.tsx               # Session list
│   │   ├── ChatInput.tsx             # Message input with attachments
│   │   ├── MessageBubble.tsx         # User/assistant/system messages
│   │   ├── TypingIndicator.tsx       # "denkt nach..."
│   │   ├── WelcomeEmptyState.tsx     # NEU: benannt, wie ChatGPT empty
│   │   ├── MarkdownRenderer.tsx      # NEU: react-markdown wrapper
│   │   ├── CodeBlock.tsx             # NEU: syntax-highlighted code with copy
│   │   ├── ToolCallDisplay.tsx       # NEU: Tool-approval + status display
│   │   ├── ModelSelectorHeader.tsx   # NEU: model dropdown in header
│   │   ├── AttachmentPreview.tsx     # NEU: file chips in input
│   │   └── SettingsPanel.tsx         # NEU: settings as right panel or modal
│   └── layout/
│       ├── AppShell.tsx              # NEU: top-level shell (sidebar + main + panels)
│       └── WindowControls.tsx        # NEU: custom window controls (macOS)
│
├── store/
│   └── chatStore.ts                  # Zustand store
│
├── hooks/
│   ├── useInView.ts
│   └── useLocalStorage.ts
│
├── lib/
│   ├── api.ts                        # REST API client
│   ├── websocket.ts                  # WSClient
│   └── utils.ts                      # Helpers
│
└── types/
    └── index.ts                      # NEU: shared TypeScript types
```

---

## 5. STATE-MANAGEMENT ERWEITERUNG

Der existierende Zustand (`chatStore.ts`) muss erweitert werden:

```typescript
// chatStore.ts — NEUE Interfaces

interface OnboardingState {
  step: 0 | 1 | 2 | 3  // 0 = nicht gestartet, 1/2/3 = Schritt, 99 = abgeschlossen
  ollamaInstalled: boolean | null
  ollamaVersion: string | null
  selectedModel: string
  memoryEnabled: boolean
  toolApprovalEnabled: boolean
  trayEnabled: boolean
  systemPrompt: string
  assistantName: string
}

// Neue actions in chatStore:
completeOnboarding(): void
setOnboardingStep(step: number): void
setModelSelection(model: string): void
```

Zustand wird in `localStorage` mit einem `persist`-Middleware gespeichert, um den Onboarding-Status zu erhalten.

---

## 6. TAUARI-SIDE: NEUE RUST COMMANDS

```rust
// src-tauri/src/main.rs — NEUE Tauri Commands

#[tauri::command]
fn check_ollama_installed() -> Result<OllamaStatus, String> {
    // Prüft `which ollama` oder Registry (Windows)
    // Gibt zurück: { installed: bool, version: Option<String> }
}

#[tauri::command]
fn check_ollama_model(model: &str) -> Result<ModelStatus, String> {
    // Ruft `ollama list` auf und prüft ob Modell existiert
}

#[tauri::command]
fn ollama_pull_model(model: &str) -> Result<(), String> {
    // Führt `ollama pull <model>` aus, streamed Progress
}

#[tauri::command]
fn open_file_picker() -> Result<Option<Vec<String>>, String> {
    // Tauri FilePicker API — für File Attachments
}

#[tauri::command]
fn get_supported_models() -> Result<Vec<String>, String> {
    // Ruft Ollama API `http://localhost:11434/api/tags` ab
}
```

---

## 7. ZEIT-SCHÄTZUNG

### Phase 1: Landing Page & Plattform-Wahl (1-2 Tage)

| Task | Aufwand |
|------|---------|
| CTASection → PlatformSelector umschreiben (macOS/Windows/Linux/Web) | 2h |
| Download-Links konfigurieren (GitHub Releases per Platform) | 1h |
| Landing Page Routing prüfen (Web vs App-Detection) | 1h |
| **Subtotal** | **4h** |

### Phase 2: Onboarding Wizard (2-3 Tage)

| Task | Aufwand |
|------|---------|
| `OnboardingPage` mit 3-Schritt Wizard (Router-View) | 4h |
| `OllamaCheck` — Tauri `check_ollama_installed` command + UI | 3h |
| `ModelSelector` — Ollama API `tags` endpoint + download | 3h |
| `FirstChatSetup` — Name, System-Prompt, Options | 2h |
| Zustand-Persistenz (localStorage via Zustand persist) | 1h |
| **Subtotal** | **13h** |

### Phase 3: Chat UI Overhaul (3-4 Tage)

| Task | Aufwand |
|------|---------|
| `AppShell` — neues Layout (Sidebar fix + main + optional panel) | 3h |
| `WelcomeEmptyState` — ChatGPT-style Empty State | 2h |
| `MarkdownRenderer` — react-markdown + rehype-highlight | 2h |
| `CodeBlock` — Syntax-Highlighting + Copy-Button | 2h |
| `ToolCallDisplay` — Tool-Approval inline im Chat | 3h |
| `ModelSelectorHeader` — Model-Dropdown im Header | 2h |
| Chat-Input Verbessern (auto-resize, drag-drop, file chips) | 3h |
| Markdown im Chat-Live (streaming → markdown render) | 2h |
| **Subtotal** | **17h** |

### Phase 4: Native Features (3-4 Tage)

| Task | Aufwand |
|------|---------|
| Tauri: Custom Title Bar (Overlay/Transparent) | 2h |
| Tauri: System Tray (Cmd+W → Tray) | 2h |
| Tauri: Native Menu Bar (macOS/Win) | 2h |
| Tauri: FilePicker für Attachments | 1.5h |
| Tauri: Window Controls Overlay (custom close/min/max) | 1.5h |
| Tauri: Auto-update setup (tauri-plugin-updater) | 3h |
| **Subtotal** | **12h** |

### Phase 5: Settings & Polish (2-3 Tage)

| Task | Aufwand |
|------|---------|
| Settings Panel (rechts, als Slide-over Panel) | 3h |
| Settings: Model, API, Memory, Appearance | 3h |
| Keyboard Shortcuts (Cmd+N, Cmd+B, Cmd+K, Esc) | 2h |
| Scroll behavior, "New messages" dot | 1h |
| Toast-Notifications (Tauri Plugin) | 1h |
| Animation-Passing (framer-motion für Sidebar, Panel) | 2h |
| **Subtotal** | **12h** |

### GESAMT

| Phase | Tage | Stunden |
|-------|------|---------|
| 1. Landing Page & Plattform-Wahl | 1-2 | 4h |
| 2. Onboarding Wizard | 2-3 | 13h |
| 3. Chat UI Overhaul | 3-4 | 17h |
| 4. Native Features | 3-4 | 12h |
| 5. Settings & Polish | 2-3 | 12h |
| **TOTAL** | **~2-3 Wochen** (einzige Person, parallel) | **~50-55h** |

### Priorisierung (MVP-Flow)

```
P0 (Kern-Erfahrung, Week 1):
  ✓ Landing Page mit Plattform-Wahl
  ✓ Onboarding: Ollama Check + Modell-Auswahl
  ✓ Chat UI: Basic + Markdown + Code-Blocks
  ✓ Sidebar + Session Management

P1 (Native Plus, Week 2):
  ✓ System Tray + CmdW → Tray
  ✓ Native Menu Bar
  ✓ File Picker (Attachments)
  ✓ Model-Selector Header

P2 (Polish, Week 3):
  ✓ Settings Panel
  ✓ Keyboard Shortcuts
  ✓ Custom Title Bar
  ✓ Auto-update

P3 (Nice-to-Have):
  ⬚ Light Mode
  ⬚ Multi-Window
  ⬚ Clipboard Monitoring
  ⬚ Screenshot Capture
```

---

## 8. RISK & MITIGATION

| Risiko | Auswirkung | Mitigation |
|--------|-----------|------------|
| **Ollama nicht installiert** | Onboarding blockiert | Klarer, Copy-Paste Install-Anleitung. Auto-Install-Option über Tauri shell. |
| **Modell-Download groß (14GB+)** | Langsam, User bricht ab | Progress-Bar im Onboarding. Download im Background (Tauri spawn). Pause/Resume. |
| **Windows Ollama-Path nicht in PATH** | Check schlägt fehl | Windows-spezifische Registry-Prüfung (`HKEY_CURRENT_USER\Software\Ollama`). |
| **Linux Distribution-Vielfalt** | Install-Befehl variiert | Distro-Erkennung via `cat /etc/os-release` und angepasste Befehle. |
| **Tauri 2 Plugin-Kompatibilität** | Breaking Changes | Tauri 2.6+ stabil. Plugins: tray, menu, fs, dialog, shell, updater. |
| **macOS Notarization** | App wird blockiert | Signierung mit Developer ID, Notarization-Stapelsubmission im CI/CD. |
| **Memory-Leaks im React** | Langsame App über Zeit | `react-compiler`, Memory-Management im `conversation_compactor` (Python). |

---

## 9. EMPFOHLENE ERSTE SCHRITTE (FÜR ENTWICKLER)

```bash
# 1. Dependencies für Markdown/Highlighting hinzufügen
cd /Users/sanji/mimi-nox/app
npm install react-markdown rehype-highlight remark-gfm

# 2. Onboarding-Route in App.tsx hinzufügen
# Route: /onboarding (falls Onboarding noch nicht abgeschlossen)
# Route: /chat (Haupt-Chat, nur falls Onboarding abgeschlossen)

# 3. Tauri Commands für Ollama-Check schreiben
# src-tauri/src/lib.rs → neue Commands: check_ollama_installed, get_supported_models

# 4. Platform Selector in CTASection umschreiben
# Die bestehende CTASection wird zur PlatformSelector-Komponente

# 5. ChatGPT-Style Empty State erstellen
# WelcomeEmptyState.tsx mit zentriertem Design wie ChatGPT
```

---

*Erstellt: 2025-07-25*  
*Basis: Existierender Codebase-Scan von mimi-nox/app (React 19/Vite 6) und src-tauri (Tauri 2.11)*  
*UI-Ziel: Hermes Agent / ChatGPT Ästhetik — dunkel, minimalistisch, fokusiert*
# MiMi Nox Desktop App — UX/Design Plan
## Hermes Agent Style Chat UI

> **Status:** Plan-Phase | **Erstellt:** 2025-07-25
> **Ziel:** Desktop-App (Tauri) mit UX-Qualität von Hermes Agent + ChatGPT

---

## 0. Zusammenfassung & Vision

MiMi Nox wird von einer Web-PWD zu einer **native-feelenden Desktop-App** mit professioneller Chat-UI. Das Ziel ist ein Produkt, das beim Start sofort wie **Hermes Agent** oder **ChatGPT** aussieht — einladend, performant, intuitiv. Das bestehende Schwarzwald-Theme (Schwarz + Forest-Green) wird beibehalten, aber professionalisiert: weniger "effekt-lastig", mehr "premium-tool".

### Kernentscheidung
> **Layout:** Sidebar-left (collapsible) + Main-Chat-Area — exakt wie Hermes Agent.
> **Begründung:** Die Sidebar ist der Industriestandard für Chat-Apps (ChatGPT, Claude, Gemini, Hermes). Sie bietet Raum für Sessions, Tools, Settings, und ist auf Desktop unverzichtbar. Ein zentrierter Chat allein (wie Perplexity) wäre für eine **Tool-Use-App** unzureichend — man braucht Kontext-Management.

---

## 1. UI/UX Design Plan

### 1.1 Layout-Struktur

```
┌─────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════╗  │  ← Custom Title Bar (Tauri)
│  ║  🌲 MiMi Nox               🔍 Suche  ⚙️  ◑  10:42  ▤  ║  │      System Chrome
│  ╚═══════════════════════════════════════════════════════════╝  │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                      │
│ Sidebar  │  Hauptbereich (Chat / Welcome / Tools)               │
│ (260px)  │                                                      │
│          │  ┌──────────────────────────────────────────┐        │
│ + Neue   │  │  🌲 Hi, hier ist MiMi Nox               │        │
│ Chat     │  │  Wähle einen Vorschlag oder schreibe...  │        │
│          │  │                                          │        │
│ ● Chat 1 │  │  [Erkläre Projekt]  [Schreibe E-Mail]   │        │
│   12 Msg │  │  [Analysiere Bild]  [Online Suche]      │        │
│          │  └──────────────────────────────────────────┘        │
│ ● Chat 2 │                                                      │
│   45 Msg │  ← Scrollbarer Chat-Bereich                         │
│          │                                                      │
│ ● Chat 3 │  ┌──────────────────────────────────────────┐        │
│   3 Msg  │  │ 📎 🖼️ 🎤 📄 | Nachricht schreiben...  ➤ │        │
│          │  │      gemma4:12b · Lokal · Verbunden      │        │
│ ───────  │  └──────────────────────────────────────────┘        │
│ + Tool   │                                                      │
│ + Skill  │                                                      │
│          │                                                      │
│ Settings │                                                      │
│ Model    │                                                      │
│ Docs     │                                                      │
├──────────┴──────────────────────────────────────────────────────┤
│  Statusleiste:  ◑ 12b · 23°C CPU · RAM 1.2GB · v2.0.0         │
└─────────────────────────────────────────────────────────────────┘
```

#### Layout-Entscheidungen:

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Sidebar breiten | 260px (collapsible zu 60px) | Genug Platz für Session-Titel + Nachrichtenanzahl, aber nicht dominierend. Collapsible für maximale Chat-Breite. |
| Header in Chat | Minimal (nur Model-Info, Search, Settings) | Wie ChatGPT: der Header sollte nicht ablenken. Model-Picker und Settings gehören hierher. |
| Title Bar | Native OS Chrome (nicht custom HTML) | Tauri kann nativen Frame nutzen — das gibt native Context-Menüs, Cmd+K, etc. Custom Title Bar ist overkill. |
| Chat-Max-Width | 720px (centered) | Wie ChatGPT/Hermes: optimaler Zeilenumfang für Lesbarkeit. Full-width wäre bei langen Texten schlecht. |
| Input-Position | Fixed bottom, immer sichtbar | Standard-UX bei allen Chat-Apps. Muss nicht scrollen um zu tippen. |
| Footer | Statusleiste statt Footer | Zeigt Model, CPU/RAM (Desktop-Vorteil!), Version. Wie ein "Dashboard-Pip". |

### 1.2 Theme & Farben

Das Schwarzwald-Theme wird **professionalisiert**:

```
Primary:    #22C55E → #16A34A (weniger "hacky", mehr "premium")
Background: #000000 → #0A0A0A (tiefes Schwarz, nicht hartes #000)
Surface:    rgba(34,197,94,0.03) → rgba(255,255,255,0.03) (neutrales Glass)
Border:     rgba(34,197,94,0.1) → rgba(255,255,255,0.06) (subtiler)
Accent:     Green bleibt, aber nur noch als FOCUS-Farbe
```

**Warum diese Änderungen?**
1. **Pure Black (#000)** ist zu hart für eine Premium-App. #0A0A0A wirkt wie ChatGPT's Dark Mode: tief aber angenehm.
2. **Glass-Effekte** mit grünen Rändern wirken "hackerhaft". Mit weißen/neutralen Rändern wirken sie "produziert".
3. **Grün als Akzent** bleibt als Branding, aber zurückhaltender: nur bei Focus, Active State, und Primary-Button.
4. **Kein "Liquid Glass"** — zu sehr. Stattdessen: einfache, performante Glass-Effekte wie ChatGPT verwendet.

**Desktop-spezifische Anpassungen:**
- macOS: `backdrop-filter` mit -webkit prefix für native Translucency
- Windows: Acrylic-Backup über Tauri's `backdrop: "Acrylic"` (wird per Tauri-Config gesteuert)
- Linux: Simpler semi-transparenter Hintergrund (kein backdrop-filter auf allen Distros)

### 1.3 Navigation

```
Sidebar (erweitert):
┌────────────────┐
│ 🌲 MiMi Nox    │  ← Logo + Name (klickbar → Home)
│                │
│ + Neuer Chat   │  ← Primary Button, grün, prominent
│                │
│ ── Heute       │  ← Datum-Sektionen (wie ChatGPT)
│  ● Chat 1      │
│  ● Chat 2      │
│                │
│ ── Gestern     │
│  ● Chat 3      │
│  ● Analyse     │
│                │
│ ── Letzte Woche│
│  ● Projekt X   │
│                │
│ ── Tools       │
│  📊 Analyze    │
│  📝 Writer     │
│                │
│ ── Skills      │
│  🔧 Debug      │
│  🧠 Memory     │
│                │
│ ──             │
│  ⚙️ Einstellungen│
│  📖 Dokumentation│
│  ❓ Feedback     │
└────────────────┘

Sidebar (collapsiert zu 60px):
┌────┐
│ 🌲 │  ← Logo
│    │
│ +  │  ← "New Chat" als Icon
│    │
│ ●  │  ● = aktiver Chat (Indikator)
│ ●  │
│ ●  │
│    │
│ ─  │  ← Divider
│ 🔧 │  Tools-Icon
│ ⚙️ │  Settings-Icon
└────┘
```

**Navigation-Entscheidungen:**

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Session-Sortierung | Datum-Gruppen (Heute/Gestern/Letzte Woche) | ChatGPT hat es richtig gemacht: man findet den letzten Chat sofort |
| "Neuer Chat" Button | Immer sichtbar, oben, grün | Most-common action muss immer 1-Click erreichbar sein |
| Collapsible | Ja, mit Toggle-Button (≡ oder ┇) | Maximale Chat-Breite wenn man nur chatten will |
| Tool/Skill-Navigation | In Sidebar, unter Sessions | Desktop-Vorteil: lokale Tools/Skills sind erstklassige Navigations-Elemente |
| Keyboard Shortcut | Cmd+N = New Chat, Cmd+K = Command Palette | Industriestandard. Cmd+K wie ChatGPT/Claude/Linear |
| Cmd+K Palette | Ganzseitig, Search-Bar + Quick-Actions | Suche Sessions, Tools, Models, Commands. Wie VS Code's Go to Anything. |

### 1.4 Interaktions-Muster

#### Keyboard Shortcuts (Desktop-only, wichtig!)

```
Cmd/Ctrl + N    → Neuer Chat
Cmd/Ctrl + K    → Command Palette öffnen
Cmd/Ctrl + Shift + M  → Model wechseln
Cmd/Ctrl + ,    → Einstellungen
Cmd/Ctrl + D    → Dark/Light Toggle
Cmd/Ctrl + /    → Help / Shortcuts anzeigen
Cmd/Ctrl + L    → Sidebar toggle
Esc             → Command Palette schließen
Enter           → Nachricht senden (wenn Input focus)
Shift + Enter   → Neue Zeile
```

#### Drag & Drop
- Dateien auf Input → Datei wird angehängt (PDF, TXT, Code, Bilder)
- Dateien auf Chat → Datei wird im Chat kontextuell eingebunden
- URLs auf Chat → URL Preview wird erzeugt

#### Tool Approval (wichtigste Desktop-Interaktion)
- Tool-Call erscheint als **inline Expansion** im Chat (wie Hermes Agent)
- User sieht: Tool-Name, Args, Output (previews)
- Buttons: ✅ Approve | ❌ Deny | 👁️ Preview
- Approve: Auto-approve für sichere Tools (read_file, list_dir)
- Manual: Für riskante Tools (write, delete, execute, browser)

#### Context Menu (Right-Click)
- Nachricht → Copy, Edit, Rerender, Regenerate
- Sidebar-Entry → Rename, Delete, Duplicate
- Input-Feld → Paste File, Attach from Browser

---

## 2. Onboarding & Setup Flow

### 2.1 Gesamtübersicht

```
┌─────────────────────────────────────────────────┐
│                                                   │
│  Screen 1: Erster Start                          │
│  ┌───────────────────────────────────────────┐   │
│  │                                           │   │
│  │         🌲                                │   │
│  │         MiMi Nox                          │   │
│  │                                           │   │
│  │   Willkomen.                              │   │
│  │                                           │   │
│  │   Installiere zuerst Ollama.              │   │
│  │   Ollama ist dein lokaler Modell-Server.  │   │
│  │                                           │   │
│  │   [📥 Ollama installieren]  (macOS)       │   │
│  │   [📄 Anleitung]                           │   │
│  │                                           │   │
│  │   Ollama ist bereits installiert?         │   │
│  │   [Weiter →]                              │   │
│  │                                           │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                                                   │
│  Screen 2: Setup wird geprüft                     │
│  ┌───────────────────────────────────────────┐   │
│  │                                           │   │
│  │   Prüfe Ollama...                         │   │
│  │   ━━━━━━━━━━━━━━━━━━ ● 33%              │   │
│  │                                           │   │
│  │   ◷ Ollama gefunden: v0.5.0              │   │
│  │   ◷ gemma4:12b wird heruntergeladen...    │   │
│  │   ◷ Backend-Server wird gestartet...      │   │
│  │                                           │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│                                                   │
│  Screen 3: Welcome + Erste Nachricht              │
│  ┌───────────────────────────────────────────┐   │
│  │                                           │   │
│  │   🌲  Alles bereit!                       │   │
│  │                                           │   │   │   │   Probiere es aus:                        │   │
│  │   [Wie kann ich dir heute helfen?]         │   │
│  │                                           │   │
│  └───────────────────────────────────────────┘   │
│                                                   │
└─────────────────────────────────────────────────┘
```

### 2.2 Detaillierter Flow

#### Step 0: App-Start prüfen (automatisch)
```
1. Prüfe: Ollama läuft auf localhost:11434?
2. Prüfe: MiMi Nox Backend läuft auf localhost:8765?
3. Prüfe: gemma4:12b (oder Default-Model) vorhanden?
```

**Wenn alles da → Direkt zum Chat (Step 3)**
**Wenn nicht → Onboarding-Flow starten**

#### Step 1: Ollama-Status prüfen
```
Tauri Command: check_ollama()
- Prüft ob ollama binary existiert (which ollama)
- Prüft ob Port 11434 offen ist
- Prüft Model-Existenz (ollama list)
```

**Falls Ollama installiert:**
→ Springe zu Step 2 (Model-Check)

**Falls Ollama NICHT installiert:**
→ Zeige Installations-Button mit Plattform-spezifischem Download

| Plattform | Action | URL/Command |
|---|---|---|
| macOS | `brew install ollama` oder Download .dmg | https://ollama.com/download/mac |
| Windows | Installations-Assistant (.exe) | https://ollama.com/download/windows |
| Linux | `curl -fsSL https://ollama.com/install.sh \| sh` | https://ollama.com/download/linux |

#### Step 2: Model-Download (optional, wenn Model nicht da)
```
Tauri Command: pull_model("gemma4:12b")
- Zeigt Fortschrittsbalken
- Zeigt Speed und verbleibende Zeit
- Hintergrund-Download (App bleibt bedienbar)
```

**Warum nicht automatisch?**
- 12GB+ Download braucht Zeit
- User sollte kontrollieren können (Bandbreite, Kosten)
- Model-Auswahl sollte möglich sein (User wollen vielleicht Llama, Qwen, etc.)

#### Step 3: Model-Auswahl
```
┌──────────────────────────────────────┐
│  Welches Modell möchtest du nutzen?  │
│                                      │
│  🌟 Empfohlen:                       │
│  ┌────────────────────────────────┐  │
│  │ 🟢 gemma4:12b                  │  │
│  │ 12B Parameter · 8GB RAM        │  │
│  │ Schneller guter Standard       │  │
│  │ [✓ Ausgewählt]                 │  │
│  └────────────────────────────────┘  │
│                                      │
│  Andere Modelle:                     │
│  ○ llama4:mini  (schneller, 6GB RAM) │
│  ○ qwen3:8b     (stark, 5GB RAM)    │
│  ○ codestral:22b (Code-spezialisiert)│
│  ○ [Andere Modell...]               │
│                                      │
│  [Weiter →]                          │
└──────────────────────────────────────┘
```

#### Step 4: Erster Chat
```
- App öffnet direkt im Chat
- Willkommens-Nachricht: "Alles bereit! Wie kann ich dir helfen?"
- Suggestion-Cards wie aktuell, aber poliert
- Sidebar ist leer → "Noch keine Chats"
```

#### Step 5: Optional — Quick Setup (Settings)
Nach dem Onboarding:
```
- Model noch anpassen?
- Tools aktivieren/deaktivieren?
- Memory-Feature erklären?
- TTS aktivieren?
- Sprachauswahl (DE/EN)
```

### 2.3 "Ollama schon installiert?" Flow

Wenn Ollama bereits läuft:
1. **Sofortiger Model-Check:** `ollama list` via Tauri Command
2. **Wenn Model da:** Direkt zum Chat (0 Sekunden)
3. **Wenn Model fehlt:** Nur Model-Download zeigen
4. **Feedback:** "Ollama erkannt! Lade nur noch das Model..."

**Warum dieser Flow?**
- Die meisten frühen Nutzer haben Ollama schon
- Der Flow muss < 3 Sekunden fühlen für "ready"-User
- Nur Ollama-Install-Flow ist "warm"

---

## 3. Landing Page — Plattform-Wahl

### 3.1 Aktuelle Situation
Die aktuelle Landing Page (LandingPage.tsx) ist eine Marketing-Seite:
- Hero mit Video-Background
- Feature-Section, Architecture-Section, Skills-Section
- CTA-Section mit "Jetzt installieren" + GitHub-Link
- **Problem:** Keine Plattform-Auswahl. Ein "Jetzt installieren" Button weiß nicht wohin.

### 3.2 Neue Landing Page-Struktur

```
┌─────────────────────────────────────────────────────────────┐
│  NAV:  ◑ MiMi Nox     Funktionen     Tools     GitHub  ⬇  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  HERO (wie bisher, aber mit Plattform-CTA)                  │
│                                                             │
│  ◑ MiMi Nox                                                 │
│  Dein lokaler KI-Assistent                                  │
│  Privat. Lokal. Dein.                                       │
│                                                             │
│  curl -fsSL ... | bash                                       │
│  [Copy]                                                      │
│                                                             │
│  ┌──────────┐  ┌─────────────┐                             │
│  │  Install  │  │  Web nutzen  │                             │
│  └──────────┘  └─────────────┘                             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INSTALLATION — Wähle deine Plattform                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│  │ 🍎 macOS   │ │ 🪟 Windows │ │ 🐧 Linux   │              │
│  │            │ │            │ │            │              │
│  │ Apple Silicon        │ x86_64 / ARM64     │              │
│  │ Universal Binary     │ .deb / .rpm        │              │
│  │ .dmg / .zst          │ .AppImage           │              │
│  │                    │              │              │
│  │ [Download →]       │ [Download →] │ [Download →] │              │
│  │ ~45 MB              │ ~52 MB          │ ~48 MB          │              │
│  └────────────┘ └────────────┘ └────────────┘              │
│                                                             │
│  Oder nutze die Web-App im Browser:                         │
│  ┌────────────────────────────────────────────┐             │
│  │  🌐   MiMi Nox Web — Jede Plattform        │             │
│  │   Funktioniert mit Chrome, Firefox, Edge   │             │
│  │   [Web-App öffnen →]                        │             │
│  └────────────────────────────────────────────┘             │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  FEATURES (wie bisher, aber komprimierter)                  │
│  ─ 100% Offline    ─ Tool-Use    ─ Skills    ─ Memory      │
├─────────────────────────────────────────────────────────────┤
│  FOOTER                                                       │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Plattform-Detektion & Download-Logik

```javascript
function getPlatformInfo() {
  const ua = navigator.userAgent
  const isMac = /Mac|iPhone OS/.test(ua)
  const isWin = /Windows/.test(ua)
  const isLinux = /Linux/.test(ua)
  const isARM = /ARM|aarch64|arm64/.test(ua) || (navigator.hardwareConcurrency <= 4 && isMac)

  return {
    macOS: isMac,
    Windows: isWin,
    Linux: isLinux,
    arch: isARM ? 'aarch64' : 'x86_64',
    primary: isMac ? 'macOS' : isWin ? 'Windows' : isLinux ? 'Linux' : 'Web'
  }
}

// Download-URLs (Beispiele — müssen mit Release-Infrastruktur synchronisiert werden)
const DOWNLOADS = {
  macos_arm64: 'https://releases.miminox.app/v2.0.0/miminox-darwin-arm64.dmg',
  macos_x64:   'https://releases.miminox.app/v2.0.0/miminox-darwin-x64.dmg',
  windows:     'https://releases.miminox.app/v2.0.0/miminox-setup.exe',
  linux_rpm:   'https://releases.miminox.app/v2.0.0/miminox-linux-x86_64.rpm',
  linux_deb:   'https://releases.miminox.app/v2.0.0/miminox-linux-x86_64.deb',
  linux_appimage: 'https://releases.miminox.app/v2.0.0/miminox.AppImage',
  web:         'https://app.miminox.app'  // PWA
}
```

**Entscheidungen:**

| Entscheidung | Wahl | Begründung |
|---|---|---|
| Plattform-Detektion | JS + navigator.userAgent | Clientseitig, kein Server-Req. Tauri kann es noch präziser machen (platform API). |
| Auto-Download der primären Plattform | Ja, mit "Detect" | User will nicht klicken — App soll wissen was sie braucht. |
| "Detect" Button | Ja, unter den Platform-Cards | Falls Auto-Detect falsch ist (z.B. VM), kann man manuell wählen. |
| App-Size Anzeige | Ja, bei jedem Download | Transparenz schafft Vertrauen (~45-52 MB). |
| Web-PWA als Option | Ja, separate Sektion | Nicht jeder will eine Desktop-App. PWA ist 0-Install-Option. |
| Linux: 3 Formate | DEB, RPM, AppImage | Cover 95%+ der Linux-Distributionen. |
| macOS: 2 Builds | ARM64 + x86_64 | Apple Silicon ist Standard, aber Intel-Macs noch relevant. |

### 3.4 Tauri-integrierte Download-Experience

Wenn die App bereits als Desktop-App läuft, kann sie **Auto-Update** prüfen:

```rust
// Tauri Command: check_for_updates()
// Prüft: latest release auf GitHub / CDN
// Zeigt: Update-Dialog in-app
// Installiert: silent background (macOS/Windows) oder manuell (Linux)
```

**Warum nicht einfach Download-Links?**
- Desktop-Apps sollten selbst updaten können
- Tauri hat `tauri-plugin-updater` — das ist der Standard
- Auto-Update = Premium-Feel

---

## 4. Feature-Matrix: Desktop vs Web

### 4.1 Feature-Vergleich

```
┌──────────────────────────────────┬──────────┬────────┬────────────────┐
│ Feature                          │ Desktop  │  Web   │ Begründung     │
├──────────────────────────────────┼──────────┼────────┼────────────────┤
│ Lokaler Ollama Connect           │ ✅       │ ✅     │ Backend API    │
│ Tool-Use & Approval              │ ✅       │ ✅     │ WS/REST API    │
│ Session Management               │ ✅       │ ✅     │ Memory Store   │
│ Memory (langfristiges)           │ ✅       │ ✅     │ Backend      │
│ File Attachments                 │ ✅       │ ⚠️     │ Desktop: FS    │
│ Drag & Drop Dateien              │ ✅       │ ✅     │ Both support   │
│ TTS (Text-to-Speech)             │ ✅       │ ⚠️     │ Desktop nativ  │
│ System-Integration                │ ✅       │ ❌     │ Clipboard, FS  │
│ Auto-Update                      │ ✅       │ ❌     │ Desktop only   │
│ Background-Process                │ ✅       │ ❌     │ Tauri Cap.     │
│ Custom File Protocols             │ ✅       │ ❌     │ URL Schemes    │
│ Native Keyboard Shortcuts         │ ✅       │ ⚠️     │ Global shorts  │
│ Hardware Info (CPU, RAM, GPU)    │ ✅       │ ❌     │ Tauri Info     │
│ PWA Installierbar                 │ ❌       │ ✅     │ Web only       │
│ Browser-Sharing (Link)            │ ❌       │ ✅     │ Web only       │
│ Mobile (iOS/Android)              │ ❌       │ ✅     │ Web only       │
│ Model-Auswahl UI                  │ ✅       │ ✅     │ Beide        │
│ Skill-Management                  │ ✅       │ ✅     │ Backend      │
│ Web-Suchen (optional)            │ ✅       │ ✅     │ Opt-in      │
│ OpenAI-compatible Provider       │ ✅       │ ✅     │ Backend      │
│ Theme Switch (Dark/Light)        │ ✅       │ ✅     │ CSS Variablen  │
│ Sidebar Collapse                 │ ✅       │ ⚠️     │ Desktop UX    │
│ Command Palette (Cmd+K)          │ ✅       │ ✅     │ JS Implement.  │
│ Desktop Notifications            │ ✅       │ ⚠️     │ Browser API    │
│ Clipboard Monitoring              │ ✅       │ ❌     │ Desktop API    │
│ File-Read (System)               │ ✅       │ ❌     │ Tauri FS     │
│ Process Execution                 │ ✅       │ ❌     │ Tauri Cmd    │
│ System Tray Integration           │ ✅       │ ❌     │ Desktop only   │
│ Window State (persist)            │ ✅       │ ✅     │ Tauri/Storage  │
│ Multi-Monitor Support             │ ✅       │ ⚠️     │ Desktop      │
│ HiDPI / Retina Native             │ ✅       │ ✅     │ Both        │
│ Offline-First                     │ ✅       │ ✅     │ PWA Cache    │
│ Windows App Signing               │ ✅       │ ❌     │ Desktop      │
│ Notarization (macOS)              │ ✅       │ ❌     │ Desktop      │
└──────────────────────────────────┴──────────┴────────┴────────────────┘

✅ = Full Support    ⚠️ = Limited/Polyfill    ❌ = Not Available
```

### 4.2 Desktop-Only Features (priorisiert)

| Feature | Aufwand | Priority | Warum Desktop-Only |
|---|---|---|---|
| **Auto-Update** | Niedrig (tauri-plugin-updater) | P0 | Premium-UX, kein manuelles Update |
| **Hardware Info Panel** | Niedrig | P1 | User sieht: CPU, RAM, GPU — wie ein Dashboard |
| **Global Keyboard Shortcuts** | Mittel | P1 | Cmd+N global, auch wenn App im Hintergrund |
| **System Tray** | Niedrig | P1 | Minimize-to-tray, Quick-Chat aus Tray |
| **File Protocol Handler** | Mittel | P2 | `miminox://` URL-Schema für Sharing |
| **Clipboard Monitor** | Mittel | P2 | Eingefügter Text automatisch als Prompt |
| **Desktop Notifications** | Niedrig | P2 | "Antwort fertig!" wenn App minimiert |

### 4.3 Sync-Strategie (Desktop ↔ Web)

```
Desktop ←→ Local Filesystem ←→ Backend (localhost:8765)
                                    ↕ (optional: cloud sync)
Web ←→ Browser Storage (IndexedDB) ←→ Backend (cloud/remote)
```

**Sync-Modell (Phase 1 — MVP):**
- Desktop: 100% local. Keine Cloud. Keine Sync.
- Web: 100% local (IndexedDB). Keine Cloud.
- **Keine Sync zwischen Desktop und Web** — bewusst, weil MiMi Nox's USP ist: 100% lokal, kein Account.

**Sync-Modell (Phase 2 — Optional):**
- Optionaler End-to-End encrypted Sync via selbst-hosted Server
- User bringt ihren eigenen Server mit (Self-hosted)
- Sessions werden verschlüsselt synchronisiert
- **Niemals** standardmäßig aktiv

**Warum keine Auto-Sync?**
- MiMi Nox's Brand Promise: "Privat. Lokal. Dein."
- Cloud-Sync untergräbt das Vertrauen
- Wenn User Sync wollen → sie müssen es explizit konfigurieren

---

## 5. Screen-by-Screen Wireframe-Beschreibungen

### Screen 1: Landing Page (Web)
```
┌─ Header: ◑ MiMi Nox | Features | Tools | GitHub | [Install ▼] ─┐
│                                                                 │
│  ┌─ Hero Section ────────────────────────────────────────────┐ │
│  │  ◑ MiMi Nox  (groß, gradient, mit Blur-Animation)        │ │
│  │  Dein lokaler KI-Assistent                                │ │
│  │  Privat. Lokal. Dein. 100% offline.                       │ │
│  │                                                           │ │
│  │  ┌─ Command-Block ─────────────────────────────────────┐  │ │
│  │  │ curl -fsSL ... | bash                                │  │ │
│  │  │ [Copy] [▶ Demo Watch]                                │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                           │ │
│  │  [Installieren ▼]  [▶ Demo Video]  [GitHub]              │ │
│  │  7,000+ Users · 100% Offline · Apache 2.0                │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Platform Selector ──────────────────────────────────────┐  │
│  │  Wähle deine Plattform:                                   │  │
│  │  [🍎 macOS] [🪟 Windows] [🐧 Linux] [🌐 Web/PWA]         │  │
│  │  (jeweils mit Arch, Size, Format)                         │  │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Features (4 Cards) ─────────────────────────────────────┐  │
│  │  💻 100% Offline    🛠️ Tool-Use     🧠 Memory     🔒 Secure │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Skills Section (3-4 featured) ──────────────────────────┐  │
│  │  Zeige die wichtigsten Skills: Debug, Write, Analyze      │  │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ CTA ──────────────────────────────────────────────────────┐ │
│  │  Starte jetzt mit MiMi Nox                                  │ │
│  │  [Installieren] [Dokumentation]                             │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─ Footer ───────────────────────────────────────────────────┐ │
│  │  MiMi Nox · GitHub · License · Docs · Blog                 │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Screen 2: Onboarding — Ollama Install
```
┌─ MiMi Nox (Tauri Window — System Chrome) ──────────────────────┐
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │                        ◑                                  │  │
│  │                  MiMi Nox Setup                           │  │
│  │                                                           │  │
│  │  ─────────────────────────────────────────────────────    │  │
│  │                                                           │  │
│  │  ⚠️  Ollama ist nicht installiert                         │  │
│  │                                                           │  │
│  │  MiMi Nox benötigt Ollama als lokalen Modell-Server.      │  │
│  │  Ollama ist Open Source und läuft 100% lokal.             │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │  📥 Ollama für macOS installieren                   │   │  │
│  │  │  ─────────────────────────────────────────────────  │   │  │
│  │  │  Öffnet den Download von ollama.com                 │   │  │
│  │  │  ~20 MB · Offizieller Installer                     │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  Oder manuell installieren:                                │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │  brew install ollama                                 │  │  │
│  │  │  [Copy] [▶]                                         │  │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  Ollama ist bereits installiert?                           │  │
│  │  [Weiter ohne Ollama →]  (nur für Remote-Models)         │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Progress: 0% ████████░░░░░░░░░░  Ollama wird geprüft...       │
└─────────────────────────────────────────────────────────────────┘
```

### Screen 3: Onboarding — Model-Auswahl
```
┌─ MiMi Nox Setup ───────────────────────────────────────────────┐
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │  ◑  Wähle dein Modell                                     │  │
│  │                                                           │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │  🌟 Empfohlen                                       │   │  │
│  │  │                                                     │   │  │
│  │  │  ◉ gemma4:12b              ━━━━━━ 100% ●           │   │  │
│  │  │  12B Parameter · ~8GB RAM · Schnell & stark         │   │  │
│  │  │  Download: 7.2 GB · ~2 Min                          │   │  │
│  │  │                                                     │   │  │
│  │  │  ☐ llama4:mini               (schneller, 6GB RAM)   │   │  │
│  │  │  ☐ qwen3:8b                    (stark, 5GB RAM)     │   │  │
│  │  │  ☐ codestral:22b               (Code-Specialist)    │   │  │
│  │  │  ○ models/...                  (eigenes Modell)     │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                                                           │  │
│  │  [← Zurück]              [Modell laden & Weiter →]       │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Model wird heruntergeladen: 4.3 GB / 7.2 GB  60%              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                 │
│  Geschwindigkeit: 45 MB/s · Verbleibend: 45s                    │
└─────────────────────────────────────────────────────────────────┘
```

### Screen 4: Welcome / Erster Chat
```
┌─ ── MiMi Nox ─────────────────────────────────────────────────┐│
│  ◑ MiMi Nox       🔍 Suche...              📋 ◑  14:32  ▤  ││
├──────────┬────────────────────────────────────────────────────┤│
│          │                                                     ││
│ + Neuer  │                                                     ││
│ Chat     │  ┌─────────────────────────────────────────────┐    ││
│          │  │                                             │    ││
│          │  │         ◑                                   │    ││
│          │  │         MiMi Nox                            │    ││
│          │  │         Alles bereit!                       │    ││
│          │  │                                             │    ││
│          │  │  Was kann ich für dich tun?                 │    ││
│          │  │                                             │    ││
│          │  │  ┌─────────────────┐ ┌─────────────────┐   │    ││
│          │  │  │ 📊 Analysiere   │ │ ✍️ Schreibe     │   │    ││
│          │  │  │ meinen Code     │ │ eine E-Mail     │   │    ││
│          │  │  └─────────────────┘ └─────────────────┘   │    ││
│          │  │                                             │    ││
│          │  │  ┌─────────────────┐ ┌─────────────────┐   │    ││
│          │  │  │ 🖼️ Bild-        │ │ 🔍 Suche        │   │    ││
│          │  │  │ analyse         │ │ online          │   │    ││
│          │  │  └─────────────────┘ └─────────────────┘   │    ││
│          │  └─────────────────────────────────────────────┘    ││
│          │                                                     ││
│          │  ┌─────────────────────────────────────────────┐    ││
│          │  │ 📎 🖼️ 🎤 📄  |  Wie kann ich helfen?  ✉️ │    ││
│          │  │      gemma4:12b · Lokal · Verbunden · 23°C │    ││
│          │  └─────────────────────────────────────────────┘    ││
├──────────┴────────────────────────────────────────────────────┤│
│  ◑ 12b · 🟢 Verbunden · CPU 23°C · RAM 2.1GB · v2.0.0        ││
└───────────────────────────────────────────────────────────────┘│
```

### Screen 5: Aktiver Chat (mit Tool-Use)
```
┌─ ── MiMi Nox — Chat 1 ──────────────────────────────────────┐│
│  ◑ MiMi Nox       🔍 Suche...              📋 ◑  14:35  ▤  ││
├──────────┬────────────────────────────────────────────────────┤│
│ ● Chat 1 │                                                     ││
│   8 Msg  │  👤 Du:                                           ││
│          │  "Analysiere /src/main.py"                         ││
│          │                                                     ││
│          │  ◑ MiMi Nox:                                      ││
│          │  Ich werde die Datei analysieren.                  ││
│          │                                                     ││
│          │  ┌────────────────────────────────────────────┐     ││
│          │  │ 🔧 read_file                               │     ││
│          │  │  Args: { "path": "/src/main.py" }          │     ││
│          │  │                                            │     ││
│          │  │  Result Preview:                            │     ││
│          │  │  ┌────────────────────────────────────┐    │     ││
│          │  │  │ import os                           │    │     ││
│          │  │  │ from flask import Flask             │    │     ││
│          │  │  │ ...                                  │    │     ││
│          │  │  └────────────────────────────────────┘    │     ││
│          │  │                                            │     ││
│          │  │  [✓ Approve]  [✗ Deny]  [▶ Full Preview]  │     ││
│          │  └────────────────────────────────────────────┘     ││
│          │                                                     ││
│          │  ◑ MiMi Nox:                                      ││
│          │  Ich habe die Datei gelesen. Hier ist meine        ││
│          │  Analyse: ...                                      ││
│          │                                                     ││
│          │  ┌────────────────────────────────────────────┐     ││
│          │  │ ✅ write_file                              │     ││
│          │  │  Args: { "path": "/output/report.md" }     │     ││
│          │  │  Status: ⏳ Waiting for approval            │     ││
│          │  │                                            │     ││
│          │  │  [✓ Approve]  [✗ Deny]                    │     ││
│          │  └────────────────────────────────────────────┘     ││
│          │                                                     ││
│          │  ┌────────────────────────────────────────────┐     ││
│          │  │ 📎 Report.md wurde erstellt.                │     ││
│          │  │  [Open]  [📋 Copy]  [📁 Open Folder]       │     ││
│          │  └────────────────────────────────────────────┘     ││
│          │                                                     ││
│          │  ┌────────────────────────────────────────────┐     ││
│          │  │ 📎 🖼️ 🎤 📄 | Antwort schreiben...    ✉️ │     ││
│          │  │      gemma4:12b · Lokal · 3 Tools genutzt   │     ││
│          │  └────────────────────────────────────────────┘     ││
├──────────┴────────────────────────────────────────────────────┤│
│  ◑ 12b · 🟢 Verbunden · CPU 45°C · RAM 3.2GB · v2.0.0        ││
└───────────────────────────────────────────────────────────────┘│
```

### Screen 6: Command Palette (Cmd+K)
```
┌─ ── MiMi Nox ─────────────────────────────────────────────────┐│
│                                                                 ││
│  ┌─ ═══════════════════════════════════════════════════════════ ═│
│  │  🔍  Suche Sessions, Tools, Models, Commands...            │ │
│  │                                                               │ │
│  │  ─── NEUE SESSION                                             │ │
│  │  💬 Neuer Chat                    ⌘N                        │ │
│  │                                                               │ │
│  │  ─── SESSIONS                                                │ │
│  │  📄 Code-Analyse               Gesten                         │ │
│  │  📄 E-Mail schreiben             Vor 2 Tagen                  │ │
│  │  📄 Projekt-Dokumentation        Letzte Woche                 │ │
│  │                                                               │ │
│  │  ─── TOOLS                                                  │ │
│  │  🔧 read_file                     #file                       │ │
│  │  🔧 write_file                    #write                      │ │
│  │  🔧 browser                       #browser                    │ │
│  │  🔧 transcribe                    #audio                      │ │
│  │                                                               │ │
│  │  ─── COMMANDS                                               │ │
│  │  ⚙️  Einstellungen öffnen           #settings                │ │
│  │  🔄 Modell wechseln                  #model                   │ │
│  │  🌗 Theme wechseln                   #theme                   │ │
│  │  📊 Hardware-Info                    #hardware                │ │
│  │  📋 Clipboard prüfen                 #clipboard               │ │
│  └─ ═══════════════════════════════════════════════════════════ ═│
│                                                                 ││
└─────────────────────────────────────────────────────────────────┘│
```

### Screen 7: Settings Panel
```
┌─ ── MiMi Nox — Einstellungen ─────────────────────────────────┐│
│  ◑ MiMi Nox       Einstellungen                  ◑  14:40  ▤  ││
├──────────┬────────────────────────────────────────────────────┤│
│ ● Chat 1 │  ┌─ Modell ─────────────────────────────────────┐  ││
│ ● Chat 2 │  │  Aktuelles Modell: gemma4:12b        [Ändern] │  ││
│          │  │  Ollama Endpoint: localhost:11434             │  ││
│          │  │  [Test Connection]                            │  ││
│          │  └───────────────────────────────────────────────┘  ││
│          │                                                     ││
│          │  ┌─ Tools ──────────────────────────────────────┐  ││
│          │  │  Tool-Approval:      ◉ Immer fragen          │  ││
│          │  │                     ○ Nur riskante Tools    │  ││
│          │  │                     ○ Auto-approve alles    │  ││
│          │  │  Auto-save:          ✅ Ja (jede Nachricht)  │  ││
│          │  │  Max. Nachrichten:    100               [- +] │  ││
│          │  └───────────────────────────────────────────────┘  ││
│          │                                                     ││
│          │  ┌─ Memory ─────────────────────────────────────┐  ││
│          │  │  Langzeit-Memory:     ✅ Aktiv                │  ││
│          │  │  Memory-Einträge:     247                     │  ││
│          │  │  [Memory leeren]                                │  ││
│          │  └───────────────────────────────────────────────┘  ││
│          │                                                     ││
│          │  ┌─ Appearance ─────────────────────────────────┐  ││
│          │  │  Theme:              🌑 Dark (Standard)       │  ││
│          │  │  Font-Size:           14px                [- +] │  ││
│          │  │  Sidebar:              ◉ Expanded             │  ││
│          │  │                     ○ Collapsed               │  ││
│          │  └───────────────────────────────────────────────┘  ││
│          │                                                     ││
│          │  ┌─ About ──────────────────────────────────────┐  ││
│          │  │  MiMi Nox v2.0.0                              │  ││
│          │  │  Engine: Ollama / Gemma 4 12B               │  ││
│          │  │  Platform: macOS arm64                       │  ││
│          │  │  [Check for Updates]  [Docs]  [GitHub]      │  ││
│          │  └───────────────────────────────────────────────┘  ││
├──────────┴────────────────────────────────────────────────────┤│
│  ◑ 12b · 🟢 Verbunden · CPU 22°C · RAM 2.0GB · v2.0.0        ││
└───────────────────────────────────────────────────────────────┘│
```

---

## 6. Technologie-Begründung

### 6.1 Warum Tauri?

| Kriterium | Tauri | Electron |理由 |
|---|---|---|---|
| Bundle Size | ~15 MB (App) | ~100+ MB | Tauri nutzt OS-Browser. MiMi Nox muss <50 MB sein. |
| RAM-Verbrauch | ~80 MB | ~300+ MB | Lokale AI + App = RAM ist limitiert. |
| Startup | <1s | 3-5s | Instant-Startup = Premium-Feel. |
| Security | Capability System | Node-API Vollzugriff | Tauri 2 hat sandboxed capabilities — besser für security. |
| Native APIs | File System, Tray, Notifications | Polyfills nötig | Desktop-Features wie Tray, FS, Notifications sind native bei Tauri. |
| Lizensierung | MIT | Electron (BSD) | Beide OK, aber Tauri ist schlanker. |
| Multi-Platform | macOS, Windows, Linux | macOS, Windows, Linux | Gleicher Support. |
| Community | Wachsend | Gross, etabliert | Tauri 2.0 ist production-ready (wir nutzen 2.11.3). |

**Entscheidung:** Tauri ist die einzig sinnvolle Wahl für MiMi Nox:
1. **Offline-first, lokal, klein** — Tauri's Philosophy = MiMi Nox's Philosophy
2. **Native Desktop-Features** — Tray, FS, Notifications, Shortcuts
3. **Größere App = weniger Overhead** — User mit 8GB RAM (typisch für lokale AI) brauchen nicht 300MB Browser-Overhead

### 6.2 Warum Sidebar-Layout?

1. **Industriestandard:** ChatGPT, Claude, Gemini, Copilot — alle nutzen Sidebar
2. **Session-Management:** Desktop-Apps haben viele Sessions. Sidebar ist unverzichtbar.
3. **Erweiterbarkeit:** Sidebar wächst mit der App (Tools, Skills, Memory, Settings)
4. **Chat-Geschwindigkeit:** Maximale Chat-Breite für Markdown, Code-Blöcke, Tables
5. **Collapsible:** Wer nur chatten will → Sidebar ausklappen. Wer manages → reinklappen.

### 6.3 Warum Schwarzwald-Theme beibehalten?

1. **Brand Identity:** Green-on-black ist erkennbar. Neue User sollten "das ist MiMi Nox" sofort erkennen.
2. **Developer-Aesthetic:** Das dunkle Theme mit grünen Akzenten spricht die Zielgruppe (Developer, Tech) an.
3. **Differenzierung:** ChatGPT ist grau/weiß. Claude ist warm. Gemini ist bunt. MiMi Nox ist: dark green = unique.
4. **Professionalisierung:** Nicht das Theme ändern, sondern die Ausführung. Weniger "hacker cosplay", mehr "premium tool".

### 6.4 Warum React 19 + Vite 6?

1. **React 19:** Server Components (zukünftig), bessere Performance, Action API.
2. **Vite 6:** Schnellster Build + HMR. Essentiell für schnelle Iteration.
3. **TypeScript:** Typ-sicherer Zustand (Zustand Store), bessere DX.
4. **Tailwind CSS v4:** Utility-first, schnell, konsistent.
5. **framer-motion:** Smooth, native-feel Animationen.
6. **lucide-react:** Konsistente, moderne Icons.

---

## 7. Zeit-Schätzung

### Phase 1: Core UI (Baseline) — 3-4 Wochen
| Komponente | Aufwand | Priorität |
|---|---|---|
| Sidebar-Redesign (collapsible, date-groups) | 3d | P0 |
| Header-Redesign (minimal, model-info) | 2d | P0 |
| Chat-Input Redesign (polished, file-drop) | 3d | P0 |
| Message-Bubble Redesign (markdown, code-blocks) | 4d | P0 |
| Empty State / Welcome Screen | 3d | P0 |
| Typing-Indicator (polished) | 1d | P0 |
| Responsive/Adaptive Layout | 3d | P1 |
| **Subtotal** | **19 Tage** | |

### Phase 2: Desktop Features — 2-3 Wochen
| Komponente | Aufwand | Priorität |
|---|---|---|
| Tauri Window Setup (native frame, resize) | 3d | P0 |
| Auto-Update (tauri-plugin-updater) | 2d | P0 |
| System Tray | 2d | P1 |
| Global Keyboard Shortcuts | 3d | P1 |
| Hardware Info Panel | 2d | P1 |
| Desktop Notifications | 1d | P2 |
| File Protocol Handler | 2d | P2 |
| **Subtotal** | **13 Tage** | |

### Phase 3: Onboarding Flow — 2 Wochen
| Komponente | Aufwand | Priorität |
|---|---|---|
| Tauri: check_ollama() | 2d | P0 |
| Tauri: pull_model() (with progress) | 3d | P0 |
| Onboarding UI (3 Screens) | 4d | P0 |
| Model Selection UI | 2d | P0 |
| "Ollama already installed" fast path | 2d | P0 |
| **Subtotal** | **13 Tage** | |

### Phase 4: Landing Page Redesign — 1-2 Wochen
| Komponente | Aufwand | Priorität |
|---|---|---|
| Landing Page Redesign | 4d | P0 |
| Platform Selector (detect + buttons) | 2d | P0 |
| Download-URL Infrastructure | 3d | P0 |
| Animated Sections (keep but polish) | 3d | P1 |
| **Subtotal** | **12 Tage** | |

### Phase 5: Polish & Perfection — 2-3 Wochen
| Komponente | Aufwand | Priorität |
|---|---|---|
| Command Palette (Cmd+K) | 4d | P0 |
| Tool-Approval UI (inline expansion) | 4d | P0 |
| Animation Polish (spring, ease, duration) | 3d | P1 |
| Theme Consistency (CSS audit) | 3d | P1 |
| Windows/Linux Platform Testing | 3d | P1 |
| Accessibility (a11y) audit | 2d | P2 |
| **Subtotal** | **19 Tage** | |

### Gesamt-Schätzung

| Phase | Wochen | Tage (5d/Woche) |
|---|---|---|
| 1. Core UI | 3-4 | 19 |
| 2. Desktop Features | 2-3 | 13 |
| 3. Onboarding | 2 | 13 |
| 4. Landing Page | 1-2 | 12 |
| 5. Polish | 2-3 | 19 |
| **TOTAL** | **10-14** | **76 Tage** |

**Realistisch mit einem Developer: 10-14 Wochen (2.5-3.5 Monate)**

### Parallelisierbare Arbeit
```
Werkzeug 1 (UI): Sidebar + Chat + Header + Input  → 3-4 Wochen
Werkzeug 2 (Backend): Tauri Commands (Ollama, Update, Tray, Shortcuts) → 2-3 Wochen
Werkzeug 3 (Landing): Landing Page Redesign → 1-2 Wochen (kann parallel zu 1 und 2)
Polish: 2-3 Wochen (auf alles)

→ Mit 2-3 Entwicklern parallel: 8-10 Wochen gesamt
```

---

## 8. Risiko & Mitigation

| Risiko | Impact | Mitigation |
|---|---|---|
| Tauri 2 Plugin-Legacy | Hoch | Alle Tauri 2 Plugins müssen 2.x-kompatibel sein. Vor Implementierung prüfen. |
| Ollama-Install-Fails auf Windows | Mittel | Manuelle Anleitung immer parat. Fallback: Remote Ollama Endpoint. |
| macOS Notarization delay | Mittel |提前 2-4 Wochen für Zertifikate/Notarization. |
| Bundle Size Explosion | Niedrig | Tauri ist schon klein. Tree-shaking von React-Dependencien. |
| Dark Mode only → Accessibility | Mittel | Light Mode als Option (auch wenn Dark default). |
| Linux Package-Fragmentierung | Mittel | DEB + RPM + AppImage cover 95%. Flatpak optional. |

---

## 9. Quick Wins (Wo man sofort anfangen kann)

1. **Sidebar-Text auf English?** → Deutsch ist OK für DACH-Markt. Wenn international: i18n einplanen.
2. **`liquid-glass` CSS zu viel** → Reduziere auf 30% der aktuellen Glass-Effekte. Mehr whitespace.
3. **Cmd+K Command Palette** → Reines JS-Feature, 2 Tage, großer UX-Boost.
4. **Header bereinigen** → Currently: Menu button + Logo + Connection + Settings = zu viel. Reduziere auf: Model-Picker + Settings.
5. **Chat-Message-Animationen** → `framer-motion` ist da. Reduziere blur(10px) auf fade + slide (schneller, weniger GPU).
6. **Sidebar: Active-Indicator** → Statt nur bg-color: Ein kleiner绿-Strich links wie ChatGPT.

---

## 10. Nächste Schritte

1. **✅ Dieser Plan** — Review und Approval vom Product Lead
2. **Nächster Schritt:** Wireframes als HTML/Render erstellen
3. **Dann:** Core UI Components (Sidebar, Chat, Input) neu implementieren
4. **Parallel:** Tauri Commands für Ollama-Check + Model-Pull
5. **Dann:** Onboarding-Flow integrieren
6. **Zum Schluss:** Landing Page Redesign + Desktop Polish

---

*Ende des UX/Design Plans — MiMi Nox Desktop App v2.0*
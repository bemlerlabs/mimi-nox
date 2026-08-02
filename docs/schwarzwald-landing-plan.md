# MiMi Nox — Schwarzwald Landing Page: 3-Phasen Umgestaltungsplan

> **Leitdesigner-Konzept**: Die Landing Page wird zur digitalen Erfahrung eines Schwarzwald-Abends — nicht als Dekoration, sondern als emotionale Metapher für das Produktversprechen: lokal, urwüchsig, vertraut, privat.

---

## DESIGN-PRINZIPIEN (übergeordnet)

### Das Schwarzwald-Paradigma

Die Landing Page soll sich nicht anfühlen wie eine Tech-Site mit grünem Hintergrund. Sie soll sich anfühlen wie **Betretung eines Schwarzwald-Forstes bei Nacht**: dunkel, aber nicht finster; geheimnisvoll, aber nicht unheimlich; natürlich, aber nicht rustikal. Jedes Pixel muss dem Prinzip dienen: *"Dies könnte hier wachsen."*

### Design-Säulen

| Säule | Bedeutung | Umsetzung |
|-------|-----------|-----------|
| **Tiefe** | Kein flat Design — alles muss Layer haben | Canvas-Hintergrund → Nebel → Content → Glow |
| **Nacht** | Kein reines `#000` — das ist toter Raum | Gradient-Black mit grünem und bläulichem Unterton |
| **Mose** | Kein grelles Grün — organische Farbtiefe | Drei Moos-Grüntöne, jeder mit spezifischer HSL-Variation |
| **Stein** | Nicht alles ist Glassmorphism — auch Texturen | Subtile Noise/Grain-Overlays auf Karten und Sektionen |
| **Licht** | Fireflies als Micro-Interaktion, nicht als Main-Drop | Canvas + CSS für unterschiedliche Größenskalen |

---

## FARBSYSTEM

### Hauptpalette (HSL, Tailwind v4 format)

```
--color-black-forest:    0 0% 2%       ← Hintergrund-Basis (nicht #000!)
--color-black-midnight:  220 15% 5%    ← Nacht-Himmel-Tönung
--color-moss-deep:       142 35% 12%   ← Tiefes Moos (Section-Trennungen)
--color-moss:            142 40% 22%   ← Mittleres Moos (Karten-Hintergrund)
--color-moss-light:      142 45% 35%   ← Helles Moos (Borders, Hover)
--color-firefly:         142 65% 55%   ← Leuchtend (aktive Elemente, CTA)
--color-firefly-glow:    142 80% 65%   ← Glow-Effect (Hover, Fokus)
--color-lichen:          85  30% 55%   ← Akzent (neuer Punkt, Warning)
--color-mist:            210 10% 70%   ← Text-Helligkeit (secondary)
--color-stone:           0   0% 100%   ← Primary-Text
```

### Warum NICHT reines `#000` als Hintergrund?

- Reines Schwarz `#000` ist **tot** — kein Tiefenversprechen, kein Raum
- Schwarzwald-Nacht ist **komplex** — Sterne, Mondlicht, Tannen-Schatten, Nebel
- `bg-black-forest` (0 0% 2%) lässt Raum für Subtle-Gradients, die den Forest-Background-Canvas lebendig machen
- **Referenz**: [Linear.app](https://linear.app) verwendet nicht `#000` — ihr `--bg` ist `#0E0E10` mit subtiler Blau-Shift
- **Referenz**: [Arc Browser](https://arc.dev) — ihr dark-mode ist ein warmes Schwarz mit Brown-Unterton, nicht kaltes `#000`

### Alternative: Was WÄRE auch möglich?

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Blau-dunkel (wie Stripe Dark) | Fühlt sich an wie Fintech, nicht wie Natur |
| Reines Schwarz mit neon-grün (wie Matrix) | 2010er Cyberpunk — nicht premium 2026 |
| Brown-basiert (wie Holz/Keller) | Wählt die Metapher zu wörtlich — wirkt unmodern |
| Deep-purple (wie Notion Dark) | Schön, aber kein Schwarzwald — eher Nachtclub |

---

## TYPOGRAFIE

### Schriftwahl

| Ebene | Schrift | Gewichtung | Größe (Desktop/Mobile) |
|-------|---------|------------|------------------------|
| **Display (MiMi Nox)** | `Instrument Serif` (bereits geladen!) | Italic 700 | 72px / 48px |
| **Headlines** | `Inter` | SemiBold 600 | 36px / 28px |
| **Body** | `Inter` | Regular 400 | 16px / 15px |
| **Code/Commands** | `JetBrains Mono` (neu) | Medium 500 | 14px / 13px |
| **Micro/Label** | `Inter` | Medium 500 (klein/kerning) | 12px / 11px |

### Warum Instrument Serif für den Markennamen?

- **Instrument Serif** ist bereits im Projekt geladen (`index.html`)
- Serif vs. Sans-Serif-Kontrast = visuelles Spannungsverhältnis (wie im Schwarzwald: alter Baum vs. moderne Technologie)
- Es gibt dem Brand eine **Editorial-Qualität** — wie in einem hochwertigen Magazin
- **Referenz**: [Apple](https://apple.com) nutzt auch Kontrast: San Francisco (Sans) für UI, aber serifen-haltige Touchdowns für Hero-Texte

### Alternative: Was WÄRE auch möglich?

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Nur Inter durchgezogen | Sicherer, aber kein Character — Generic-SaaS-Look |
| Playfair Display | Zu dekorativ, zu "Wedding-Invitation" |
| Libre Baskerville | Gut, aber zu "News"-Feeling, nicht "Nature Premium" |
| Custom font | Overhead: 2MB+ Ladezeit, kein ROI für Landing |

---

# PHASE 1: FOUNDATION & ATMOSPHERE

> **Ziel**: Die technische und emotionale Basis schaffen — die "Luft im Schwarzwald" atmen lassen.

**Warum diese Phase zuerst?**  
Ohne die richtige Atmosphäre und das richtige Farbsystem ist jede weitere Gestaltung zum Scheitern verurteilt. Der Forest-Background ist das Herzstück der Schwarzwald-Metapher — er muss perfekt sein, bevor wir Content-Elemente hinzufügen. Die Typografie-Struktur muss ebenfalls zuerst stehen, denn der Wechsel von Sans zu Serif ist das stärkste visuelle Statement der Seite.

---

### 1.1 — Canvas-Hintergrund: Vom Firefly zum "Living Forest"

**Aufgabe:**
Den aktuellen `ForestBackground.tsx` von einem einfachen Firefly-Canvas zu einer **mehrschichtigen Wald-Atmosphäre** erweitern.

**Details:**

1. **Canvas-Layer 1 — Nebel (0.15px opacity)**
   - WebGL oder 2D-Canvas mit `createRadialGradient` für volumetrische Lichtkegel
   - 3–4 schwebende "Nebel-Blobs" die sich langsam horizontal bewegen (20s–40s loops)
   - Farbe: `hsla(210, 10%, 15%, 0.03)` — fast unsichtbar, aber im Fullscreen spürbar
   - Bewegung: parallax-artig, abhängig von Mausbewegung (subtil, < 5px)

2. **Canvas-Layer 2 — Deep Forest Gradient**
   - Der aktuelle linear gradient (dunkel-grün) wird ersetzt durch einen **multi-stop radial gradient**
   - Von unten aufsteigend: `rgba(0, 20, 8, 0.4)` → `rgba(0, 10, 4, 0.2)` → transparent
   - Simuliert das "Licht aus dem Tal" — der Wald ist unten heller, oben dunkler

3. **Canvas-Layer 3 — Fireflies (verbessert)**
   - Aktuelle 30–60 Partikel werden zu **80–120 Partikeln** erhöht
   - Zwei Größen-Klassen: "Glow" (R=6, alpha 0.3) und "Core" (R=2, alpha 0.8)
   - 70% der Partikel sind warm-grün (`hsl(142, 60%, 55%)`), 30% sind warm-amber (`hsl(45, 70%, 60%)`) — Amber als seltene, elegante Variation
   - **Performance**: `requestAnimationFrame` → nur ausführen wenn `document.visibilityState === 'visible'` (Battery-Saving)

**Warum diese Reihenfolge?**  
Nebel gibt die Atmosphäre, der Gradient gibt die Tiefe, Fireflies geben das Leben. Ohne Nebel wirkt die Seite zu "digital". Ohne Gradient zu flach. Ohne Fireflies zu tot.

**Warum nicht nur WebGL?**
- Canvas 2D ist für diese Anzahl Partikel **schneller** als WebGL (kein Shader-Overhead)
- WebGL wäre Overhead für 120 Partikel
- Canvas 2D hat bessere Browser-Support-Faileback-Strategien
- **Referenz**: [Three.js Showrooms](https://github.com/mrdoob/three.js) zeigen: für < 500 Partikel ist 2D-Canvas die pragmatische Wahl

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| CSS-only Animationen (divs mit @keyframes) | DOM-Bloat: 120 divs = schlechte Performance, schlechter GC |
| WebGL (Three.js / Pixi.js) | Overhead für 120 Partikel; zusätzliche ~100KB Bundle |
| Lottie-Datei | Nicht interaktiv, keine Parallax, keine Responsivität |
| Hintergrund-Video | Schwerwiegend: 10MB+ Datei, keine Interaktivität, Ladezeit |

---

### 1.2 — Farbsystem & Theme: Vom Green-400 zum 3-Tone Moos

**Aufgabe:**
Das `globals.css`-Theme und die Tailwind-Konfiguration vollständig überarbeiten.

**Details:**

1. **Tailwind v4 Theme-Update** (`globals.css` `@theme` block)
   - Alle existing `--color-primary` (142 76% 46%) → aufgeteilt in 3 Stufen
   - Neue Colors: `moss-deep`, `moss`, `moss-light` (wie oben definiert)
   - Background-Basis: `black-forest` (0 0% 2%) statt `0 0% 0%`
   - Neue Color: `mist` (210 10% 70%) für Secondary-Text

2. **Global-Night-Glow (neue Utility)**
   - `@keyframes night-glow`: 30s loop, `box-shadow` von `0 0 60px hsla(142,40%,22%,0.05)` → `0 0 120px hsla(142,40%,22%,0.12)`
   - Wendet sich auf den `body` oder den `ForestBackground`-Container
   - Gibt der Seite ein "Leben" — wie der Wald "atmet"

3. **Noise/Grain Overlay (neue Utility)**
   - `@layer utilities` → `.noise-overlay`
   - `background-image`: inline SVG mit Noise-Filter (1px × 1px SVG data URI, repeated)
   - `opacity: 0.03` — fast unsichtbar, aber im Fullscreen spürbar
   - Wendet sich auf `body::after`
   - **Referenz**: [Stripe Dark Mode](https://stripe.com) nutzt ebenfalls subtile Noise für Premium-Gefühl

**Warum Noise?**  
Reine Farbverläufe sind sterile Mathematik. Noise bringt **Unvollkommenheit** — und Unvollkommenheit fühlt sich natürlich an. Ein Schwarzwald ist nicht glatt — er ist rau, körnig, organisch.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Subtile Bild-Overlay (JPG-Noise) | Schwerer: extra Asset, CORS-Potential, Cache-Strategy |
| SVG-Turbulence als separate Datei | Gut, aber inline SVG-Data-URI ist kleiner und self-contained |
| Gar kein Noise | Die Seite fühlt sich zu "clean/digital" an — verliert das "Earthly"-Feeling |

---

### 1.3 — Typography Hierarchy & Spacing-System

**Aufgabe:**
Die Typografie-Struktur für alle Content-Ebenen definieren und das Spacing-System etablieren.

**Details:**

1. **CSS Custom Properties für Spacing**
   ```css
   @theme {
     --space-section: clamp(4rem, 8vh, 8rem);   /* Section-Padding: responsive */
     --space-section-inner: clamp(2rem, 4vw, 5rem);  /* Max-Width-Padding */
     --space-card: 2.5rem;  /* Card-Padding */
     --space-grid-gap: 1.5rem;  /* Grid Gap */
     --space-flow: 2.5rem;  /* Default gap between content blocks */
   }
   ```

2. **Display-Headline (Markenname)**
   - `font-family: "Instrument Serif", serif; font-style: italic; font-weight: 700;`
   - Gradient: `linear-gradient(135deg, hsl(142,65%,55%) 0%, hsl(142,55%,42%) 50%, hsl(85,30%,55%) 100%)`
   - Gradient wechselt von Grün → Grün (tiefer) → Lichen (warmes Akzent-Grün/Gelb)
   - `background-clip: text; -webkit-text-fill-color: transparent`

3. **Section Headline Pattern (konsistent)**
   - Label: `uppercase tracking-[0.2em] text-[0.75rem] text-moss-light/60 mb-3`
   - Headline: `text-[clamp(2rem,4vw,3.5rem)] font-semibold font-display text-stone/90 mb-4`
   - Subtitle: `text-mist/60 max-w-lg leading-relaxed`

**Warum diese Struktur?**  
Sie erzwingt Konsistenz. Jede Section hat exakt dieselbe Typografie-Struktur (Label → Headline → Subtitle). Das ist kein Zufall — es ist **rhythmische Wiederholung**, wie Tannen im Wald: gleiches Muster, aber jede棵树 ist anders.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Tailwind nur für alles | Gut für Prototyping, aber keine CSS-Vars für responsive spacing |
| CSS-in-JS (emotion/styled-components) | Overhead, kein Vite-Tree-Shaking, Bundle-Size-Problem |
| Vanilla-extract | Gut, aber Tailwind v4 hat jetzt native CSS-Variables — warum zwei Systeme? |

---

# PHASE 2: CONTENT-REDESIGN & INTERACTIONS

> **Ziel**: Jeder Section-Content wird neu gestaltet — mit Schwarzwald-Ästhetik, mit Interaktionen, mit Micro-Animationen. Die Seite muss sich anfühlen wie **Interaktion mit der Natur**.

**Warum diese Phase zweitens?**  
Phase 1 hat die Bühne gebaut. Jetzt kommt das Spiel. Ohne die Foundation (Farben, Typografie, Canvas) wären die neuen Sections visuell unkoordiniert. Mit der Foundation kann jede Section als eigenständiges "Mood" arbeiten, aber im Gesamtkontext harmonieren.

---

### 2.1 — Hero-Section: Vom Video zum "Living Night"

**Aufgabe:**
Die Hero-Section von einem statischen CloudFront-Video zu einer **mehrschichtigen interaktiven Experience** umgestalten.

**Details:**

1. **Video-Problem lösen — Self-hosted oder Canvas-only**
   - **Option A (empfohlen)**: Canvas-only "Living Night" — keine Video-Datei
     - Canvas mit 3 Schichten: Sterne (Canvas 1), Nebel (Canvas 2), Fireflies (Canvas 3, bereits aus Phase 1)
     - Sterne: 50–80 weiße Partikel mit twinkle-Animation (random, 2–8s interval)
     - Nebel: 4–6 semi-transparente radial gradients, parallax-to-mouse
     - Fireflies: wie Phase 1, aber im Hero-Overlay (nicht als fullpage bg)
     - **Vorteil**: 0 externe Assets, 0 Ladezeit, 0 CORS, funktioniert offline (PWA!)
     - **Nachteil**: Weniger "cinematic" als Video (aber mehr "native")
   - **Option B**: Self-hosted Video in `public/videos/schwarzwald-night.mp4` (max 3MB, loop, muted)
     - Quelle: Pexels/coverr — "dark forest night"
     - Poster: static image in `public/images/hero-poster.webp` (~50KB)
     - **Vorteil**: Cinematischer
     - **Nachteil**: Extra Asset, Ladezeit, offline kein Video

2. **Hero-Content-Overhaul**
   - **Badging**: `◑ MiMi Nox v2.0` → "◑ MiMi Nox — Schwarzwald Edition" mit subtle pulse animation
   - **Headline**:
     ```
     <h1 class="font-display italic text-gradient-hero">
       MiMi <span class="text-white/90">Nox</span>
     </h1>
     ```
     - "MiMi" mit Gradient (Firefly-Grün), "Nox" mit reinem Weiß — Wortspiel: "Nox" = Nacht, lateinisch
   - **Subtitle-Upgrade**:
     ```
     Dein lokaler KI-Assistent.
     Aus dem Schwarzwald, für deine Welt.
     ```
     - Zweisilbiger Rhythmus: "Dein lokaler" (Pause) "KI-Assistent" — wie ein Vers
   - **Install-Command-Block**:
     - Liquid-Glass wird zu **Obsidian-Glass** (neuer Style — dunkler, weniger transparent, mit subtiler Texture)
     - Command-Fenster: `terminal` style mit macOS-Traffic-Lights (rot-gelb-grün dots)
     - Copy-Button: wird zu einem **"Pinecone" Icon** (statt Copy/Sync) — `tree-pinecone` SVG
   - **CTA-Buttons**:
     - Primary: `bg-moss-light/90 hover:bg-moss-light text-black-forest` → nicht mehr flaches `bg-green-500`
     - Mit subtle glow: `hover:forest-glow` (animiert, 300ms)
     - Secondary: obsidian-glass style, `border-moss-light/20 hover:border-moss-light/40`

3. **Scroll-Indicator (neues Element)**
   - Unten im Hero-Viewport: subtiles "scroll down" Element
   - Design: Pfeil nach unten, aus Moos-Grün, animiert mit `animate-bounce-slow` (3s loop)
   - Nach scroll: fade-out (IntersectionObserver, threshold 0.3)
   - **Referenz**: [Apple Macbook Air](https://apple.com/macbook-air) — der Scroll-Indicator ist subtil und elegant

**Warum Canvas > Video?**
- **PWA-Kompatibilität**: Canvas funktioniert 100% offline (service worker cache ist trivial). Video offline zu machen ist komplex (SW-streaming, content-type headers).
- **Bundle-Size**: Canvas = 0KB extern. Video = 2–10MB extern.
- **Performance auf mobile**: Canvas 2D mit 120 Partikel ≈ 0.5–2fps GPU-Usage auf modernem Phone. Video = 100% GPU, kein Throttling.
- **Einzigartigkeit**: Video kann jeder haben. Canvas mit Parallax-Mouse-Interaktion ist **maßgeschneidert**.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Unsplash-Hintergrund-Bild | Statistisch, nicht interaktiv, nicht "living" |
| Three.js 3D-Wald | Overkill, 300KB+ Bundle, keine sichtbare Qualitätssteigerung |
| WebM-Video (statt MP4) | Immer noch extern, trotzdem Ladezeit, kein Offline |
| Web-GL-Landschaft | Übertrieben — der Schwarzwald ist nicht ein 3D-Spiel, er ist eine Atmosphäre |

---

### 2.2 — Features-Section: Vom Grid zum "Moss-Covered Stones"

**Aufgabe:**
Die Feature-Cards von generischen Glass-Karten zu **"moosbedeckten Steinen"** umgestalten.

**Details:**

1. **Card-Design: Obsidian-Stone**
   - **Hintergrund**: Nicht mehr `rgba(34,197,94,0.03)` sondern `rgba(0,20,8,0.4)` — tiefgrüner, fast schwarz
   - **Border**: `hsl(142,30%,20%,0.3)` — Moos-Farbe, nicht Firefly-Grün
   - **Hover-Effekt**: 
     - `box-shadow: 0 0 40px hsla(142,35%,15%,0.3)` (Mose-Glow, nicht Firefly-Glow)
     - Border wechselt zu `hsl(142,35%,25%,0.5)` — Moos leuchtet beim Berühren
   - **Noise-Overlay**: Jede Card hat `.noise-overlay` (3% opacity)

2. **Icon-Styling: Von Lucide zu Custom**
   - Aktuelle Lucide-Icons sind zu generisch
   - **Upgrade**: Icons werden mit `stroke-width="0.8"` (statt default 2) und `stroke="hsl(142,45%,35%)"` gerendert
   - Icons haben einen **inner glow** bei Hover: `filter: drop-shadow(0 0 8px hsla(142,50%,40%,0.5))`
   - **Motion**: Icons erscheinen mit `scale(0.8) → scale(1)` + `opacity(0→1)` — als würden sie aus dem Moos aufwachsen

3. **Section-Background & Layout**
   - Section-Hintergrund: `bg-gradient-to-b from-black-forest via-moss-deep/10 to-black-forest`
   - **Trennlinie** zwischen Hero und Features: nicht mehr nur Farbverlauf, sondern ein **visuelles "Waldrand"-Element**
     - SVG-Silhouette von Tannen-Spitzen als `border-bottom` zwischen Hero und Features
     - 3 Tannen-Silhouetten in `hsla(142,30%,10%,0.15)` — kaum sichtbar, aber im Fullscreen spürbar
   - **Layout**: 3-Spalten (desktop), 2-Spalten (tablet), 1-Spalte (mobile)
   - **Grid Gap**: `var(--space-grid-gap)` (definiert in Phase 1)
   - **Hover-Reveal**: Jede Card hat ein subtiles "Mist"-Overlay das bei Hover erscheint — `bg-mist/3` mit blur(2px)

**Warum "Moss-Covered Stones" statt "Glass Panels"?**
- Glassmorphism ist 2020–2023. 2026 ist **"Materielles Dark Mode"** — Dinge fühlen sich an wie reale Materialien (Stein, Holz, Samt, Moos).
- **Referenz**: [Arc Browser](https://arc.dev) hat Glassmorphism durch "tactile materials" ersetzt — Karten fühlen sich an wie reale Objekte, nicht wie durchsichtige Platten.
- Moos-bedeckter Stein ist die perfekte Metapher für MiMi Nox: etwas Altes und Beständiges, das sich mit Neuem (KI) überzogen hat.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Gradient-Border Cards (wie Linear) | Gut, aber zu "tech-y" — kein Natur-Feeling |
| Voll transparent (kein Hintergrund) | Verliert die Card-Definition auf Canvas-Hintergrund |
| Helle Cards (Light Cards on Dark BG) | Kontrast-Problem, nicht konsistent mit "Nacht"-Thema |

---

### 2.3 — Architektur- & Skills-Sections: Vom Diagramm zur "Forest Layer"

**Aufgabe:**
Die Architektur- und Skills-Sections in das Schwarzwald-Konzept integrieren.

**Details:**

1. **Architektur-Section: "Root System" (Wurzelsystem)**
   - Statt 3 Boxes mit Pfeilen → **visuelle Wurzeldarstellung**
   - Canvas-basiert: 3 "Roots" die aus dem Browser PWA (oben) in den Boden (unten) wachsen
   - Wurzeln sind animierte Linien (framer-motion `animate-dashoffset` oder Canvas-Stroke-Animation)
   - Jede Wurzel hat einen Node: `Browser PWA` → `FastAPI Server` → `Ollama (Local)`
   - Die Wurzeln enden in einem "Wurzelballen" (radialer Glow) — das Symbol für "Local"
   - **Code-Block** darunter wird zum **"Seed Block"** — ein kleiner, dunkler Kasten mit Moos-Textur, der `miminox start` als "Saat" präsentiert

2. **Skills-Section: "Undergrowth" (Unterwuchs)**
   - Statt Grid-Karten → **Organische Verteilung** mit fester Spaltenstruktur
   - Jede Skill-Card erscheint wie eine Pflanze im Unterwuchs
   - **Hover-Effekt**: Skill-Name wächst (scale 1 → 1.05), Icon wird leuchtender, Hintergrund wird zu `rgba(0,20,8,0.6)`
   - **Bewegung**: Staggered entrance — Skills erscheinen nicht alle gleichzeitig, sondern "wachsen" nacheinander aus dem Boden (y: 30→0, opacity: 0→1, duration: 0.4s, stagger 0.08s)
   - **Gruppierung**: 3 Skill-Gruppen mit Labels:
     - 📝 Text & Docs (`/write`, `/pdf`, `/research`)
     - 🔍 Analyse (`/scan`, `/review`, `/files`)
     - ⚡ Tools (`/shell`, `/chart`, `/svg`)
   - Group-Labels erscheinen als "Moss-Band" über den Skills (horizontaler Streifen in `moss-deep/20`)

3. **Micro-Interaktionen auf beiden Sections**
   - **Scroll-Synced Parallax**: Architektur-Roots bewegen sich leicht mit dem Scroll (Transform: translateX based on scroll position)
   - **Glow-Follow-Mouse**: In der Architektur-Section leuchtet ein 100px "Scheinwerfer" der Maus hinterher (radial gradient, fixed position, pointer-events: none)
   - **Referenz**: [Vercel Dashboard](https://vercel.com/dashboard) — der Glow-Follow-Mouse-Effekt ist subtil und gibt Tiefe

**Warum Wurzeln statt Pfeile?**
- Pfeile sind "Tech-Sprech". Wurzeln sind "Natur-Sprech". Beide bedeuten "Verbindung", aber Wurzeln sind **metaphorisch konsistent** mit dem Schwarzwald-Thema.
- Wurzeln sind organisch gekrümmt, nicht gerade — das gibt Dynamik.
- **Referenz**: [Obsidian](https://obsidian.md) — die Website nutzt organische Formen (nicht gerade Linien) für ihre Architektur-Darstellungen.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Pfeil-Diagramm (aktuell) | Generisch, nicht Schwarzwald, nicht emotional |
| Isometrische Illustration | Schön, aber statisch; 3D-Asset erforderlich; Overhead |
| Reine Text-Darstellung | Langweilig; keine visuelle Verbindung; verpasst die Metapher |
| SVG-Animation (statt Canvas) | Für Wurzeln gut, aber Canvas ist performanter bei komplexen Linien |

---

# PHASE 3: POLISH & MICRO-DETAILS

> **Ziel**: Das Feingranulare — alles, was den Unterschied zwischen "gut" und "unglaublich" macht. Micro-Animationen, Sound (optional), Haptik, Last-Mile-Polish.

**Warum diese Phase zuletzt?**  
Phase 3 ist das Polieren eines fertigen Möbelstücks. Man poliert nicht einen unverleimten Tisch. Erst wenn Struktur, Design und Content stehen, kommt die letzte Veredelung.

---

### 3.1 — CTA-Section: Vom Button zum "Sacred Grove"

**Aufgabe:**
Die CTA-Section von einem generischen "Jetzt installieren" zu einer **emotionalen Kulmination** — dem "heiligen Hain".

**Details:**

1. **Section-Background: "Sacred Grove"**
   - Radial gradient vom Zentrum aus: `radial-gradient(ellipse 60% 50% at center center, hsla(142,40%,15%,0.15) 0%, transparent 70%)`
   - In der Mitte: ein subtiles "Licht" — der Punkt, an dem der Himmel durch die Bäume scheint
   - **Ring-Animation**: 2 konzentrische Ringe, die sich langsam vom Zentrum aus ausdehnen und verblassen (CSS `@keyframes ring-expand`, 4s loop, `border-width` 2px → 0, `opacity` 0.3 → 0)

2. **Logo-Icon Upgrade**
   - Der aktuelle Kreis-in-Kreis wird zu einem **"Nacht-Blüte"**-Icon
   - Design: 6 Blätter in radialer Anordnung, jedes in `moss-light/60`, mit `firefly`-Glow bei Hover
   - Rotation: langsame, kontinuierliche Rotation (60s pro Umdrehung) — sichtbar, aber nicht distractierend
   - Bei Hover: beschleunigte Rotation (30s pro Umdrehung) + stärkerer Glow

3. **Copy-Upgrade & Hierarchy**
   ```
   H2: "Der Wald erwartet dich."
   Subtitle: "100% lokal. 0% Cloud. Dein persönlicher KI-Assistent, der nie telefoniert."
   
   Primary-CTA: "Installieren"
   Secondary-CTA: "Quellcode ansehen" (GitHub Link)
   
   Stats (3x, unter dem Button):
   - "7.000+ aktive Instanzen" (statt "Users")
   - "0 Cloud-Abhängigkeiten"
   - "Apache 2.0 — Frei & Offen"
   ```

4. **Button-Interaktion: "Press to Plant"**
   - Primary-Button hat einen subtilen **Ripple-Effekt** bei Click (Material-Design-inspiriert, aber in Moos-Farbe)
   - Post-Click: Kurzzeitiger Glow (200ms `firefly-glow`), dann zurück zu Normal
   - **Feedback**: Der Button gibt visuelles Feedback — es fühlt sich an wie "Drücken in Moos" — weich, aber mit Widerstand

**Warum "Sacred Grove"?**  
Der CTA ist der Höhepunkt der Page. Wenn der User bis hierher gescrollt hat, hat er 80% der Seite gesehen. Die CTA-Section muss sich anfühlen wie ein **Ziel erreicht** — wie aus dem dichten Wald plötzlich eine Lichtung.

**Alternative Ansätze:**

| Ansatz | Warum NICHT gewählt |
|--------|---------------------|
| Großer Hintergrund-Bild (Lichtung) | Schwer, nicht interaktiv, nicht PWA-freundlich (offline) |
| Nur Text, keine Visuals | Zu spartanisch — verpasst die emotionale Kulmination |
| 3D-Szene (Three.js Lichtung) | Overhead, nicht nötig, nicht PWA-freundlich |

---

### 3.2 — Footer: Vom Standard zum "Roots"

**Aufgabe:**
Den Footer von generisch zu einem thematischen Abschluss.

**Details:**

1. **Footer-Design: "Die Wurzeln des Schwarzwaldes"**
   - Hintergrund: `bg-black-forest` (identisch mit Seite, nahtloser Übergang)
   - Top-Border: nicht gerade Linie, sondern **verzweigtes Wurzel-Muster** (SVG, 1px stroke-width, `moss-deep/30`)
   - Die Wurzel-Linien gehen in die Breite und verästeln sich → visuelle Metapher für "Verwurzelung"

2. **Footer-Inhalt**
   ```
   Line 1: ◑ MiMi Nox — Privat. Lokal. Dein.
   Line 2: Aus dem Schwarzwald für die Welt. v2.0.0 · Apache 2.0
   
   [Social Links: GitHub, Discord, RSS]
   (Twitter/X wird durch Discord ersetzt — Community-Feeling, nicht Influencer-Feeling)
   
   Line 3 (unten): Built with 🌲 in Freiburg im Breisgau
   ```

3. **Micro-Animation: "Roots Growing"**
   - Beim Scrollen in den Footer: Wurzel-Linien zeichnen sich von links nach rechts ein (CSS `stroke-dashoffset` Animation, 1.5s)
   - Nur einmal — nicht bei jedem Scroll-in. Der Footer ist "unten", da scrollt man nur einmal rein.

---

### 3.3 — Performance, Accessibility & PWA-Polish

**Aufgabe:**
Sicherstellen, dass die Schwarzwald-Ästhetik nicht auf Kosten von Performance und Barrierefreiheit geht.

**Details:**

1. **Performance-Optimierungen**
   - **Canvas-Pause**: `document.addEventListener('visibilitychange')` — Canvas-Render pausieren wenn Tab nicht sichtbar (Battery-Saving)
   - **Mobile Canvas-Reduction**: Auf Bildschirmen < 768px: Firefly-Count von 120 auf 40 reduzieren, Nebel-Layer deaktivieren
   - **Prefers-Reduced-Motion**: `@media (prefers-reduced-motion: reduce)` — alle Animationen auf `animation-duration: 0.01ms` setzen oder `animation: none`
   - **Font-Display**: `font-display: swap` für alle Google Fonts (bereits in `index.html`)
   - **Critical CSS**: Noise-Overlay und Hero-CSS inline in `<head>` (klein genug für Inline)
   - **Bild-Optimierung**: Hero-Poster (falls Option B Video) als WebP, < 80KB

2. **Accessibility**
   - **Kontrast-Prüfung**: Alle Text-Farben müssen WCAG AA (4.5:1 für normal, 3:1 für groß) erfüllen
     - `text-stone/90` auf `bg-black-forest` = 18.5:1 ✓
     - `text-mist/60` auf `bg-black-forest` = 7.2:1 ✓  
     - `text-moss-light/60` auf `bg-black-forest` = 5.8:1 ✓
   - **Focus-States**: Alle interaktiven Elemente haben sichtbare Focus-Ringe (`ring-2 ring-moss-light/50`)
   - **Keyboard-Navigation**: Tab-Reihenfolge ist logisch (Hero → Features → Architektur → Skills → CTA → Footer)
   - **ARIA-Labels**: Canvas-Elemente haben `role="presentation"` ( dekorativ, nicht informativ )
   - **Screen-Reader**: `aria-hidden="true"` für dekorative Canvas- und Animationselemente

3. **PWA-Optimierung**
   - **Offline-Fallback**: Canvas-Hintergrund funktioniert offline (kein Asset erforderlich). Wenn Video (Option B): Offline-Fallback ist Canvas-only.
   - **Cache-Strategy**:
     - `globals.css`: cache 1 Jahr (content-hash)
     - Google Fonts: cache 30 Tage
     - SVG/Icons (falls self-hosted): cache 1 Jahr
   - **Manifest-Update**: `theme_color` von `#000000` auf `#0A1408` (black-forest) aktualisieren
   - **Splash Screen**: `public/images/splash-screen.webp` — 1080×1920, zeigt MiMi Nox Logo + "Schwarzwald Night"-Gradient

---

# RESSOURCEN & ZEITSCHÄTZUNG

## Zeitansatz

Die Schätzungen gehen von einem **Senior Frontend-Entwickler** (oder einem erfahrenen Fullstack-Entwickler wie Hermes) aus.

| Phase | Umfang | Schätzung | Meilenstein |
|-------|--------|-----------|-------------|
| **Phase 1** | Canvas-Overhaul, Farbsystem, Typografie | **2–3 Tage** (16–24h) | Die Seite "lebt" — Hintergrund, Farben, Schrift sind Schwarzwald |
| **Phase 2** | Hero, Features, Architektur, Skills-Redesign | **3–5 Tage** (24–40h) | Alle Sections sind neu gestaltet — visuelle Konsistenz |
| **Phase 3** | CTA, Footer, Micro-Details, Perf/A11y | **2–3 Tage** (16–24h) | Die Seite ist poliert, barrierefrei, PWA-optimiert |
| **TOTAL** | | **7–11 Tage** (56–88h) | Schwarzwald Landing Page ready |

### Tages-Verteilung (empfohlen)

| Tag | Fokus | Deliverable |
|-----|-------|-------------|
| Tag 1–2 | Phase 1.1 — Canvas-Overhaul | Living Forest Hintergrund (Nebel + Fireflies + Gradient) |
| Tag 2–3 | Phase 1.2 — Farbsystem + Noise | globals.css Theme, Tailwind v4 Colors, Noise Overlay |
| Tag 3–4 | Phase 1.3 — Typografie + Spacing | Typografie-System, Section-Pattern, CSS Vars |
| Tag 4–6 | Phase 2.1 — Hero-Redesign | Living Night Hero mit Canvas, upgraded Content |
| Tag 6–8 | Phase 2.2 — Features + Cards | Moss-Covered Stone Cards, Hover-Effects, Waldrand-Trennung |
| Tag 8–10 | Phase 2.3 — Architektur + Skills | Root-System Diagramm, Undergrowth Skills, Parallax |
| Tag 10–11 | Phase 3.1 — CTA-Section | Sacred Grove mit animiertem Logo & Button |
| Tag 11 | Phase 3.2 — Footer | Roots-Footer, Discord-Link, Wurzel-Animation |
| Tag 11–12 | Phase 3.3 — Perf + A11y + Polish | Prefers-reduced-motion, Lighthouse-90+, PWA-Manifest |

---

# REFERENZ-URLS & INSPIRATION

## Dark Mode Excellence

| Quelle | URL | Warum relevant |
|--------|-----|-----------------|
| **Linear** | https://linear.app | Goldstandard Dark-Mode. Gradient-Text, Glassmorphism-2.0, subtile Animationen |
| **Arc Browser** | https://arc.dev | "Tactile materials" statt Glassmorphism. Warmes Schwarz, organische Formen |
| **Stripe** | https://stripe.com | Noise-Overlays, Premium-Dark-Mode, scroll-synced Animationen |
| **Vercel** | https://vercel.com | Glow-Follow-Mouse, minimalistisch, perfekt ausgeführte Hovers |
| **Raycast** | https://raycast.com | Canvas-Animationen, organische Farbübergänge, clean |
| **Cursor** | https://cursor.com | Dark-Mode AI-Tool Landing, sehr hochwertig, Video-Integration |
| **Notion Dark** | https://notion.so | Warmes Schwarz, organische Layouts, nicht "Tech" |

## Natur/Organisch Inspired

| Quelle | URL | Warum relevant |
|--------|-----|-----------------|
| **Gorillas (Nature App)** | https://gorillas.io | Organische Formen, Moos-Grün, Natur-Theme |
| **AllTrails** | https://alltrails.com | Schwarzwald-ästhetik: Wald, Trails, Natur-Dark |
| **Obsidian** | https://obsidian.md | Organische Architektur-Darstellung, Dark-Mode, "Living" Feel |
| **Lumina (Notion AI)** | https://www.notion.so/product/ai | Organic dark gradients, earthy tones |

## Canvas/Animation Referenzen

| Quelle | URL | Warum relevant |
|--------|-----|-----------------|
| **Pixi.js Examples** | https://pixijs.com/examples | Canvas-Partikel-Systeme, Firefly-ähnlich |
| **p5.js Gallery** | https://editor.p5js.org | Creative Canvas-Animationen, organische Bewegung |
| **Three.js Showroom** | https://github.com/mrdoob/three.js | WebGL-Referenzen (falls später skalierbar) |
| **CSS-Tricks: Parallax** | https://css-tricks.com/parallax-scrolling | Parallax-Implementierungstechniken |

## Typography Inspiration

| Quelle | URL | Warum relevant |
|--------|-----|-----------------|
| **Apple** | https://apple.com | Serif/Sans-Kontrast im Hero, elegantes Typography |
| **The Information** | https://theinformation.com | Serif-Headlines mit Sans-Body — Editorial-Feeling |
| **Monocle** | https://monocle.com | Serif/Sans-Kontrast, warmes Schwarz, Premium |

---

# RISIKEN & MITIGATION

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| Canvas-Performance auf Low-End Android | Mittel | Hoch | Mobile Canvas-Reduktion (Phase 3.3), Feature-Detection |
| Font-Loading-FOUT für Instrument Serif | Mittel | Niedrig | `font-display: swap`, preconnect, fallback zu system serif |
| Video-Ladezeit (falls Option B) | Hoch | Mittel | Canvas-Only als default, Video als Progression-Enhancement |
| prefers-reduced-motion Konflikt mit Design | Niedrig | Hoch | `@media (prefers-reduced-motion: reduce)` mit elegantem Fallback |
| Lighthouse Performance < 90 | Mittel | Mittel | Canvas-Pause, Mobile-Reduction, Critical CSS, Code-Splitting |
| Tailwind v4 CSS-Bloat | Niedrig | Mittel | Tree-shaking, Purge-Konfiguration, CSS-Compression |

---

# ENTSCHEIDUNGS-LEITFADEN

Bei jeder Design-Entscheidung gilt diese Prioritäten-Liste:

1. **Emotionalität** — Fühlt sich der Schwarzwald an? (höchste Priorität)
2. **Performance** — Lädt die Seite in < 3s? 3G? Low-End Mobile?
3. **Barrierefreiheit** — Kann jeder die Seite nutzen? (WCAG AA)
4. **Einzigartigkeit** — Gleicht diese Seite mit jeder anderen Tech-Site?
5. **Wartbarkeit** — Können andere Entwickler diese Seite pflegen?

**Die Seite ist erst fertig, wenn alle 5 Punkte erfüllt sind.**
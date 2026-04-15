<div align="center">

# 🧠 MIMINOX v2: Die Gläserne KI-Agentur

**Strategischer Fahrplan — Vom Ist-Zustand zum "Zero Human Company" OS**

*Basierend auf einer vollständigen Analyse des existierenden Codes (Stand: April 2026)*

</div>

---

## 🎯 Das Endziel

Am Ende hast du ein System, das eine komplexe Aufgabe (z. B. „Baue eine E-Commerce App") entgegennimmt und diese **autonom durch eine Hierarchie von KI-Mitarbeitern** abarbeitet. Du sitzt im „Kontrollraum" und siehst live:

- **Wer mit wem spricht** (Inter-Agent Communication)
- **Was sie gerade denken** (Echtzeit-Parsing der `<|think|>`-Tags)
- **Welche Aufgaben offen sind** (Automatisches Kanban-Board)
- **Wie effizient sie arbeiten** (Virtuelle Arbeitsstunden & Token-Verbrauch)
- **Warum sie Entscheidungen treffen** (Knowledge-Graph-Audit-Trail)

---

## 📊 Ist-Zustand — Was bereits existiert und wiederverwendbar ist

> [!IMPORTANT]
> Der existierende Code ist **kein Prototyp — er ist produktionsreif**. Der Plan baut gezielt auf diesem Fundament auf, statt es zu ersetzen.

### ✅ Voll funktionsfähig (Direkt wiederverwendbar)

| Modul | Datei | Was es kann | Relevanz für v2 |
|---|---|---|---|
| **Swarm V2 Engine** | `core/swarm_v2.py` | Manager → Spawn → Execute → Synthesize Pipeline | 🔴 **Kern-Baustein** — wird zum Firmen-Orchestrator erweitert |
| **Swarm State Store** | `core/swarm_state.py` | Agent-Lifecycle (SPAWNED→RUNNING→DONE), Pub/Sub Events | 🔴 **Kern-Baustein** — wird zum Shared Firmenstatus |
| **Thinking Parser** | `core/chat.py` (L69-158) | Zustandsautomat für `<\|think\|>` Tag-Parsing im Stream | 🔴 **Direkt nutzbar** — Grundlage für Brain-Views |
| **Tool-Calling Engine** | `core/chat.py` + `core/tools.py` | 15 Tools, Auto-Execution, Shell-Sandbox, Vision | 🔴 **Direkt nutzbar** — Agenten nutzen diese Tools |
| **RAG / Vector Memory** | `core/memory.py` | ChromaDB, semantische Suche, Context-Injection | 🟡 **Erweiterbar** — wird zum Firmengedächtnis |
| **ReAct + Reflexion** | `core/react.py` | Selbstkorrektur-Loop mit Qualitätsprüfung | 🟡 **Erweiterbar** — QA-Agent nutzt das |
| **Vision Pipeline** | `core/vision.py` | Screenshot → Gemma4 → Koordinaten → Click/Type | 🟡 **Erweiterbar** — UI-Test-Pipeline |
| **Browser Engine** | `core/browser.py` | Headless Playwright, Screenshot, Click, Type | 🟡 **Erweiterbar** — für Agent-UI-Tests |
| **Skill System** | `core/skills.py` | CRUD, Trigger-Matching, Auto-Generation | 🟢 Nutzbar für Agent-SOPs |
| **Scheduler** | `core/scheduler.py` | APScheduler, Cron-Jobs | 🟢 Bleibt wie es ist |
| **Session/Profile** | `core/session.py`, `core/profile.py` | JSON-Persistenz, User-Profil | 🟢 Bleibt wie es ist |
| **Server** | `server/main.py` + `routes/` | FastAPI, CORS, SSE, REST-API | 🟡 **Erweiterbar** — neue Endpoints |
| **Tests** | `tests/` (28 Dateien) | 248 Unit + 32 GWT-Tests | 🔴 **Regressions-Sicherheit** |

### 🔍 Was genau fehlt (Gap-Analyse)

| Feature | Ist-Zustand | Soll-Zustand | Gap |
|---|---|---|---|
| **Agent-Rollen** | Generische `role`-Strings ("researcher", "writer") | Benannte Persönlichkeiten (Alice_CEO, Bob_CTO) mit individuellen System-Prompts | **System-Prompts + Config** |
| **Inter-Agent-Chat** | Agenten arbeiten isoliert, nur finales Ergebnis wird zusammengeführt | Agenten kommunizieren über einen Firmen-Chat (Message-Bus) | **Neues Modul** |
| **Hierarchie** | Flacher Swarm (Manager → N Workers) | Baum: CEO → CTO → Devs → QA mit Delegation + Feedback-Loops | **Orchestrator-Erweiterung** |
| **Kanban-Board** | Keine Ticket-Verwaltung | Auto-Tickets (Backlog → In Progress → Testing → Done) | **Neues Modul + Tool** |
| **Knowledge Graph** | Lineare Audit-Logs | Vernetzte Entscheidungsgraphen mit Visualisierung | **Neues Modul + UI** |
| **Firmen-Persistenz** | Session-basiert (pro Chat) | Firma überlebt Server-Neustart, kennt gestrige Arbeit | **DB-Schema** |
| **Dashboard** | Single-Chat-UI mit Sidebar | Drei-Panel "Mission Control" (HR, Ops, Topologie) | **Neues React-Frontend** |
| **Selbstregulierung** | Feste Agent-Anzahl bei Spawn | Dynamisches Scaling (CEO spawnt Extra-Devs bei Overload) | **Orchestrator-Logik** |
| **Kritikfähigkeit** | ReAct/Reflexion auf eigene Antwort | QA lehnt Dev-Code ab → Dev bekommt Feedback → Fix | **Feedback-Loop-Protokoll** |
| **Agent-Skills** | Keine Kompetenz-Messung | RPG-Skill-Tabellen pro Agent (Code Quality, Architecture etc.) mit Leveling | **Neues Modul + UI** |
| **Selbstlernen** | Nur `CorrectionJournal` (reaktiv) | Agenten lernen autonom aus Tasks, bauen Skills, verbessern Schwächen | **Erweiterung skill_builder + corrections** |
| **Shared State** | In-Memory SwarmStateStore | Persistenter Store (Redis oder SQLite) | **Storage-Adapter** |

---

## 🧠 Das Firmengehirn — "Topologies of Thoughts"

Das Herzstück von Miminox v2 ist kein Token-Counter, sondern ein **lebendes Wissensnetzwerk**. Das "Firmengehirn" ist eine 3D-interaktive Spinnennetz-Visualisierung, die sich nicht nur wie ein Gehirn *anfühlt*, sondern auch so *funktioniert*.

### 1. Der Topologie-Puls (Statt Token-Graph)

Das Dashboard zeigt **keine rohen Token-Zahlen** mehr. Stattdessen: Ein **3D-Netzwerk von Punkten** (Gedanken, Dokumente, SOPs), die durch **Lichtkanten** (Entscheidungen, Beziehungen) verbunden sind.

```
          ┌─────────────────────────────────────────────────────────┐
          │                 TOPOLOGIE-PULS                          │
          │                                                         │
          │         [SOP: API Design]                               │
          │              ╱          ╲                                │
          │       ══════╱════        ╲═══════                       │
          │      ║            ║       ║         ║                    │
          │   [Bob_CTO]──────────[Ticket #3]   ║                    │
          │      ║       ⚡PULS⚡      ║         ║                    │
          │      ║            ║       ║         ║                    │
          │   [MongoDB SOP]──────[Charlie_Dev]──[Code: api.ts]      │
          │              ╲           ╱                               │
          │               ╲═════════╱                                │
          │                                                         │
          │   ⚡ Charlie wählt MongoDB → Kante leuchtet auf         │
          │   🔵 Blaue Knoten = Aktive Gedanken                     │
          │   🟢 Grüne Kanten = Bestätigte Entscheidungen           │
          │   🔴 Rote Kanten = Abgelehnte Ansätze                   │
          └─────────────────────────────────────────────────────────┘
```

**Der Effekt:** Wenn Charlie (Dev) sich für MongoDB entscheidet, siehst du live, wie sich der "Charlie"-Knoten und der "MongoDB SOP"-Knoten verbinden und **hell aufleuchten**. Die Firma pulsiert visuell mit jedem neuen Gedanken.

### 2. Der Gedanken-Dekomposition-Tree (Topologie des Denkens)

Anstatt linearer Logs zeigt Miminox eine **hierarchische Topologie des Denkens**. Wenn du auf einen Agenten klickst, öffnet sich sein spezifischer Gedankenbaum:

**Neue Metriken (statt Token-Counts):**

| Alte Metrik | Neue Metrik | Bedeutung |
|---|---|---|
| `t: 15k Tokens` | **TF: 15** Gedankenflüsse | Wie viele Denkprozesse hat der Agent durchlaufen? |
| `p: 2.3s` | **KC: 45** Wissensknoten | Wie viele Knoten im Graph hat der Agent berührt/erstellt? |
| `cost: $0.02` | **€ 4.200 gespart** | Virtuell gesparte Agenturkosten |

**Beispiel eines Gedankenbaums:**

```
🧠 Kern-Gedanke (Centralized Core I):
│  "[Alice_CEO] Entscheide: Parallelisiere API-Entwicklung."
│
├── [Aktion] Beauftragte CTO Bob
│   │
│   ├── Topologie-Check: [Bob_CTO] Prüft Architekturnetzwerk
│   │   └── ✅ Findet keinen Konflikt mit bestehendem Code
│   │
│   ├── Konsultation Wissensbasis: [Charlie_Dev] Sucht SOP #12
│   │   └── 📋 SOP #12: "Skalierbarkeit — wähle NoSQL für MVP"
│   │
│   └── End-Entscheidung (Knoten #456):
│       └── "[Charlie_Dev] Wähle MongoDB, da standardisiert."
│           Grund: ──────► Verweis auf SOP-Knoten #12
│           TF: 3 | KC: 7
│
└── [Parallel] Diana_QA wartet auf submit_work
```

### 3. Interaktiver Knowledge Graph (Eingriff des Aufsichtsrats)

Du **chattest nicht mehr nur** — du kannst mit dem Graphen interagieren:

- **Fehler-Topologie:** Wenn ein Fehler auftritt, zeigt Diana (QA) nicht nur Text, sondern die **visuelle Topologie des Fehlers**:
  ```
  [❌ Fehler: Login Crashed] ◄──► [📄 Datei: scraper.py] ◄──► [📋 SOP: Bot-Schutz]
  ```

- **Drag & Drop Wissensknoten:** Du ziehst einen neuen Knoten (z.B. "DSGVO-Richtlinie") per Drag-and-Drop in das Netzwerk und schreibst:
  > *"@Team, konsultiert diesen neuen Knoten, bevor wir weitermachen."*

- **Graph-Queries:** Klicke auf einen beliebigen Knoten und frage: "Warum wurde das so entschieden?" → Der Graph highlightet den gesamten Entscheidungspfad.

---

## 📋 Der Fahrplan (Task-Liste)

### Phase 1: Die Infrastruktur — Das „Bürogebäude"
**Wochen 1–4 · Ziel: Node.js Runtime mit Firmen-Kern**

> [!NOTE]
> **Strategische Entscheidung:** Das Python-Backend (`core/`) bleibt als **Referenzimplementierung und Logik-Vorlage** erhalten. Die Migration zu Node.js betrifft den Runtime-Layer (Agent-Orchestrierung, Worker-Management). Bewährte Python-Module (RAG, Vision, Tools) werden über eine **Python-Bridge** (Child-Process oder gRPC) angebunden, bis sie nativ portiert sind.

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 1.1 | **Core-Server Setup** | — (Neu) | Node.js + Express + Socket.io für Echtzeit-Events. REST-API-Struktur von `server/routes/` übernehmen |
| 1.2 | **Gemma 4 Connector** | `core/chat.py` (Referenz) | Ollama HTTP API Client in JS. **Stream-Handler der Text und Tool-Calls trennt** — Logik aus `chat_with_tools()` L349-556 portieren |
| 1.3 | **Thinking-Parser portieren** | `ThinkingStreamParser` (L69-158) | Zustandsautomat 1:1 nach JS portieren. **Bereits vollständig implementiert in Python** — nur Syntax-Übersetzung |
| 1.4 | **Shared State Store** | `core/swarm_state.py` (Referenz) | Redis oder SQLite statt In-Memory. Schema von `SwarmStateStore` übernehmen. Pub/Sub-Pattern beibehalten |
| 1.5 | **Agent Worker Factory** | `core/swarm_v2.py` (Referenz) | `worker_threads`-basierter Agent-Runner. Lifecycle von `SwarmAgent.run()` (L213-344) als Blueprint nutzen |
| 1.6 | **Python-Bridge** | `core/tools.py`, `core/memory.py` | Child-Process Bridge zu Python für Tools die nicht sofort portiert werden (RAG, Vision, Browser) |
| 1.7 | **Tool-Engine portieren** | `core/tools.py` (983 Zeilen) | Alle 15 Tool-Schemas + `execute_tool()` Router nach JS. **JSON-Schemas sind bereits Ollama-kompatibel** |

**Akzeptanzkriterium Phase 1:**
```
✅ Ein Node.js-Server kann Gemma 4 E4B via Ollama aufrufen
✅ Agent-Worker starten in isolierten worker_threads
✅ <|think|>-Tags werden korrekt im Stream geparst
✅ Shared State ist persistent (überlebt Server-Neustart)
✅ Mindestens 5 Tools sind nativ in JS verfügbar (web_search, read_file, list_directory, get_datetime, run_shell)
✅ Alle existierenden Python-Tests laufen weiterhin grün (Regression)
```

---

### Phase 2: Rollen & Hierarchien — Das „Personalwesen"
**Wochen 5–8 · Ziel: Benannte Agenten mit Firmenstruktur**

> [!NOTE]
> **Existierendes Fundament:** `MANAGER_SYSTEM` und `SPECIALIST_SYSTEM_TEMPLATE` in `swarm_v2.py` L69-100 zeigen bereits das Pattern. Phase 2 erweitert das von "generische Rollen" zu "Firmen-Persönlichkeiten".

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 2.1 | **Rollen-Definitionen** | `MANAGER_SYSTEM` Prompt (swarm_v2.py) | System-Prompts für CEO, CTO, Developer, QA/Tester mit Persönlichkeit, Befugnissen, Tool-Whitelists |
| 2.2 | **Hierarchie-Orchestrator** | `SwarmOrchestrator._execute_pipeline()` | Erweiterte Pipeline: CEO → analysiert → CTO → technische Tickets → Dev/QA spawns |
| 2.3 | **Kommunikations-Tools** | `get_spawn_swarm_schema()` (Referenz) | Neue Tool-Schemas: `assign_task`, `submit_work`, `request_help`, `reject_work`, `approve_work` |
| 2.4 | **Firmen-Chat Bus** | `SwarmStateStore._notify()` | Message-Bus für Agent-zu-Agent Kommunikation. Jede Nachricht: Timestamp, Sender, Empfänger, Inhalt, Typ |
| 2.5 | **Feedback-Loop-Protokoll** | `core/react.py` reflect() | QA kann Code ablehnen → Dev bekommt strukturiertes Feedback → Fix → Re-Review |
| 2.6 | **Dynamisches Scaling** | `SwarmOrchestrator` spawn-Logik | CEO kann bei hohem Workload entscheiden: „Spawne 2 weitere Developer" |
| 2.7 | **RPG-Skill-System** | `core/skills.py` + `core/corrections.py` | Jeder Agent hat ein Skill-Profil (8 Skills, 0-100). Skills verbessern sich durch: abgeschlossene Tasks (+XP), QA-Feedback (+Bug Detection), Tool-Usage (+Research) |
| 2.8 | **Agent-Selbstlernen** | `core/skill_builder.py` + `core/corrections.py` | Agenten lernen autonom aus Tasks: CorrectionJournal für Fehler-Vermeidung, auto-generierte Skills via SkillBuilder, Schwächen-Erkennung aus Skill-Profil |

**RPG-Skill-Profil (pro Agent):**

Jeder Agent hat ein **Character Sheet** wie in einem RPG. Skills verbessern sich automatisch durch Erfahrung:

```
┌─────────────────────────────────────────────────────────────────┐
│  🤖 Charlie_Dev                          Level 7 (2,340 XP)   │
│  Senior Developer · ● active                                  │
│                                                                │
│  ⚔️ Code Quality ........ ████████░░ 82  (+3 seit gestern)    │
│  🛡️ Bug Detection ........ ██████░░░░ 64  (+8 nach QA-Review) │
│  🧠 Architecture ......... █████░░░░░ 52                      │
│  🔍 Research ............. ███████░░░ 73  (+5 nach web_search) │
│  ⚡ Speed ................ █████████░ 91                      │
│  🔧 Tool Mastery ......... ████████░░ 85                      │
│  💬 Communication ........ ██████░░░░ 61                      │
│  🧪 Testing .............. ███████░░░ 71  (+12 nach Tests)    │
│                                                                │
│  📚 Letzte Learnings:                                         │
│  • Gelernt: FastAPI Router-Pattern aus SOP #12 (vor 2h)       │
│  • Korrektur: TypeError in async handler (vor 4h)             │
│  • Neuer Skill: pytest-fixtures (auto-generiert, gestern)     │
└─────────────────────────────────────────────────────────────────┘
```

**Wie Skills sich verbessern:**

| Trigger | Betroffener Skill | Mechanismus |
|---|---|---|
| Task abgeschlossen ohne QA-Rejection | ⚔️ Code Quality +3 XP | Erfolgsquote tracken |
| QA gibt Feedback, Dev fixt → Re-Approve | 🛡️ Bug Detection +8 XP | Lernschleife aus Fehler-Topologie |
| Agent konsultiert SOP im Knowledge Graph | 🧠 Architecture +2 XP | Graph-Kante `consulted` |
| Agent nutzt web_search oder browser_go | 🔍 Research +5 XP | Tool-Usage tracken |
| Inferenzzeit unter Median | ⚡ Speed +1 XP | Timer-basiert |
| Agent nutzt neue Tools erfolgreich | 🔧 Tool Mastery +4 XP | Neues Tool = Bonus |
| Inter-Agent-Nachricht ist klar & prägnant | 💬 Communication +3 XP | QA/CEO Feedback |
| Agent schreibt Tests / Test-Suite grün | 🧪 Testing +12 XP | Test-Ergebnis auswerten |
| **Autonomes Lernen:** Agent nutzt `CorrectionJournal` | Alle Skills | Fehler nie wiederholen |
| **Skill-Builder:** Agent generiert eigenen Skill | 🔧 Tool Mastery +10 XP | Wie Hermes: Agent schreibt SOPs |

**Rollen-Architektur:**

```
                     ┌────────────────────┐
                     │   👤 User (Du)      │
                     │   "Aufsichtsrat"    │
                     └────────┬───────────┘
                              │ Aufgabe: "Baue E-Commerce App"
                     ┌────────▼───────────┐
                     │   🤖 Alice_CEO     │
                     │   Strategie        │
                     │   Tools: assign_task │
                     └────────┬───────────┘
                              │ Technische Planung
                     ┌────────▼───────────┐
                     │   🤖 Bob_CTO       │
                     │   Architektur       │
                     │   Tools: assign_task, │
                     │   create_ticket      │
                     └────┬──────────┬─────┘
               ┌──────────▼──┐  ┌───▼──────────┐
               │ 🤖 Charlie   │  │ 🤖 Diana_QA  │
               │ _Developer  │  │ Tester        │
               │ Tools: code, │  │ Tools: review,│
               │ shell, browser│ │ reject_work   │
               └──────┬───────┘  └───▲──────────┘
                      │ submit_work  │ approve/reject
                      └──────────────┘
```

**Akzeptanzkriterium Phase 2:**
```
✅ 4 benannte Agenten (CEO, CTO, Dev, QA) mit individuellen Prompts
✅ Jeder Agent hat ein RPG-Skill-Profil mit 8 Skills (0-100)
✅ Skills verbessern sich automatisch durch Task-Completion und Feedback
✅ CorrectionJournal wird pro Agent geführt (Hermes-Pattern)
✅ Agenten können eigene Skills auto-generieren (SkillBuilder)
✅ CEO kann Aufgaben an CTO delegieren, CTO an Dev und QA
✅ QA kann Code ablehnen → Dev erhält Feedback → Fix-Cycle → Skill-XP
✅ Firmen-Chat loggt alle Agent-Nachrichten mit Sender/Empfänger
✅ Dynamisches Spawning: CEO kann Extra-Entwickler hinzufügen
```

---

### Phase 3: Transparenz-Features — Das „Glashaus"
**Wochen 9–12 · Ziel: Vollständige Beobachtbarkeit**

> [!NOTE]
> **Existierendes Fundament:** `ThinkingStreamParser` in `core/chat.py` isoliert bereits `<|think|>`-Inhalte. `SwarmStateStore` hat bereits Event-Callbacks für Status-Updates. Phase 3 baut darauf den Audit-Trail und die Metriken.

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 3.1 | **Thinking-Splitter + Dekomposition** | `ThinkingStreamParser` | Pro Agent: `<\|think\|>`-Content wird als **Gedankenbaum** strukturiert (nicht linear!) und als separater Event-Stream gepusht. Jeder Gedankenfluss (TF) wird ein Knoten im Graph |
| 3.2 | **Real-time Event Log** | `SwarmStateStore._notify()` | Jeder Tool-Call, jede Agent-Nachricht, jede Entscheidung → strukturiertes Event (Timestamp, Sender, Empfänger, Typ, Payload) |
| 3.3 | **Topologie-Metriken (TF/KC)** | `AgentState.created_at / finished_at` | Neue Metriken: **TF** (Gedankenflüsse) und **KC** (Wissensknoten) statt roher Token-Counts. Skill-XP-Tracking pro abgeschlossenem Task |
| 3.4 | **Knowledge Graph Engine (Firmengehirn)** | `core/memory.py` (erweitert) | Graphology.js Graph mit Knoten-Typen: `agent`, `task`, `decision`, `sop`, `code`, `error`. Kanten: `decided`, `consulted`, `produced`, `rejected` |
| 3.5 | **Topologie-Puls Backend** | `SwarmStateStore._notify()` | Echtzeit-Events wenn neue Knoten/Kanten im Graph entstehen. Jedem Event wird ein **Puls-Signal** angehängt (für Frontend-Animation) |
| 3.6 | **Fehler-Topologie** | Knowledge Graph + Event-Log | Wenn ein Agent einen Fehler erkennt: automatische Topologie generieren: `[Fehler] ◄──► [Datei] ◄──► [Relevante SOP]` |
| 3.7 | **Audit-Trail-Persistence** | `SwarmStateStore` | Alle Events + Graph persistent in SQLite/JSON. Firma darf nicht vergessen was gestern passiert ist |
| 3.8 | **Graph-Query-API** | Knowledge Graph Engine | REST/WS-API: "Warum wurde X entschieden?" → Graph traversiert den Entscheidungspfad und gibt ihn als Pfad zurück |

**Transparenz-Architektur (mit Topologie):**

```
Agent arbeitet...
    │
    ├─── <|think|> "Ich überlege ob REST oder GraphQL besser ist..."
    │         │
    │         ├──► Gedankenbaum: Neuer TF (Gedankenfluss #3)
    │         └──► Dashboard: Brain-View zeigt Denkprozess als Baum
    │
    ├─── Tool-Call: web_search("REST vs GraphQL 2026")
    │         │
    │         ├──► Event-Log: {type: "tool_call", agent: "Bob_CTO", ...}
    │         ├──► Knowledge Graph: Knoten "Recherche: REST vs GraphQL" (KC +1)
    │         └──► Topologie-Puls: ⚡ Kante [Bob] → [Recherche] leuchtet auf
    │
    ├─── Konsultation: SOP #12 "API-Design" aus Wissensbasis geladen
    │         │
    │         ├──► Knowledge Graph: Kante [Bob] → [SOP #12] (type: consulted)
    │         └──► Topologie-Puls: ⚡ SOP-Knoten pulsiert blau
    │
    ├─── Entscheidung: "REST. Begründung: SOP empfiehlt REST für MVPs"
    │         │
    │         ├──► Knowledge Graph: Knoten "Decision #456" (type: decision)
    │         ├──► Kanten: [Bob] → [Decision] → [SOP #12] → [Ticket #3]
    │         └──► Topologie-Puls: ⚡ Gesamter Pfad leuchtet grün auf
    │
    └─── Metriken: TF: 3 | KC: 7 | 3.2s Inferenz | +5 XP Research, +2 XP Architecture
```

**Akzeptanzkriterium Phase 3:**
```
✅ <|think|>-Inhalte werden als Gedankenbaum (nicht linear!) strukturiert
✅ Topologie-Metriken: TF (Gedankenflüsse) und KC (Wissensknoten) statt Tokens
✅ Knowledge Graph: Knoten-Typen (agent, task, decision, sop, code, error)
✅ Topologie-Puls: Backend sendet Puls-Events bei neuen Knoten/Kanten
✅ Fehler-Topologie: [Fehler] ◄──► [Datei] ◄──► [SOP] automatisch generiert
✅ Graph-Query: "Warum hat Bob REST gewählt?" → Pfad im Graph
✅ Persistenz: Graph + Events überleben Server-Neustart vollständig
```

---

### Phase 4: Das Dashboard — Das „Management-Cockpit"
**Wochen 13–18 · Ziel: React "Mission Control" mit drei Hauptbereichen**

> [!NOTE]
> **Existierendes Frontend:** `app/src/` (Vanilla HTML/JS/CSS) dient als UX-Referenz — Style-Tokens aus `style.css` (46KB) und Interaktions-Patterns aus `main.js` (82KB) werden übernommen.

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 4.1 | **React + Vite Setup** | — (Neu) | React 19 + Tailwind CSS v4 + Vite. Socket.io Client für Echtzeit |
| 4.2 | **Agent-Skill-Sheets (Links)** | RPG-Skill-System (Phase 2.7) | **RPG-Character-Sheets** pro Agent: Skill-Bars (0-100), Level/XP, Radar-Chart, Recent Learnings. Klick auf Agent → Detail-View mit Skill-History |
| 4.3 | **Firmen-Chat (Mitte)** | Event-Log Bus (Phase 3) | Slack-ähnlicher Feed mit Agent-Avataren, Screenshot-Support, Fehler-Topologien inline, Drag & Drop |
| 4.4 | **Auto-Kanban-Board (Mitte)** | Ticket-System (Phase 2) | Drag-and-drop Board. Tickets wandern automatisch: CTO erstellt → Dev bearbeitet → QA abnimmt |
| 4.5 | **Gedanken-Dekomposition-View** | Thinking-Splitter (Phase 3.1) | Klick auf Agent → **hierarchischer Gedankenbaum** (nicht linearer Log!). Jeder Knoten ist ein TF mit Drill-Down |
| 4.6 | **Topologie-Puls (Rechts)** | Knowledge Graph (Phase 3.4) | **3D-Spinnennetz-Visualisierung** (Three.js / D3.js force-3d): Knoten als Lichtpunkte, Kanten als Lichtfäden. Pulsiert bei jeder Entscheidung |
| 4.7 | **Interaktiver Graph-Editor** | Topologie-Puls | User kann **Knoten per Drag & Drop hinzufügen** (z.B. neue SOP). Klick auf Knoten → "Warum?"-Audit. Rechtsklick → "@Team, konsultiert diesen Knoten" |
| 4.8 | **Fehler-Topologie-Renderer** | Fehler-Topologie (Phase 3.6) | Inline im Firmen-Chat: visuelle Spanne `[Fehler] ◄──► [Datei] ◄──► [SOP]` als klickbare Mini-Graphen |
| 4.9 | **Skill-Evolution-Tracker** | RPG-Skill-System (Phase 2.7) | Zeitverlauf der Skill-Entwicklung pro Agent. Zeigt wann und warum Skills gewachsen sind. Radar-Charts im Vergleich (heute vs. letzte Woche) |
| 4.10 | **WebSocket-Integration** | Socket.io Server (Phase 1) | Alle Panels aktualisieren sich reaktiv. Puls-Events triggern Animationen im Topologie-Scanner |

**Dashboard-Layout (mit Skill-Sheets + Topologie-Puls):**

```
┌───────────────────────────────────────────────────────────────────────────────────┐
│                          MIMINOX MISSION CONTROL                                 │
├──────────────────┬────────────────────────────────────────┬────────────────────────┤
│  🎮 SKILL-SHEETS  │          🏭 FABRIKHALLE                │  🧠 TOPOLOGIE-PULS     │
│                   │                                        │  (3D Firmengehirn)     │
│  👤 Charlie   🟢 │  ┌──────────────────────────────────┐ │                        │
│  Lv.7 (2340 XP)  │  │  KANBAN: Backlog → Prog → QA → ✅  │ │     ●──────●          │
│  Code  ████████░░ │  └──────────────────────────────────┘ │    ╱ ⚡PULS⚡ ╲         │
│  Bug   ██████░░░░ │                                        │   ●───Bob────●         │
│  Arch  █████░░░░░ │  ┌──────────────────────────────────┐ │    ╲   │    ╱          │
│  Rsrch ███████░░░ │  │ 🤖 Alice: Sprint Planning done.   │ │     ●──┼──●            │
│  Speed █████████░ │  │ 🤖 Bob: API-Design fertig.        │ │      SOP│#12            │
│  Tools ████████░░ │  │ 📸 [Screenshot]                   │ │        │               │
│  Comm  ██████░░░░ │  │ 🤖 Diana: [Fehler-Topologie]:     │ │     ●──┴──●            │
│  Tests ███████░░░ │  │   [❌Login] ◄──► [scraper.py]      │ │   MongoDB  Code        │
│ +8 Bug Detection! │  │ 👤 DU: "Ship it."                 │ │                        │
│                   │  └──────────────────────────────────┘ │  [Drag SOP hier ↓]     │
│  [🕸 Radar-Chart] │                                        │  [Click = Audit]       │
├──────────────────┴────────────────────────────────────────┴────────────────────────┤
│  🧠 GEDANKEN-BAUM (Click auf Agent):                                             │
│  Kern: [Alice] "Parallelisiere API" → [Bob] Topologie-Check ✅ → [Charlie] SOP#12│
│  → End-Entscheidung: MongoDB (TF: 3 | KC: 7)                                     │
└───────────────────────────────────────────────────────────────────────────────────┘
```

**Akzeptanzkriterium Phase 4:**
```
✅ Agent-Skill-Sheets: RPG-Bars + Level/XP + Radar-Chart pro Agent
✅ Skill-Updates live: "+8 Bug Detection" erscheint nach QA-Feedback
✅ Topologie-Puls: 3D-Spinnennetz rendert mit 60 FPS bei 500+ Knoten
✅ Puls-Animation: Neue Entscheidungen lassen Kanten hell aufleuchten
✅ Gedanken-Dekomposition: Klick auf Agent → hierarchischer Baum (nicht linear!)
✅ Interaktiver Graph: User kann SOPs per Drag & Drop hinzufügen
✅ Fehler-Topologie: Inline im Chat als klickbarer Mini-Graph
✅ Skill-Evolution: Radar-Chart zeigt Kompetenz-Entwicklung über Zeit
✅ Firmen-Chat: Nachrichten + Topologien erscheinen in < 200ms
✅ Kanban: Tickets wandern automatisch zwischen Spalten
✅ Graph-Query: Rechtsklick auf Knoten → "Warum?" → Audit-Pfad highlighted
```

---

### Phase 5: Multimodalität & Vision — Die „Augen" der Firma
**Wochen 19–22 · Ziel: Screenshot-basierte Agent-Kommunikation + Vision-QA**

> [!NOTE]
> **Existierendes Fundament:** `core/vision.py` (Screenshot → Gemma4 → Koordinaten) und `core/browser.py` (Headless Playwright) sind vollständig funktional. Phase 5 verbindet diese zu einer **Agent-zu-Agent Vision-Pipeline**.

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 5.1 | **terminal-to-image Tool** | `take_screenshot()` in tools.py | Neues Tool: Terminal-Output → PNG. Agent-Agnostic, jeder Agent kann seinen Output als Bild teilen |
| 5.2 | **Vision-QA Pipeline** | `core/vision.py` + `core/browser.py` | Dev baut UI → Puppeteer-Screenshot → QA analysiert per Gemma4 Vision → Strukturiertes Feedback |
| 5.3 | **Agent-Bild-Austausch** | Firmen-Chat Bus (Phase 2.4) | Bilder als Nachrichten im Inter-Agent-Chat. Vision-Analyse als Tool verfügbar für alle Agenten |
| 5.4 | **Drag & Drop (User → Team)** | Frontend (Phase 4) | User zieht Design-Screenshot ins Dashboard → alle Agenten erhalten das Bild als Kontext |
| 5.5 | **Screenshot-Diff** | `analyze_image()` in tools.py | Vergleich: "So sieht es aus" vs. "So soll es aussehen" → automatische Differenz-Analyse |

**Akzeptanzkriterium Phase 5:**
```
✅ Agent kann Terminal-Output als Bild an andere Agenten senden
✅ Dev → Screenshots → QA → Vision-Analyse → Feedback → Fix-Cycle
✅ User kann Bilder ins Dashboard ziehen → Team reagiert
✅ Screenshots erscheinen inline im Firmen-Chat
```

---

### Phase 6: User Journey & Polish — Der „Red Carpet"
**Wochen 23–26 · Ziel: One-Click-Start, Onboarding, Produktionsreife**

| # | Task | Baut auf… | Details |
|---|---|---|---|
| 6.1 | **Setup-Interview** | — (Neu) | KI-CEO begrüßt User: "Wie soll die Firma heißen? Was ist das erste Projekt?" |
| 6.2 | **Auto-Konfiguration** | Skill System + RAG | CEO konfiguriert basierend auf Interview: System-Prompts, SOPs, Agent-Allokation |
| 6.3 | **Docker Compose** | `install.sh` (Referenz) | `docker compose up` startet: Node.js + Ollama + Redis + React-Dashboard |
| 6.4 | **npm run start:company** | — (Neu) | Single-Command-Start ohne Docker (Node + lokales Ollama) |
| 6.5 | **E2E-Tests** | `tests/` (28 Dateien, Referenz) | Playwright E2E für Dashboard + API-Integration-Tests |
| 6.6 | **Performance-Tuning** | Alle Phasen | Worker-Pool-Sizing, Memory-Limits, WebSocket-Backpressure |
| 6.7 | **README v2 + Demo-Video** | Dieses Dokument | README mit GIFs, Pitch-Deck, Architektur-Diagramme |

**Akzeptanzkriterium Phase 6:**
```
✅ `npm run start:company` startet vollständige Firma in < 30 Sekunden
✅ Setup-Interview: User beantwortet 3 Fragen → Firma konfiguriert sich
✅ Docker Compose: One-Command-Deployment funktioniert
✅ E2E-Tests decken alle Must-Haves ab
✅ Firma überlebt Server-Neustart mit vollem Kontext
```

---

## ✅ Must-Haves — Was das System am Ende KÖNNEN MUSS

| # | Anforderung | Wie es geprüft wird | Phase |
|---|---|---|---|
| **MH-1** | **Autonome Dekomposition** — User sagt "Ich brauche Tool X" → CEO versteht → CTO erstellt Tickets | E2E-Test: Aufgabe rein → Tickets im Kanban erscheinen automatisch | Phase 2 |
| **MH-2** | **Kritikfähigkeit** — QA lehnt Code ab → Dev bekommt Feedback → Fix. User liest den "Streit" live mit | E2E-Test: Absichtlich schlechten Code erzeugen → QA rejected → Dev fixt | Phase 2 |
| **MH-3** | **Selbstregulierung** — Bei hohem Workload spawnt das System selbstständig Extra-Agenten | Stress-Test: 10 Tickets gleichzeitig → CEO spawnt Extra-Devs | Phase 2 |
| **MH-4** | **Persistenz** — Firma vergisst NICHTS. Server aus → Server an → Alles da | Test: Server stoppen, neustarten, prüfen ob Tickets + Chat + Graph vollständig | Phase 3 |
| **MH-5** | **Vollständige Beobachtbarkeit** — Jede Entscheidung ist durch Thinking-Log oder Chat belegbar | Audit-Test: Zufällige Entscheidung auswählen → "Warum?" → Antwort im Graph | Phase 3 |

---

## ⚙️ Technische Entscheidungen

### Backend: Python → Node.js (Hybride Migration)

> [!WARNING]
> **Kein Big-Bang-Rewrite.** Die Migration erfolgt hybrid: Node.js als neuer Runtime-Layer, Python-Kern über Bridge angebunden. Module werden schrittweise portiert.

```
┌─────────────────────────────────────────────────────────────┐
│                    NODE.JS RUNTIME                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Express +     │  │ Worker       │  │ Socket.io       │  │
│  │ REST API      │  │ Thread Mgr   │  │ Echtzeit        │  │
│  └──────────────┘  └──────┬───────┘  └─────────────────┘  │
│                           │                                 │
│                    ┌──────▼───────┐                          │
│                    │ Python Bridge │                          │
│                    │ (child_process│                          │
│                    │  oder gRPC)   │                          │
│                    └──────┬───────┘                          │
│                           │                                 │
│  ┌────────────────────────▼─────────────────────────────┐  │
│  │                 PYTHON CORE (bestehend)               │  │
│  │  memory.py · vision.py · browser.py · tools.py       │  │
│  │  react.py · skills.py · scheduler.py                 │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

| Was wird portiert (Phase 1) | Was bleibt Python (Bridge) | Was wird neu in JS |
|---|---|---|
| Ollama Client | RAG/ChromaDB | Worker Thread Manager |
| ThinkingStreamParser | Vision Pipeline | Firmen-Chat Bus |
| Basis-Tools (5 von 15) | Playwright Browser | Kanban-Engine |
| Agent Lifecycle | Whisper STT | Knowledge Graph |
| Shared State | Scheduler | Dashboard (React) |

### State Management

| Ebene | Technologie | Persistenz |
|---|---|---|
| **Echtzeit-State** | Redis (Pub/Sub + Key/Value) | In-Memory, Snapshot alle 60s |
| **Firmen-Persistenz** | SQLite (Tickets, Chat-History, Agent-Logs) | Datei-basiert, lokal |
| **Wissens-Basis** | ChromaDB (bestehend) | Datei-basiert, lokal |
| **Knowledge Graph** | Graphology.js (In-Memory) + JSON-Export | Datei-basiert, lokal |

### Frontend: React + Tailwind CSS

- **React 19** + Vite als Bundler
- **Tailwind CSS v4** — **Farben bleiben!** Die bestehende MiMiNox-Farbpalette aus `style.css` wird 1:1 als Design-Tokens übernommen (Hintergrund, Akzente, Agent-Farben). Nur die Komponenten-Architektur ändert sich, nicht die visuelle Identität.
- **Socket.io Client** für Echtzeit-Events
- **Three.js** + **3d-force-graph** für 3D Topologie-Puls Visualisierung
- **D3.js** als Fallback für 2D Knowledge-Graph
- **dnd-kit** für Kanban Drag & Drop + Graph-Knoten Drag & Drop
- **Zustand** für Client-State

---

## ⚠️ Risiken & Mitigationen

| Risiko | Mitigation |
|---|---|
| Node.js-Migration dauert zu lange | **Hybrid-Ansatz:** Python-Bridge ab Tag 1. Node.js nur für neuen Code, Python bleibt für existierende Module |
| Gemma 4 E4B zu schwach für CEO-Rolle | **Model-Routing:** CEO/CTO nutzen stärkeres Modell (Mixtral/Qwen), Devs nutzen E4B. Konfigurierbar per Agent |
| Worker-Threads nicht isoliert genug | **Fallback:** Docker-Container pro Agent statt worker_threads. Entscheidung nach Phase-1-Benchmarks |
| Knowledge Graph wird zu komplex | **Start minimal:** Nur Agent → Aufgabe → Ergebnis. Keine SOPs bis Phase 3 validiert ist |
| Redis-Dependency unnötig für Solo-User | **Optional:** SQLite als Default, Redis als opt-in für Multi-User-Setup |

---

## 📈 Erfolgsmetriken

### Technisch

| Metrik | Ziel |
|---|---|
| Agent-Spawn → erste Aktion | < 3 Sekunden |
| Inter-Agent-Nachricht Latenz | < 200ms |
| 6 parallele Agenten ohne Crash | ≥ 30 Minuten stabil |
| Dashboard WebSocket Latenz | < 100ms |
| Knowledge Graph Rendering | 60 FPS bei 500+ Knoten |
| Full-System Docker Start | < 60 Sekunden |
| Test-Coverage (neuer Code) | > 85% |
| Python-Tests Regression | 0 Failures |

### Produkt

| Metrik | Ziel |
|---|---|
| One-Click-Install Erfolgsrate | > 95% |
| User → Firma-läuft (Onboarding) | < 5 Minuten |
| Aufgabe → autonome Bearbeitung | Ohne menschlichen Eingriff für Standard-Tasks |
| Audit-Transparenz | Jede Entscheidung in < 2 Klicks nachvollziehbar |

---

## 🗂️ Dateistruktur (Ziel)

```
miminox/
│
├── package.json                    Node.js Projekt-Root
├── docker-compose.yml              One-Command-Start
├── tsconfig.json                   TypeScript Config
│
├── server/                         Node.js Backend (NEU)
│   ├── index.ts                    Express + Socket.io Server
│   ├── agents/                     Agent-Definitionen
│   │   ├── roles.ts                CEO, CTO, Dev, QA System-Prompts
│   │   ├── worker.ts               Worker-Thread Agent Runner
│   │   └── orchestrator.ts         Firmen-Orchestrator (ex SwarmOrchestrator)
│   ├── llm/                        Gemma 4 Integration
│   │   ├── ollama-client.ts        Ollama HTTP Client
│   │   └── thinking-parser.ts      <|think|> Tag Parser (Port von Python)
│   ├── state/                      Shared State
│   │   ├── redis-store.ts          Redis Pub/Sub Adapter
│   │   ├── sqlite-store.ts         SQLite Persistenz
│   │   └── kanban.ts               Ticket-Management
│   ├── tools/                      Tool Engine
│   │   ├── index.ts                Tool Router + Schemas
│   │   ├── web-search.ts           DuckDuckGo
│   │   ├── file-ops.ts             read_file, list_directory
│   │   └── shell.ts                Sandboxed Shell
│   ├── graph/                      Firmengehirn (Knowledge Graph)
│   │   ├── engine.ts               Graphology.js Graph + Knoten-Typen
│   │   ├── topology-pulse.ts       Puls-Event-Generator für Frontend-Animationen
│   │   ├── thought-decomposer.ts   <|think|> → hierarchischer Gedankenbaum
│   │   ├── error-topology.ts       Fehler → visuelle Topologie generieren
│   │   └── persistence.ts          JSON Import/Export + SQLite Backup
│   └── bridge/                     Python Bridge
│       └── python-bridge.ts        child_process Wrapper
│
├── dashboard/                      React Frontend (NEU)
│   ├── src/
│   │   ├── App.tsx                 Main Layout (3-Panel)
│   │   ├── components/
│   │   │   ├── HRPanel.tsx         Agent-Status, Gamification, System-Puls
│   │   │   ├── FirmenChat.tsx      Slack-Style Feed
│   │   │   ├── KanbanBoard.tsx     Auto-Kanban
│   │   │   ├── BrainView.tsx       <|think|> Live-Monitor
│   │   │   ├── TopologyPuls.tsx     3D Firmengehirn (Three.js / 3d-force-graph)
│   │   │   ├── GedankenBaum.tsx    Hierarchischer Gedanken-Dekomposition-Tree
│   │   │   ├── FehlerTopologie.tsx  Inline Mini-Graphen für Fehler-Visualisierung
│   │   │   └── StatsPanel.tsx      TF/KC-Metriken, €-Ersparnis
│   │   ├── hooks/
│   │   │   └── useSocket.ts        Socket.io Hook
│   │   └── stores/
│   │       └── firmStore.ts        Zustand State
│   └── vite.config.ts
│
├── core/                           Python Core (BESTEHEND — Bridge)
│   ├── chat.py                     ✅ Referenz für LLM-Integration
│   ├── swarm_v2.py                 ✅ Referenz für Agent-Orchestrierung
│   ├── swarm_state.py              ✅ Referenz für State-Management
│   ├── tools.py                    ✅ Tool-Engine (15 Tools)
│   ├── memory.py                   ✅ RAG/ChromaDB
│   ├── react.py                    ✅ ReAct/Reflexion
│   ├── vision.py                   ✅ Vision Pipeline
│   ├── browser.py                  ✅ Playwright Headless
│   └── ...                         ✅ Alle bestehenden Module
│
├── tests/                          Tests (BESTEHEND + NEU)
│   ├── python/                     Bestehende 28 Test-Dateien
│   └── node/                       Neue Jest/Vitest Tests
│
└── docs/
    └── MIMINOX_VISION_2026.md      ← Dieses Dokument
```

---

<div align="center">

**Dieses Dokument ist der lebende Bauplan für Miminox v2.**
Es wird mit jeder abgeschlossenen Phase aktualisiert.

*Built with 🧠 in the Black Forest. One person. One laptop. Infinite possibilities. 🌲*

**MiMi Tech AI UG — Bad Liebenzell, Schwarzwald, Deutschland**

</div>

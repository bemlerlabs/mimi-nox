# 🧠 MIMINOX v2 — Task List (TDD / GWT)

> **Methodik:** Test-Driven Development. Jede Task hat **GIVEN-WHEN-THEN** Akzeptanztests.
> Tests werden **VOR** der Implementierung geschrieben.
> `[U]` = User-Story (E2E/Integration) · `[D]` = Developer-Test (Unit)

---

## 🏗️ Bereich 1: Foundation — Node.js Runtime
**Phase 1 · Wochen 1–4 · Ziel: Server steht, Gemma 4 antwortet, Worker starten**

### 1.1 Core-Server Setup
- `[x]` **[D] Express + Socket.io Server** ✅
  - GIVEN ein Node.js-Projekt mit Express und Socket.io
  - WHEN der Server auf Port 3001 gestartet wird
  - THEN antwortet `GET /api/health` mit `{ status: "ok", version: "2.0.0" }`
  - AND ein WebSocket-Client kann sich verbinden und erhält ein `connected` Event

- `[x]` **[D] REST-API Grundstruktur** ✅
  - GIVEN der Express-Server läuft
  - WHEN `GET /api/agents` aufgerufen wird
  - THEN antwortet er mit `200` und einer leeren Agent-Liste `[]`
  - WHEN `POST /api/tasks` mit `{ prompt: "Baue eine App" }` aufgerufen wird
  - THEN antwortet er mit `202 Accepted` und einer `taskId`

- `[x]` **[U] Server startet ohne Fehler** ✅
  - GIVEN ein frisch geklontes Repository
  - WHEN `npm run dev` ausgeführt wird
  - THEN startet der Server in < 5 Sekunden ohne Fehler
  - AND die Konsole zeigt `🚀 Miminox v2 listening on :3001`

---

### 1.2 Gemma 4 Connector (Ollama Client)
- `[x]` **[D] Ollama HTTP Client — Streaming** ✅
  - GIVEN ein OllamaClient mit `baseUrl: "http://localhost:11434"`
  - WHEN `client.chat({ model: "gemma4:e4b", messages: [...] })` aufgerufen wird
  - THEN wird ein ReadableStream zurückgegeben
  - AND jeder Chunk enthält `{ content: string }` oder `{ tool_calls: [...] }`

- `[x]` **[D] Ollama Client — Connection Error** ✅
  - GIVEN Ollama läuft NICHT auf Port 11434
  - WHEN `client.chat(...)` aufgerufen wird
  - THEN wird ein `OllamaNotReachableError` geworfen
  - AND die Fehlermeldung enthält "Ollama ist nicht erreichbar"

- `[x]` **[D] Ollama Client — Model Not Found** ✅
  - GIVEN Ollama läuft, aber Modell "nonexistent:latest" ist nicht installiert
  - WHEN `client.chat({ model: "nonexistent:latest", ... })` aufgerufen wird
  - THEN wird ein `ModelNotFoundError` geworfen

- `[x]` **[D] Ollama Client — Tool-Call Parsing** ✅
  - GIVEN ein Ollama-Stream der einen Tool-Call enthält
  - WHEN der Stream vollständig gelesen wird
  - THEN enthält das Ergebnis `toolCalls: [{ name: "web_search", arguments: { query: "..." } }]`
  - AND der Text-Anteil ist separat in `content` verfügbar

- `[ ]` **[U] Gemma 4 antwortet auf eine Frage**
  - GIVEN der Server läuft und Ollama ist online mit Gemma 4 E4B
  - WHEN ein User `POST /api/chat` mit `{ message: "Was ist 2+2?" }` sendet
  - THEN erhält er eine SSE-Antwort mit Text-Chunks
  - AND die finale Antwort enthält "4"

---

### 1.3 ThinkingStreamParser (Port von Python)
- `[x]` **[D] Parser erkennt `<|think|>` Tags** ✅
  - GIVEN ein ThinkingStreamParser
  - WHEN die Chunks `["Hallo ", "<|", "think", "|>", "Ich denke...", "<|/", "think|>", " Welt"]` gefüttert werden
  - THEN ist `parser.thinking` = `"Ich denke..."`
  - AND `parser.answer` = `"Hallo  Welt"`

- `[x]` **[D] Parser ohne Thinking-Tags** ✅
  - GIVEN ein ThinkingStreamParser
  - WHEN die Chunks `["Hallo", " Welt"]` gefüttert werden
  - THEN ist `parser.thinking` = `""`
  - AND `parser.answer` = `"Hallo Welt"`

- `[x]` **[D] Parser mit mehreren Think-Blöcken** ✅
  - GIVEN ein ThinkingStreamParser
  - WHEN ein Stream mit 2 `<|think|>...<|/think|>` Blöcken verarbeitet wird
  - THEN enthält `parser.allThoughts` beide Gedanken
  - AND `parser.answer` enthält nur den Text außerhalb

- `[x]` **[D] Parser ruft Callback bei Thinking auf** ✅
  - GIVEN ein ThinkingStreamParser mit `onThinking` Callback
  - WHEN `<|think|>Ich überlege...<|/think|>` gestreamt wird
  - THEN wird der Callback mit "Ich überlege..." aufgerufen
  - AND der Callback wird NICHT mit dem Answer-Text aufgerufen

- `[x]` **[D] Parser puffert partielle Tags korrekt** ✅
  - GIVEN ein ThinkingStreamParser
  - WHEN der Stream das Tag in 1-Byte-Chunks liefert: `"<", "|", "t", "h", "i", "n", "k", "|", ">"`
  - THEN wird das Tag korrekt erkannt (kein Text-Leak)

---

### 1.4 Shared State Store
- `[x]` **[D] SQLite Store — Agent CRUD** ✅
  - GIVEN ein leerer SQLiteStateStore
  - WHEN `store.createAgent({ id: "charlie", role: "developer", status: "spawned" })` aufgerufen wird
  - THEN gibt `store.getAgent("charlie")` das Agent-Objekt zurück
  - AND `store.getAllAgents()` enthält genau 1 Agent

- `[x]` **[D] SQLite Store — Agent Lifecycle** ✅
  - GIVEN ein Agent mit Status "spawned"
  - WHEN `store.updateAgent("charlie", { status: "running" })` aufgerufen wird
  - THEN hat der Agent den Status "running"
  - WHEN `store.updateAgent("charlie", { status: "done", result: "Code fertig" })` aufgerufen wird
  - THEN hat der Agent den Status "done" und das Ergebnis ist gespeichert

- `[x]` **[D] SQLite Store — Persistenz** ✅
  - GIVEN ein SQLiteStateStore mit 3 Agenten und 5 Chat-Nachrichten
  - WHEN der Store geschlossen und mit demselben Pfad neu geöffnet wird
  - THEN sind alle 3 Agenten und 5 Nachrichten noch vorhanden

- `[x]` **[D] SQLite Store — Pub/Sub Events** ✅
  - GIVEN ein SQLiteStateStore mit einem Subscriber
  - WHEN `store.updateAgent("charlie", { status: "running" })` aufgerufen wird
  - THEN erhält der Subscriber ein Event `{ type: "agent_updated", agentId: "charlie", status: "running" }`

- `[x]` **[U] Firma überlebt Server-Neustart** ✅
  - GIVEN eine laufende Firma mit 4 Agenten und 10 Chat-Nachrichten
  - WHEN der Server gestoppt und neu gestartet wird
  - THEN sind alle Agenten, Nachrichten und Tickets vollständig erhalten

---

### 1.5 Agent Worker Factory
- `[x]` **[D] Worker spawnt in isoliertem Thread** ✅
  - GIVEN eine WorkerFactory
  - WHEN `factory.spawn({ id: "charlie", role: "developer", systemPrompt: "..." })` aufgerufen wird
  - THEN läuft ein neuer worker_thread
  - AND der Worker sendet ein `{ type: "spawned", agentId: "charlie" }` Event an den Main-Thread

- `[x]` **[D] Worker führt LLM-Call aus** ✅
  - GIVEN ein laufender Worker mit gemocktem OllamaClient
  - WHEN der Worker die Nachricht `{ type: "execute", prompt: "Schreibe Tests" }` erhält
  - THEN streamt er `{ type: "chunk", content: "..." }` Events zurück
  - AND am Ende sendet er `{ type: "done", result: "..." }`

- `[x]` **[D] Worker Timeout** ✅
  - GIVEN ein Worker mit `timeout: 5000ms`
  - WHEN der LLM-Call länger als 5 Sekunden dauert
  - THEN wird der Worker beendet
  - AND er sendet `{ type: "error", error: "Timeout nach 5000ms" }`

- `[x]` **[D] Worker Crash Recovery** ✅
  - GIVEN ein Worker der während der Ausführung abstürzt
  - WHEN der Main-Thread den Crash erkennt
  - THEN wird der Agent-Status auf "error" gesetzt
  - AND die anderen Worker laufen unbeeinträchtigt weiter

- `[x]` **[D] Mehrere Worker parallel** ✅
  - GIVEN eine WorkerFactory
  - WHEN 4 Worker gleichzeitig gespawnt werden
  - THEN laufen alle 4 parallel in eigenen Threads
  - AND sie teilen keinen Zustand (Isolation)

---

### 1.6 Python-Bridge
- `[x]` **[D] Bridge ruft Python-Funktion auf** ✅
  - GIVEN eine PythonBridge mit Pfad zur Python-Umgebung
  - WHEN `bridge.call("memory", "search", { query: "Python" })` aufgerufen wird
  - THEN wird ein Python child_process gestartet
  - AND das Ergebnis ist ein Array von Memory-Einträgen

- `[x]` **[D] Bridge Timeout** ✅
  - GIVEN eine PythonBridge mit `timeout: 10000ms`
  - WHEN der Python-Prozess nicht innerhalb von 10s antwortet
  - THEN wird ein `BridgeTimeoutError` geworfen
  - AND der Python-Prozess wird beendet

- `[x]` **[D] Bridge Error Handling** ✅
  - GIVEN eine PythonBridge
  - WHEN der Python-Code eine Exception wirft
  - THEN wird ein `BridgeError` geworfen mit der Python-Fehlermeldung

---

### 1.7 Tool-Engine (Node.js Port)
- `[x]` **[D] web_search Tool** ✅
  - GIVEN die Tool-Engine
  - WHEN `executeTool("web_search", { query: "Node.js 2026" })` aufgerufen wird
  - THEN gibt es ein Array mit `[{ title, url, body }]` zurück

- `[x]` **[D] read_file Tool — Whitelist** ✅
  - GIVEN die Tool-Engine mit Pfad-Whitelist
  - WHEN `executeTool("read_file", { path: "/etc/passwd" })` aufgerufen wird
  - THEN wird ein `FileNotAllowedError` geworfen
  - WHEN `executeTool("read_file", { path: "~/Desktop/test.txt" })` aufgerufen wird (Datei existiert)
  - THEN wird der Dateiinhalt zurückgegeben

- `[x]` **[D] run_shell Tool — Confirmation Gate** ✅
  - GIVEN die Tool-Engine
  - WHEN `executeTool("run_shell", { command: "ls -la" })` aufgerufen wird
  - THEN wird ein `ShellConfirmationRequired` Error geworfen (nie direkt ausführen)

- `[x]` **[D] get_datetime Tool** ✅
  - GIVEN die Tool-Engine
  - WHEN `executeTool("get_datetime", {})` aufgerufen wird
  - THEN enthält das Ergebnis das aktuelle Jahr "2026"
  - AND das Format ist deutsch (z.B. "Freitag, 04. April 2026")

- `[x]` **[D] Tool-Schema Kompatibilität** ✅
  - GIVEN `getToolSchemas()` aufgerufen
  - THEN gibt es ein Array von Objekten mit `{ type: "function", function: { name, description, parameters } }`
  - AND jeder Schema-Name existiert als Funktion in der TOOL_MAP
  - AND die Schemas sind Ollama-kompatibel

---

## 👥 Bereich 2: Personalwesen — Rollen & Hierarchie
**Phase 2 · Wochen 5–8 · Ziel: 4 Agenten mit Firmenstruktur + Skills**

### 2.1 Rollen-Definitionen
- `[x]` **[D] System-Prompts laden** ✅
  - GIVEN eine RoleConfig Datei mit 4 Rollen
  - WHEN `loadRole("alice_ceo")` aufgerufen wird
  - THEN enthält das Ergebnis `{ name, role, systemPrompt, toolWhitelist, skills }`
  - AND der systemPrompt enthält Persönlichkeitsbeschreibung

- `[x]` **[D] Tool-Whitelist pro Rolle** ✅
  - GIVEN Alice_CEO mit `toolWhitelist: ["assign_task", "approve_work"]`
  - WHEN Alice versucht `run_shell` zu nutzen
  - THEN wird der Tool-Call blockiert mit "Tool nicht autorisiert für diese Rolle"

---

### 2.2 Hierarchie-Orchestrator
- `[x]` **[D] CEO dekomponiert Aufgabe** ✅
  - GIVEN ein Orchestrator mit gemocktem LLM
  - WHEN `orchestrator.execute("Baue eine E-Commerce App")` aufgerufen wird
  - THEN ruft der CEO-Agent den CTO auf (Delegation)
  - AND der CTO erstellt mindestens 2 Tickets

- `[x]` **[D] Delegation-Kette** ✅
  - GIVEN CEO → CTO → Dev Pipeline
  - WHEN CEO eine Aufgabe an CTO delegiert
  - THEN erstellt CTO Tickets und weist sie an Dev zu
  - AND jeder Schritt ist als Event im State Store protokolliert

- `[x]` **[U] Vollständige Pipeline** ✅
  - GIVEN die Firma mit 4 Agenten
  - WHEN der User "Erstelle eine REST-API für Todos" eingibt
  - THEN arbeiten CEO → CTO → Dev → QA die Aufgabe autonom ab
  - AND der Firmen-Chat zeigt alle Kommunikation zwischen Agenten

---

### 2.3 Kommunikations-Tools
- `[x]` **[D] assign_task Tool** ✅
  - GIVEN Agent "alice_ceo" ruft `assign_task({ to: "bob_cto", task: "API designen" })` auf
  - WHEN das Tool ausgeführt wird
  - THEN erscheint ein neues Ticket im Kanban (Status: "backlog")
  - AND Bob erhält die Aufgabe als nächste Nachricht

- `[x]` **[D] submit_work Tool** ✅
  - GIVEN Agent "charlie_dev" hat Ticket #3 bearbeitet
  - WHEN `submit_work({ ticketId: 3, result: "Code fertig", code: "..." })` aufgerufen wird
  - THEN wechselt das Ticket auf Status "testing"
  - AND Diana_QA erhält die Arbeit zur Review

- `[x]` **[D] reject_work Tool** ✅
  - GIVEN Diana_QA reviewed Ticket #3
  - WHEN `reject_work({ ticketId: 3, reason: "Keine Tests", feedback: "Bitte pytest hinzufügen" })` aufgerufen wird
  - THEN wechselt das Ticket zurück auf "in_progress"
  - AND Charlie_Dev erhält das Feedback als nächste Nachricht
  - AND Charlie_Dev's 🛡️ Bug Detection Skill erhält +8 XP

---

### 2.4 Firmen-Chat Bus
- `[x]` **[D] Nachricht senden** ✅
  - GIVEN der Chat-Bus
  - WHEN `bus.send({ from: "alice_ceo", to: "bob_cto", content: "Sprint starten", type: "directive" })` aufgerufen wird
  - THEN wird die Nachricht im Store persistiert
  - AND alle Subscriber erhalten ein `chat_message` Event

- `[x]` **[D] Broadcast-Nachricht** ✅
  - GIVEN der Chat-Bus mit 4 Agenten
  - WHEN `bus.broadcast({ from: "alice_ceo", content: "Alle auf Sprint fokussieren" })` aufgerufen wird
  - THEN erhalten alle 4 Agenten die Nachricht

- `[x]` **[U] Chat-Verlauf sichtbar** ✅
  - GIVEN eine laufende Firma mit aktiver Kommunikation
  - WHEN der User `GET /api/chat/history` aufruft
  - THEN erhält er alle Nachrichten chronologisch sortiert
  - AND jede Nachricht hat `from`, `to`, `content`, `timestamp`, `type`

---

### 2.5 Kanban-Engine
- `[x]` **[D] Ticket erstellen** ✅
  - GIVEN eine leere Kanban-Engine
  - WHEN `kanban.createTicket({ title: "API designen", assignee: "charlie_dev", createdBy: "bob_cto" })` aufgerufen wird
  - THEN hat das Ticket Status "backlog" und eine eindeutige ID
  - AND `kanban.getAll()` enthält genau 1 Ticket

- `[x]` **[D] Ticket-Workflow** ✅
  - GIVEN ein Ticket mit Status "backlog"
  - WHEN der Status zu "in_progress" → "testing" → "done" wechselt
  - THEN wird bei jedem Wechsel ein `ticket_moved` Event emittiert
  - AND ungültige Übergänge (z.B. "backlog" → "done") werden abgelehnt

- `[x]` **[U] Kanban über API abrufbar** ✅
  - GIVEN 5 Tickets in verschiedenen Spalten
  - WHEN `GET /api/kanban` aufgerufen wird
  - THEN sind die Tickets nach Spalten gruppiert: `{ backlog: [...], in_progress: [...], testing: [...], done: [...] }`

---

### 2.7 RPG-Skill-System
- `[x]` **[D] Skill-Profil initialisieren** ✅
  - GIVEN ein neuer Agent "charlie_dev" mit Rolle "developer"
  - WHEN sein Skill-Profil erstellt wird
  - THEN hat er 8 Skills mit Startwerten (z.B. Code Quality: 50, Bug Detection: 30, ...)
  - AND sein Level ist 1 mit 0 XP

- `[x]` **[D] XP durch Task-Completion** ✅
  - GIVEN Charlie_Dev mit Code Quality: 50
  - WHEN er ein Ticket abschließt ohne QA-Rejection
  - THEN steigt Code Quality um +3 auf 53
  - AND sein XP-Counter steigt um den Skill-Wert

- `[x]` **[D] XP durch QA-Feedback-Loop** ✅
  - GIVEN Charlie_Dev mit Bug Detection: 30
  - WHEN QA sein Code ablehnt UND er den Fix erfolgreich einreicht
  - THEN steigt Bug Detection um +8 auf 38
  - AND ein Learning-Eintrag wird ins CorrectionJournal geschrieben

- `[x]` **[D] XP durch Tool-Usage** ✅
  - GIVEN Charlie_Dev mit Research: 40
  - WHEN er `web_search` oder `browser_go` erfolgreich nutzt
  - THEN steigt Research um +5
  - WHEN er ein neues Tool zum ersten Mal nutzt
  - THEN steigt Tool Mastery um +4

- `[x]` **[D] Level-Up** ✅
  - GIVEN Charlie_Dev mit Level 3 und 950/1000 XP
  - WHEN er 100 XP durch eine Task erhält
  - THEN steigt sein Level auf 4
  - AND ein `agent_level_up` Event wird emittiert

- `[x]` **[D] Skill-Profil persistieren** ✅
  - GIVEN ein Agent mit veränderten Skills
  - WHEN der Store geschlossen und neu geöffnet wird
  - THEN sind alle Skill-Werte, XP und Level identisch

- `[x]` **[U] Skill-Profil über API abrufbar** ✅
  - GIVEN Charlie_Dev mit 8 Skills
  - WHEN `GET /api/agents/charlie_dev/skills` aufgerufen wird
  - THEN enthält die Antwort `{ skills: { codeQuality: 82, bugDetection: 64, ... }, level: 7, xp: 2340, recentLearnings: [...] }`

---

### 2.8 Agent-Selbstlernen
- `[x]` **[D] CorrectionJournal pro Agent** ✅
  - GIVEN Agent "charlie_dev" macht einen Fehler (QA-Rejection)
  - WHEN der Fehler ins CorrectionJournal geschrieben wird
  - THEN enthält `charlie.corrections.getRecent(5)` den Eintrag
  - AND beim nächsten Task wird der Fehler als Context injiziert

- `[x]` **[D] Auto-Skill-Generation** ✅
  - GIVEN Charlie_Dev hat 3 ähnliche Tasks erfolgreich abgeschlossen (z.B. FastAPI-Endpoints)
  - WHEN das System das Pattern erkennt
  - THEN generiert der SkillBuilder automatisch einen Skill "fastapi-endpoint"
  - AND Charlie's Tool Mastery steigt um +10 XP

- `[x]` **[D] Schwächen-Erkennung** ✅
  - GIVEN Charlie_Dev mit Architecture: 30 (niedrigster Skill)
  - WHEN ein neuer Task Architektur-Entscheidungen erfordert
  - THEN wird Charlie's System-Prompt um den Hinweis ergänzt: "Konsultiere SOPs für Architektur-Entscheidungen"
  - AND bei erfolgreicher SOP-Konsultation steigt Architecture um +2

---

## 🔍 Bereich 3: Transparenz — Das Glashaus
**Phase 3 · Wochen 9–12 · Ziel: Alles sichtbar, alles nachvollziehbar**

### 3.1 Thinking-Splitter + Dekomposition
- `[x]` **[D] Gedankenbaum aus Think-Tags** ✅
  - GIVEN ein Agent-Stream mit `<|think|>Soll ich REST oder GraphQL nehmen? REST ist besser für MVPs.<|/think|>`
  - WHEN der ThoughtDecomposer den Stream verarbeitet
  - THEN erzeugt er einen Baum: `{ root: "Soll ich REST oder GraphQL nehmen?", children: [{ text: "REST ist besser für MVPs", type: "conclusion" }] }`
  - AND der Gedankenfluss-Counter (TF) steigt um +1

- `[x]` **[D] Gedankenbaum als Event** ✅
  - GIVEN ein ThoughtDecomposer mit Socket.io Anbindung
  - WHEN ein neuer Gedankenfluss erstellt wird
  - THEN sendet er ein `thought_flow` Event mit dem Baum an alle Dashboard-Clients

---

### 3.2 Real-time Event Log
- `[x]` **[D] Event-Struktur** ✅
  - GIVEN der Event-Logger
  - WHEN ein Agent einen Tool-Call macht
  - THEN wird ein Event `{ timestamp, type: "tool_call", agentId, toolName, arguments, result }` gespeichert

- `[x]` **[D] Event-Stream via WebSocket** ✅
  - GIVEN ein Dashboard-Client verbunden via Socket.io
  - WHEN ein Event geloggt wird
  - THEN erhält der Client das Event in < 100ms

---

### 3.3 Topologie-Metriken (TF/KC)
- `[x]` **[D] TF-Counter** ✅
  - GIVEN ein Agent der 3 Gedankenflüsse durchlaufen hat
  - WHEN `metrics.getTF("charlie_dev")` aufgerufen wird
  - THEN gibt es `3` zurück

- `[x]` **[D] KC-Counter** ✅
  - GIVEN ein Agent der 7 Knoten im Knowledge Graph berührt hat
  - WHEN `metrics.getKC("charlie_dev")` aufgerufen wird
  - THEN gibt es `7` zurück

- `[x]` **[D] Skill-XP aus Metriken** ✅
  - GIVEN ein Agent der web_search genutzt hat (KC +1)
  - WHEN die Metrik aktualisiert wird
  - THEN steigt sein Research-Skill um +5 XP

---

### 3.4 Knowledge Graph Engine (Firmengehirn)
- `[x]` **[D] Knoten erstellen** ✅
  - GIVEN ein leerer Graph
  - WHEN `graph.addNode({ id: "bob_cto", type: "agent", label: "Bob CTO" })` aufgerufen wird
  - THEN enthält `graph.getNode("bob_cto")` den Knoten
  - AND `graph.nodeCount()` ist 1

- `[x]` **[D] Kante erstellen** ✅
  - GIVEN ein Graph mit Knoten "bob_cto" und "sop_12"
  - WHEN `graph.addEdge({ from: "bob_cto", to: "sop_12", type: "consulted" })` aufgerufen wird
  - THEN enthält `graph.getEdges("bob_cto")` eine Kante zu "sop_12"
  - AND die Kante hat den Typ "consulted"

- `[x]` **[D] Knoten-Typen** ✅
  - GIVEN verschiedene Knoten-Typen
  - WHEN Knoten mit Typen `agent`, `task`, `decision`, `sop`, `code`, `error` erstellt werden
  - THEN kann nach Typ gefiltert werden: `graph.getNodesByType("sop")` gibt nur SOP-Knoten zurück

- `[x]` **[D] Pfad-Query (Warum-Frage)** ✅
  - GIVEN ein Graph mit Pfad: Bob → consulted → SOP #12 → produced → Decision #456 → assigned → Ticket #3
  - WHEN `graph.queryPath("decision_456")` aufgerufen wird
  - THEN gibt er den vollständigen Pfad zurück mit allen Kanten und Knoten

- `[x]` **[D] Graph persistieren** ✅
  - GIVEN ein Graph mit 50 Knoten und 80 Kanten
  - WHEN `graph.save("firma.json")` aufgerufen wird AND `graph.load("firma.json")` aufgerufen wird
  - THEN sind alle Knoten und Kanten identisch

---

### 3.5 Topologie-Puls Backend
- `[x]` **[D] Puls-Events emittieren** ✅
  - GIVEN ein Graph mit Socket.io Anbindung
  - WHEN eine neue Kante hinzugefügt wird
  - THEN wird ein `topology_pulse` Event emittiert: `{ type: "edge_added", from, to, edgeType, pulseColor }`

- `[x]` **[D] Puls-Farben** ✅
  - GIVEN verschiedene Kantentypen
  - WHEN Typ "consulted" → THEN Puls-Farbe = blau
  - WHEN Typ "decided" → THEN Puls-Farbe = grün
  - WHEN Typ "rejected" → THEN Puls-Farbe = rot

---

### 3.6 Fehler-Topologie
- `[x]` **[D] Fehler-Topologie generieren** ✅
  - GIVEN ein Agent erkennt einen Fehler in `scraper.py`
  - WHEN `generateErrorTopology({ error: "Login Crashed", file: "scraper.py" })` aufgerufen wird
  - THEN wird ein Subgraph erstellt: `[Error: Login Crashed] ←→ [File: scraper.py] ←→ [SOP: Bot-Schutz]`
  - AND die SOP wird automatisch durch semantische Suche in der RAG-Datenbank gefunden

- `[x]` **[D] Fehler-Topologie als Chat-Nachricht** ✅
  - GIVEN eine generierte Fehler-Topologie
  - WHEN sie im Firmen-Chat gepostet wird
  - THEN enthält die Nachricht `{ type: "error_topology", nodes: [...], edges: [...] }`

---

### 3.7 Audit-Trail-Persistence
- `[x]` **[D] Alle Events persistent** ✅
  - GIVEN 100 Events geloggt
  - WHEN der Server neu gestartet wird
  - THEN sind alle 100 Events im Event-Log abrufbar

---

### 3.8 Graph-Query-API
- `[x]` **[U] Warum-Frage über API** ✅
  - GIVEN ein Graph mit Entscheidung "MongoDB gewählt"
  - WHEN `GET /api/graph/query?node=decision_456&question=warum` aufgerufen wird
  - THEN gibt die API den Entscheidungspfad zurück: `[Bob → SOP #12 → Decision → Ticket #3]`

---

## 🖥️ Bereich 4: Dashboard — Mission Control
**Phase 4 · Wochen 13–18 · Ziel: React-UI mit Live-Updates**

### 4.1 React + Vite Setup
- `[x]` **[D] Vite Build erfolgreich** ✅
  - GIVEN das Dashboard-Projekt
  - WHEN `npm run build` ausgeführt wird
  - THEN kompiliert es ohne Fehler in < 30 Sekunden

- `[x]` **[U] Dashboard lädt im Browser** ✅
  - GIVEN Server und Dashboard laufen
  - WHEN der User `http://localhost:5173` öffnet
  - THEN sieht er das 3-Panel-Layout (Skill-Sheets | Fabrikhalle | Topologie-Puls)

---

### 4.2 Agent-Skill-Sheets
- `[x]` **[U] Skill-Bars sichtbar** ✅
  - GIVEN 4 Agenten mit Skill-Profilen
  - WHEN das Dashboard geladen wird
  - THEN zeigt die linke Spalte für jeden Agent: Name, Level, 8 Skill-Bars (0-100), Status-Dot

- `[x]` **[U] Skill-Update live** ✅
  - GIVEN Charlie_Dev mit Bug Detection: 64
  - WHEN QA eine Rejection verarbeitet und Charlie den Fix einreicht
  - THEN aktualisiert sich Charlies Bug Detection Bar live auf 72 (+8)
  - AND eine "+8 Bug Detection!" Animation erscheint

- `[x]` **[U] Radar-Chart** ✅
  - GIVEN ein Agent mit 8 Skills
  - WHEN der User auf den Agent klickt
  - THEN öffnet sich ein Detail-View mit Radar-Chart und Learning-Log

---

### 4.3 Firmen-Chat
- `[x]` **[U] Nachrichten erscheinen live** ✅
  - GIVEN das Dashboard ist geöffnet
  - WHEN ein Agent eine Nachricht sendet
  - THEN erscheint sie in < 200ms im Chat-Feed mit Avatar und Timestamp

- `[x]` **[U] Fehler-Topologie inline** ✅
  - GIVEN Diana_QA postet eine Fehler-Topologie
  - WHEN die Nachricht im Chat erscheint
  - THEN zeigt sie einen klickbaren Mini-Graphen `[❌ Fehler] ◄──► [Datei] ◄──► [SOP]`

- `[x]` **[U] User kann Nachricht senden** ✅
  - GIVEN das Chat-Input-Feld
  - WHEN der User "@Team prüft DSGVO" eingibt und Enter drückt
  - THEN erscheint die Nachricht mit "Aufsichtsrat"-Badge im Feed
  - AND alle Agenten erhalten sie als Kontext

---

### 4.4 Auto-Kanban-Board
- `[x]` **[U] Tickets in Spalten** ✅
  - GIVEN 5 Tickets in verschiedenen Status
  - WHEN das Dashboard geladen wird
  - THEN sind die Tickets in 4 Spalten sortiert: Backlog, In Progress, Testing, Done

- `[x]` **[U] Tickets wandern automatisch** ✅
  - GIVEN ein Ticket in "Backlog"
  - WHEN Charlie_Dev anfängt daran zu arbeiten
  - THEN wandert das Ticket automatisch nach "In Progress"
  - AND eine Animation zeigt die Bewegung

---

### 4.5 Gedanken-Dekomposition-View
- `[x]` **[U] Gedankenbaum sichtbar** ✅
  - GIVEN ein Agent durchläuft einen Denkprozess
  - WHEN der User auf den Agent klickt
  - THEN zeigt die Bottom-Bar einen hierarchischen Baum mit TF/KC-Metriken

---

### 4.6 Topologie-Puls (3D)
- `[x]` **[U] 3D-Visualisierung rendert** ✅
  - GIVEN ein Graph mit 20+ Knoten
  - WHEN das Dashboard geladen wird
  - THEN rendert die rechte Spalte ein 3D-Netzwerk mit Lichtpunkten und Kanten

- `[x]` **[U] Puls-Animation** ✅
  - GIVEN das 3D-Netzwerk
  - WHEN ein Agent eine Entscheidung trifft
  - THEN leuchtet der Pfad zwischen den beteiligten Knoten auf (Puls-Animation)

- `[x]` **[U] Klick auf Knoten zeigt Audit** ✅
  - GIVEN das 3D-Netzwerk
  - WHEN der User auf einen Entscheidungs-Knoten klickt
  - THEN zeigt ein Popup den Audit-Pfad: "Warum wurde das so entschieden?"

---

### 4.7 Interaktiver Graph-Editor
- `[x]` **[U] Drag & Drop SOP** ✅
  - GIVEN das 3D-Netzwerk mit Drop-Zone
  - WHEN der User eine Datei (z.B. DSGVO-PDF) in die Drop-Zone zieht
  - THEN erscheint ein neuer SOP-Knoten im Graph
  - AND ein "@Team, konsultiert diesen neuen Knoten" wird gesendet

---

## 📸 Bereich 5: Multimodalität & Vision
**Phase 5 · Wochen 19–22 · Ziel: Agenten sehen und zeigen**

### 5.1 Vision-QA Pipeline
- `[ ]` **[D] Screenshot → Vision-Analyse**
  - GIVEN Charlie_Dev hat eine UI gebaut
  - WHEN ein Browser-Screenshot erstellt und an Diana_QA gesendet wird
  - THEN analysiert Diana den Screenshot via Gemma4 Vision
  - AND gibt strukturiertes Feedback: `{ issues: [...], approved: boolean }`

- `[ ]` **[U] Screenshots im Chat**
  - GIVEN der Firmen-Chat
  - WHEN ein Agent einen Screenshot teilt
  - THEN erscheint er inline im Chat-Feed als Thumbnail

---

### 5.2 User → Team Bilder
- `[ ]` **[U] Drag & Drop Design**
  - GIVEN das Dashboard
  - WHEN der User ein Design-Screenshot ins Chat-Feld zieht
  - THEN erhalten alle Agenten das Bild als Kontext
  - AND Alice_CEO bestätigt: "Design erhalten, leite an CTO weiter"

---

## 🎪 Bereich 6: User Journey & Polish
**Phase 6 · Wochen 23–26 · Ziel: One-Click, Onboarding, Produktionsreife**

### 6.1 Setup-Interview
- `[ ]` **[U] Onboarding-Flow**
  - GIVEN ein frischer Start ohne Firma
  - WHEN der User zum ersten Mal das Dashboard öffnet
  - THEN begrüßt Alice_CEO: "Willkommen! Wie soll unsere Firma heißen?"
  - AND nach 3 Fragen ist die Firma konfiguriert

### 6.3 Docker Compose
- `[ ]` **[U] One-Command-Start**
  - GIVEN ein System mit Docker installiert
  - WHEN `docker compose up` ausgeführt wird
  - THEN startet: Node.js Server + Ollama + React Dashboard
  - AND nach < 60 Sekunden ist das Dashboard erreichbar

### 6.4 npm run start:company
- `[ ]` **[U] Lokaler Start**
  - GIVEN Node.js und Ollama installiert
  - WHEN `npm run start:company` ausgeführt wird
  - THEN startet die Firma in < 30 Sekunden
  - AND die Konsole zeigt alle 4 Agenten als "ready"

### 6.5 E2E-Tests
- `[ ]` **[D] Playwright E2E Suite**
  - GIVEN die vollständige Anwendung
  - WHEN `npm run test:e2e` ausgeführt wird
  - THEN laufen alle E2E-Tests durch (Dashboard + API)
  - AND die Coverage ist > 85%

### 6.6 Regressions-Tests
- `[ ]` **[D] Python-Tests grün**
  - GIVEN die bestehenden 239 Python-Tests
  - WHEN `pytest tests/` ausgeführt wird
  - THEN bestehen alle 239 Tests (0 Failures, 0 Regressions)

---

## 📊 Zusammenfassung

| Bereich | Tasks | Tests (GWT) | Priorität |
|---|---|---|---|
| 1. Foundation | 25 | 25 [D] + 4 [U] | 🔴 Kritisch |
| 2. Personalwesen | 22 | 16 [D] + 6 [U] | 🔴 Kritisch |
| 3. Transparenz | 15 | 13 [D] + 2 [U] | 🟡 Hoch |
| 4. Dashboard | 14 | 2 [D] + 12 [U] | 🟡 Hoch |
| 5. Vision | 3 | 1 [D] + 2 [U] | 🟢 Mittel |
| 6. Polish | 5 | 2 [D] + 3 [U] | 🟢 Mittel |
| **Gesamt** | **84** | **59 [D] + 29 [U]** | |

> [!IMPORTANT]
> **TDD-Regel:** Für jede Task wird ZUERST der Test geschrieben (`[D]` → Jest/Vitest, `[U]` → Playwright), DANN die Implementierung. Ein Task gilt erst als `[x]` wenn der Test grün ist.

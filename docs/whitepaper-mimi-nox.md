# MiMi Nox — Whitepaper

**Ein lokaler, multimodaler KI-Assistent mit Agenten-Architektur, Tool-Use und Computer Use**

---

**Version:** 1.0  
**Datum:** Juli 2026  
**Autor:** MiMi Tech AI UG (haftungsbeschränkt)  
**Standort:** Bad Liebenzell, Schwarzwald, Deutschland  
**Lizenz:** Apache 2.0 (Code) · Dieses Whitepaper urheberrechtlich geschützt © 2026 MiMi Tech AI UG  
**Repository:** https://github.com/bemlerlabs/mimi-nox

---

## Abstract

MiMi Nox ist ein offline-first, lokaler KI-Assistent, der auf dem Endgerät des Nutzers läuft — ohne Cloud-Abhängigkeit, ohne Tracking, ohne Konto. Basierend auf einem fine-tunenden Gemma-4-Modell (E4B) mit multimodalen Fähigkeiten (Vision, Audio, Text) kombiniert MiMi Nox eine Agenten-Architektur mit 25+ integrierten Tools, darunter Headless-Browser-Automation, Desktop-Computer-Use, semantisches Langzeitgedächtnis, und Artefakt-Erzeugung (PDF, Präsentationen, SVG, Charts). Dieses Whitepaper beschreibt Architektur, Trainingspipeline, Sicherheitsmodell und die technischen Innovationen, die MiMi Nox von bestehenden Lösungen unterscheiden.

---

## Inhaltsverzeichnis

1. [Einleitung](#1-einleitung)
2. [Systemarchitektur](#2-systemarchitektur)
3. [Modell-Training & Fine-Tuning](#3-modell-training--fine-tuning)
4. [Agenten-Architektur & Tool-Use](#4-agenten-architektur--tool-use)
5. [Multimodale Fähigkeiten](#5-multimodale-fähigkeiten)
6. [Computer Use & Browser-Automation](#6-computer-use--browser-automation)
7. [Semantisches Langzeitgedächtnis](#7-semantisches-langzeitgedächtnis)
8. [Sicherheits- & Datenschutzmodell](#8-sicherheits--datenschutzmodell)
9. [Skills-System & Erweiterbarkeit](#9-skills-system--erweiterbarkeit)
10. [Mobile PWA & QR-Pairing](#10-mobile-pwa--qr-pairing)
11. [Benchmarks & Evaluierung](#11-benchmarks--evaluierung)
12. [Roadmap](#12-roadmap)
13. [Rechtlicher Hinweis](#13-rechtlicher-hinweis)

---

## 1. Einleitung

### 1.1 Das Problem

Die aktuelle Generation von KI-Assistenten ist fundamental an Cloud-Infrastrukturen gebunden. Nutzerdaten verlassen das lokale Gerät, Modelle sind proprietär, und die Abhängigkeit von Internetverbindungen macht den Einsatz in sensiblen oder offline-Szenarien unmöglich. Gleichzeitig fehlt es an lokalen Assistenten, die über einfache Chat-Funktionalität hinausgehen — zu echten Agenten mit Tool-Use, Computer Use, und persistenter Erinnerung werden.

### 1.2 Die MiMi Nox Antwort

MiMi Nox adressiert diese Lücke durch ein radikal anderes Paradigma:

- **Offline-first:** Der Kernassistent läuft vollständig lokal via Ollama mit dem Gemma-4-12B Modell. Keine Cloud, kein Tracking.
- **Agenten-Architektur:** 25+ integrierte Tools ermöglichen echte Handlungen — Dateisystemzugriff, Browser-Automation, Desktop-Steuerung, Artefakterstellung.
- **Multimodal:** Vision (Bildanalyse, OCR), Audio (Speech-to-Text, TTS), und Text in einem einzigen Modell.
- **Fine-tuned für Tool-Use:** Das Modell wurde über DPO und GRPO (Group Relative Policy Optimization) speziell für präzisen Tool-Use trainiert.
- **Privatsphäre durch Design:** Alle Daten verbleiben auf dem lokalen Gerät. Optionale Online-Features sind explizit opt-in.

### 1.3 Zielgruppe

- Entwickler und Power-User, die einen lokalen KI-Assistenten mit echten Handlungsfähigkeiten benötigen
- Organisationen mit Datenschutzanforderungen (Medizin, Recht, Forschung)
- Nutzer, die Unabhängigkeit von Cloud-Anbietern und proprietären Modellen wünschen
- Bildungseinrichtungen und öffentliche Verwaltungen mit Offline-Anforderungen

---

## 2. Systemarchitektur

### 2.1 Hocharchitektur

```
┌─────────────────────────────────────────────────┐
│                  Browser PWA                     │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │  Chat UI  │ │ Artifacts │ │  Skills Panel   │  │
│  └────┬─────┘ └────┬─────┘ └────────┬────────┘  │
│       │            │                │            │
│  ┌────▼────────────▼────────────────▼────────┐  │
│  │         Service Worker (Cache)             │  │
│  └────────────────┬──────────────────────────┘  │
└───────────────────┼─────────────────────────────┘
                    │ REST / SSE
┌───────────────────▼─────────────────────────────┐
│              FastAPI Server                      │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │ Chat API  │ │ Vision   │ │   Scheduler     │  │
│  │ Memory    │ │ Audio    │ │   Profile       │  │
│  └────┬─────┘ └──────────┘ └─────────────────┘  │
│       │                                          │
│  ┌────▼──────────────────────────────────────┐   │
│  │         Provider Router                    │   │
│  │  ┌──────────┐  ┌──────────────┐          │   │
│  │  │  Ollama   │  │ OpenAI API   │          │   │
│  │  │  (default) │  │   (opt-in)   │          │   │
│  │  └──────────┘  └──────────────┘          │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│                 Core Modules                    │
│  ┌──────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │  Chat     │ │  Tools   │ │    Memory       │  │
│  │  Engine   │ │  (25+)   │ │   (ChromaDB)    │  │
│  ├──────────┤ ├──────────┤ ├─────────────────┤  │
│  │  ReAct    │ │ Browser  │ │   Vision        │  │
│  │  Loop     │ │  (Playwright) │  Computer Use│  │
│  ├──────────┤ ├──────────┤ ├─────────────────┤  │
│  │ Artifacts │ │ Skills   │ │   Feedback      │  │
│  │ Detector  │ │  System  │ │   Corrections   │  │
│  └──────────┘ └──────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 2.2 Technologie-Stack

| Schicht | Technologie |
|---------|------------|
| Frontend | Progressive Web App (vanilla JS, CSS, HTML) |
| Backend | FastAPI (Python 3.10+) mit Uvicorn |
| KI-Inferenz | Ollama (Default), OpenAI-kompatible APIs (opt-in) |
| Modell | Gemma-4-E4B-it (fine-tuned via DPO + GRPO) |
| Vektorspeicher | ChromaDB (lokale Embeddings via all-MiniLM-L6-v2) |
| Browser-Automation | Playwright (Chromium, headless) |
| Computer Use | PyAutoGUI + MSS (Screenshots) |
| Speech | Faster-Whisper (STT), Edge-TTS / macOS TTS |
| Package Manager | hatchling (pip-installable) |
| Container | Docker + docker-compose |

### 2.3 Designprinzipien

1. **Core/UI-Trennung:** Das `core/`-Modul ist vollständig UI-unabhängig. Der FastAPI-Server ist ein dünner SSE-Layer darüber.
2. **Modulare Tools:** Jedes Tool ist ein eigenständiges Modul in `core/tools/` mit klarer Schnittstelle.
3. **Single-Codebase:** TUI, PWA, und CLI teilen sich dieselbe Core-Logik.
4. **Approval-Gating:** Sensitive Aktionen (Shell, Screenshots, Desktop-Steuerung) erfordern explizite Nutzerbestätigung.

---

## 3. Modell-Training & Fine-Tuning

### 3.1 Basismodell

MiMi Nox basiert auf **Gemma-4-E4B-it** (Google), einem 4-Milliarde-Parameter-Modell mit multimodalen Fähigkeiten (Vision-Tower, Audio-Tower, Text). Das Basismodell wurde durch ein mehrstufiges Fine-Tuning-Verfahren für den spezifischen Use-Case des Tool-Use-Assistenten optimiert.

### 3.2 Trainingspipeline

Die Fine-Tuning-Pipeline umfasst vier Stufen:

#### Stage 1: Supervised Fine-Tuning (SFT)
- Ziel: Grundlegende Tool-Use-Fähigkeiten etablieren
- Format: Instruction-following mit `<tool>` XML-Tags
- Dataset: Kuratierte Tool-Call-Beispiele

#### Stage 2: Direct Preference Optimization (DPO)
- Ziel: Präferenz für korrekte Tool-Aufrufe über Alternativen lernen
- Framework: TRL (Transformers Reinforcement Learning)
- Ergebnis: DPO-gefine-tunetes Modell als Basis für Stage 4

#### Stage 3: Dataset-Kuratie
- **8.444 Samples** über 100+ Kategorien
- Kategorien umfassen: Information Extraction, Stocks, Flight Services, Productivity, Mathematics, Machine Learning, API Calls, Web Development, Database/SQL, Cybersecurity, und viele mehr
- **20 Tools** im Registry: `fetch_webpage`, `search_web`, `send_message`, `schedule_event`, `run_code`, `analyze_image`, `analyze_audio`, `create_document`, `search_database`, `calculate`, `translate`, `summarize_text`, `generate_image`, `generate_audio`, `send_email`, `browse_website`, `query_api`, `process_file`, `control_device`

#### Stage 4: Group Relative Policy Optimization (GRPO)
- **Algorithmus:** GRPO mit LoRA (r=32, α=64)
- **GPU:** NVIDIA B200 (183GB VRAM)
- **Präzision:** FP32 (nach bf16 NaN-Diagnose)
- **Hyperparameter:**
  - Learning Rate: 2.5e-6
  - Batch Size: 4, Gradient Accumulation: 2 (effektiv 8)
  - Generations pro Prompt: 4
  - Max Completion Length: 1024
  - Max Steps: 1000
  - Temperatur: 0.9, Top-p: 0.95
  - Beta (KL): 0.04

### 3.3 Reward-Funktion (Multi-Component)

Das GRPO-Training verwendet eine gewichtete Kombination aus fünf Reward-Funktionen:

| Komponente | Gewicht | Funktion |
|-----------|---------|----------|
| **Tool Format** | 0.40 | Belohnt korrekte JSON-Struktur in Tool-Calls, bestraft Halluzinationen |
| **Task Success** | 0.25 | Belohnt erfolgreiche Aufgabenabschlüsse, bestraht Negativphrasen |
| **Safety** | 0.15 | Bestraft gefährliche Aktionen (rm -rf, shutdown, etc.) |
| **Tool Registry** | 0.10 | Validiert, dass Tool-Namen im Registry existieren |
| **Reasoning** | 0.10 | Belohnt strukturierte Argumentation und korrekte Parameter |

### 3.4 Technische Herausforderungen & Lösungen

| Herausforderung | Root Cause | Lösung |
|----------------|------------|--------|
| **bf16 NaN-Gradients** | Numerische Instabilität in gradient_checkpointing | Full FP32 Training |
| **Reward Collapse** | Konstante Rewards → Zero Variance → Zero Gradients | Bell-Curve Length-Reward, fix Regex |
| **Weight Mapping** | Gemma-4 ClippableLinear Inkompatibilität | Forward-Patch + manuelle Weight-Kopie |
| **Vision/Audio Freeze** | Multimodale Tower destabilisieren Training | Vision/Audio-Parameter frozen (requires_grad=False) |

---

## 4. Agenten-Architektur & Tool-Use

### 4.1 Tool-Calling Loop

MiMi Nox implementiert einen dreiphasigen Tool-Calling-Loop:

1. **Tool-Detection (stream=False):** Das Modell empfängt den Prompt mit Tool-Schemas und entscheidet, ob Tools benötigt werden
2. **Tool-Execution:** Jedes Tool wird via `core/tools/registry.py` ausgeführt. Sensitive Tools (Shell, Vision) erfordern Approval
3. **Final Response (stream=True):** Das Modell generiert die finale Antwort als SSE-Stream

```python
# Pseudocode des Tool-Calling Loops
for iteration in range(MAX_TOOL_ITERATIONS=5):
    response = model.chat(messages, tools=schemas, stream=False)
    if not response.tool_calls:
        break  # Kein Tool nötig → finale Antwort
    
    for tool_call in response.tool_calls:
        result = execute_tool(tool_call.name, tool_call.arguments)
        messages.append(tool_result(result))
    
    # Nächste Iteration mit Tool-Ergebnissen
```

### 4.2 ReAct-Loop mit Reflexion

Nach der Tool-Execution läuft eine automatische Qualitätsprüfung:

- **Reflexion:** Das Modell bewertet seine eigene Antwort auf Vollständigkeit und Korrektheit
- **Revision:** Bei Qualitätsmängeln wird die Antwort automatisch revidiert
- **Feedback-Loop:** 👍/👎-Feedback der Nutzer fließt in das Korrektur-Journal ein

### 4.3 Swarm-Pipeline

Der `/swarm`-Befehl ermöglicht Multi-Agent-Ausführung: komplexe Aufgaben werden in parallele Subtasks zerlegt und unabhängig ausgeführt.

---

## 5. Multimodale Fähigkeiten

### 5.1 Vision (Bildanalyse)

- **Input:** PNG, JPG, WebP, GIF, BMP Uploads
- **Pipeline:** Bild → Ollama Vision-Endpoint → Textuelle Analyse
- **Anwendungsfälle:** OCR, Dokumentenanalyse, Screenshot-Interpretation, visuelle Qualitätsprüfung

### 5.2 Audio

- **Speech-to-Text:** Faster-Whisper (lokal, keine Cloud)
- **Text-to-Speech:** Native macOS TTS oder Edge-TTS (opt-in)
- **Walkie-Talkie-Modus:** Automatische Sprachausgabe nach Voice-Input mit Waveform-Visualisierung

### 5.3 Multimodale Integration

Vision und Audio sind als native Modellkomponenten (Vision-Tower, Audio-Tower) im Gemma-4-Architektur integriert — nicht als nachgelagerte Pipeline. Dies ermöglicht kontextuelle Fusion multimodaler Inputs.

---

## 6. Computer Use & Browser-Automation

### 6.1 Desktop Computer Use

MiMi Nox kann den Desktop des Nutzers visuell steuern:

- **`take_screenshot`:** Bildschirmaufnahme via MSS
- **`vision_click`:** Screenshot → Llama-Vision analysiert Koordinaten → PyAutoGUI führt Klick aus
- **`vision_type`:** Tastatureingabe an beliebiger Desktop-Position
- **HITL-Lernmodus:** Bei Unsicherheit fragt MiMi Nox den Nutzer nach manueller Bestätigung und lernt daraus (Koordinaten-Gedächtnis per Element-Label)

### 6.2 Headless Browser (Playwright)

Ein integrierter Headless-Browser ermöglicht Web-Interaktion:

| Tool | Funktion |
|------|----------|
| `browser_go` | Navigation zu beliebiger URL |
| `browser_screenshot` | Visuelle Aufnahme der Webseite |
| `browser_click` | Vision-basiertes Klicken auf beschriebene Elemente |
| `browser_type` | Tastatureingabe im Browser |
| `browser_press` | Tastendruck (Enter, Escape, etc.) |

**Sicherheitsfeatures:**
- Cookie-Banner-Erkennung via Vision mit automatischer Akzeptierung
- 15.000-Zeichen-Truncation gegen OOM/Context-Flooding
- Singleton-Browser-Manager mit Concurrency-Safety

---

## 7. Semantisches Langzeitgedächtnis

### 7.1 Architektur

- **Vektordatenbank:** ChromaDB mit lokalem Embedding-Modell (all-MiniLM-L6-v2)
- **Speicherpfad:** `~/.mimi-nox/memory/chroma_db/`
- **Embedding:** Kosinus-Ähnlichkeit (HNSW-Index)

### 7.2 API

```python
mem = Memory()
mem.store("Ich arbeite an einem Python-Projekt mit FastAPI")
results = mem.search("Backend-Entwicklung")
# → [{text: "...", score: 0.87}, ...]
```

### 7.3 Kontext-Injection

Relevante Memory-Einträge werden automatisch in den System-Prompt injiziert:

```
--- Kontext aus deinem Gedächtnis ---
• Ich arbeite an einem Python-Projekt mit FastAPI
• Ich bevorzuge TypeScript für Frontends
--- Ende Kontext ---
```

Relevanzschwelle: Score ≥ 0.3. Max. 10 Einträge pro Query.

### 7.4 Conversation Compaction

Bei langen Konversationen wird die Historie deterministisch komprimiert:
- Projekt-Fakten, Entscheidungen, offene Tasks werden extrahiert
- Letzte Turns bleiben intakt
- System-Context wird aktualisiert

---

## 8. Sicherheits- & Datenschutzmodell

### 8.1 Lokale Defaults

| Mechanismus | Standardverhalten |
|-------------|------------------|
| Server-Binding | `127.0.0.1` (localhost only) |
| CORS | Konservativ — nur lokale Origins |
| LAN-Modus | Explizites `--lan` Flag erforderlich |
| Public Access | Explizites Opt-in (Tunnel) |

### 8.2 Tool Approval

Alle sensiblen Aktionen erfordern explizite Nutzerbestätigung:

- **Shell-Befehle:** Vorschlag → Nutzer bestätigt → Ausführung
- **Screenshots:** Approval-Gating für Desktop-Aufnahmen
- **Dateisystem:** Nur erlaubte Verzeichnisse (Home, Desktop, Documents, Downloads)
- **GUI-Aktionen:** Vision-Clicks erfordern Bestätigung bei Unsicherheit

### 8.3 Datenhoheit

- **Kein Telemetry:** Keine Analytics, kein Tracking, keine Datenübertragung
- **Lokaler Speicher:** Alle Daten auf dem lokalen Gerät
- **Kein Konto:** Keine Registrierung erforderlich für den lokalen Pfad
- **Transparente Online-Features:** Web-Recherche, öffentliche Mobile-Zugänge, und API-Provider sind klar als opt-in gekennzeichnet

### 8.4 Sicherheitsrichtlinien

- **SECURITY.md:** Detaillierte Sicherheitsrichtlinien und Meldeverfahren
- **CODE_OF_CONDUCT.md:** Verhaltenskodex für Contributors
- **CONTRIBUTING.md:** Richtlinien für sichere Contributions

---

## 9. Skills-System & Erweiterbarkeit

### 9.1 Built-in Skills

| Skill | Trigger | Funktion |
|-------|---------|----------|
| `/write` | Slash-Command | E-Mails, Notizen, Zusammenfassungen verfassen |
| `/review` | Slash-Command | Code-, Plan- oder Dokumenten-Review |
| `/files` | Slash-Command | Lokale Dateioperationen via approved Tools |
| `/pdf` | Slash-Command | PDF-Analyse und -Erstellung |
| `/scan` | Slash-Command | Screenshot-/Bildanalyse (Approval für riskante Aktionen) |
| `/svg` | Slash-Command | SVG-Asset-Erstellung |
| `/chart` | Slash-Command | Chart-Erstellung (matplotlib) |
| `/shell` | Slash-Command | Shell-Befehle (Approval erforderlich) |
| `/research` | Slash-Command | Online-Recherche (Bestätigung erforderlich) |
| `/project` | Slash-Command | Projekt-Discovery und -Analyse |

### 9.2 Skill-Architektur

Jeder Skill besteht aus:
- **SKILL.md:** Hauptdokumentation mit Trigger-Bedingungen und Schritten
- **references/:** Referenzdokumente
- **examples/:** Golden-Examples für Evaluierung
- **rubric.md:** Bewertungsrichtlinien

### 9.3 Auto-Skill-Generierung

`/learn <Thema>` generiert automatisch neue Skills via `core/skill_builder.py` — der Assistent lernt aus Nutzerinteraktionen.

### 9.4 Artefakt-Erzeugung

| Artefakt | Tool | Ausgabe |
|----------|------|---------|
| PDF-Dokumente | `create_pdf` | ReportLab-basierte PDFs mit Cover, Seitenzahlen, Sektionen |
| Pitch Decks | `create_pitch_deck` | PDF-basierte Präsentationen |
| PPTX-Decks | `create_pptx_deck` | Editierbare PowerPoint-Dateien |
| SVG-Grafiken | `create_svg` | Vektorgrafiken |
| Charts | `generate_chart` | Matplotlib-basierte Visualisierungen |
| Source Notebooks | `create_source_notebook` | NotebookLM-artige Quellen-Notebooks mit Evidence-Chunks |

---

## 10. Mobile PWA & QR-Pairing

### 10.1 PWA-Architektur

- **Manifest:** Dark-Theme (`#020504`), Install-Shortcuts, Display-Overrides
- **Service Worker:** Cache-First für Statics, Network-Only für API/Audio
- **Auto-Update:** Toast-Benachrichtigung bei neuen Service-Worker-Versionen
- **Mobile Zen-Mode:** CSS-basierte UI-Reduktion auf ≤768px Viewports

### 10.2 QR-Pairing Flow

1. MiMi Nox auf Desktop starten
2. Desktop-PWA öffnen → **Connect Phone** klicken
3. QR-Code mit Smartphone (gleiches LAN) scannen
4. Mobile PWA öffnet sich — Chat vom Smartphone aus

**Sicherheitsmodell:** LAN-first. Public Access nur via explizitem Online-Modus.

---

## 11. Benchmarks & Evaluierung

### 11.1 Evaluationsframework

- **pytest + pytest-asyncio:** Vollständige Test-Suite
- **Playwright:** Visuelle PWA-Checks
- **Skill-Evaluierung:** Golden-Examples + Rubrics pro Skill
- **CI:** GitHub Actions (Python 3.11, 3.12)

### 11.2 Training-Metriken

| Metrik | Zielwert | Status |
|--------|----------|--------|
| reward_std | > 0 (Variance) | ✓ (nach Bell-Curve Fix) |
| Entropy | > 0.01 | ✓ (Temperatur 0.9) |
| KL Divergence | 0.01–0.5 | ✓ (Beta 0.04) |
| grad_norm | > 0 | ✓ (FP32 Fix) |
| Dataset Coverage | 100+ Kategorien | ✓ (8.444 Samples) |

---

## 12. Roadmap

### Kurzfristig (Q3 2026)
- Multi-Session-Verwaltung (parallele Chats)
- Plugin-API für externe Skill-Pakete
- Lokales Embedding-Modell (Ersatz für ChromaDB default)

### Mittelfristig (Q4 2026)
- Verbesserte Conversation Compaction für 128K+ Context
- Erweiterte Computer-Use-Fähigkeiten (Drag & Drop, Multi-Monitor)
- Knowledge-Base-Integration (Offline-Wissensdatenbank)

### Langfristig (2027)
- Multi-Modal Reasoning (kombinierte Vision+Audio+Text-Reasoning)
- Distributed Agent-Netzwerk (lokale Multi-Agent-Koordination)
- On-Device Model Quantization (GGUF-Unterstützung für schwächere Hardware)

---

## 13. Rechtlicher Hinweis

### Urheberrecht

© 2026 MiMi Tech AI UG (haftungsbeschränkt), Bad Liebenzell, Deutschland.

Dieses Whitepaper ist urheberrechtlich geschützt. Die hierin beschriebenen Konzepte, Architekturansätze, Trainingsmethodiken, und Systemdesigns stellen geistiges Eigentum der MiMi Tech AI UG dar.

### Nutzung

- **Lesen und Referenzieren:** Frei gestattet
- **Zitieren:** Gestattet mit Quellenangabe
- **Vervielfältigung:** Nur mit schriftlicher Genehmigung der MiMi Tech AI UG
- **Kommerzielle Nutzung der beschriebenen Konzepte:** Die in diesem Whitepaper beschriebenen Architekturansätze, Reward-Funktionen, Trainingspipelines, und Sicherheitsmodelle sind als geschäftliche Geheimnisse und Know-how der MiMi Tech AI UG zu behandeln.

### Code-Lizenz

Der Quellcode von MiMi Nox ist unter der **Apache License 2.0** lizenziert. Dies gilt nicht für dieses Whitepaper.

### Haftungsausschluss

Dieses Whitepaper dient Informationszwecken. Die MiMi Tech AI UG übernimmt keine Haftung für die Richtigkeit, Vollständigkeit, oder Aktualität der Inhalte. Die Nutzung der beschriebenen Technologien erfolgt auf eigene Verantwortung.

---

**MiMi Tech AI UG (haftungsbeschränkt)**  
Bad Liebenzell, Schwarzwald, Deutschland  
hello@mimiai.de  
https://github.com/bemlerlabs/mimi-nox

*No cloud. No tracking. Straight from the Black Forest. ◑*
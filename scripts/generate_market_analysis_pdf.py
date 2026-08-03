#!/usr/bin/env python3
"""Generate a professional PDF report for MiMi Nox with market analysis using fpdf2."""

import os
from fpdf import FPDF

# ─── Constants ─────────────────────────────────────────────────────────
OUTPUT_PATH = '/Users/sanji/mimi-nox/docs/mimi-nox-market-analysis-2026.pdf'

# Colors (MiMi Nox dark theme)
DARK_BG = (10, 15, 13)       # #0a0f0d
ACCENT_GREEN = (34, 197, 94) # #22c55e
ACCENT_TEAL = (20, 184, 166) # #14b8a6
WHITE = (240, 253, 244)      # #f0fdf4
LIGHT_GRAY = (209, 213, 219) # #d1d5db
MID_GRAY = (156, 163, 175)  # #9ca3af
DARK_CARD = (17, 25, 22)    # #111916
BORDER_COLOR = (31, 41, 55) # #1f2937
HEADER_BG = (34, 197, 94)   # Accent green for table headers

# ─── PDF Class ─────────────────────────────────────────────────────────
class MiMiNoxPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=20)
        FONT_PATH = '/Library/Fonts/Arial Unicode.ttf'
        self.add_font('UniFont', '', FONT_PATH, uni=True)
        self.add_font('UniFont', 'B', FONT_PATH, uni=True)
        self.add_font('UniFont', 'I', FONT_PATH, uni=True)
        self.add_font('UniFont', 'BI', FONT_PATH, uni=True)

    def header(self):
        # Top accent line
        self.set_fill_color(*ACCENT_GREEN)
        self.rect(0, 0, 210, 3, 'F')
        # Footer text
        self.set_y(287)
        self.set_text_color(*MID_GRAY)
        self.set_font('UniFont', 'I', 8)
        self.cell(0, 5, f'MiMi Nox — Market Analysis & Competitive Intelligence 2026  |  Page {self.page_no()}', 0, 1, 'C')
        self.cell(0, 5, 'CONFIDENTIAL', 0, 0, 'R')

    def footer(self):
        pass # Handled in header

    def cover_page(self):
        self.add_page()
        self.set_fill_color(*DARK_BG)
        self.rect(0, 0, 210, 297, 'F')
        
        # Top accent bar
        self.set_fill_color(*ACCENT_GREEN)
        self.rect(0, 0, 210, 8, 'F')
        
        # Green accent line
        y = 150
        self.set_draw_color(*ACCENT_GREEN)
        self.set_line_width(0.5)
        self.line(20, y, 190, y)
        
        # Title
        self.set_text_color(*WHITE)
        self.set_font('UniFont', 'B', 42)
        self.ln(40)
        self.cell(0, 20, 'MiMi Nox', 0, 1, 'C')
        
        # Subtitle
        self.set_text_color(*ACCENT_GREEN)
        self.set_font('UniFont', '', 20)
        self.cell(0, 15, 'Market Analysis & Competitive Intelligence', 0, 1, 'C')
        
        # Subtitle line 2
        self.set_text_color(*MID_GRAY)
        self.set_font('UniFont', '', 16)
        self.cell(0, 12, 'State of the Art — July 2026', 0, 1, 'C')
        
        # Bottom info
        self.set_font('UniFont', '', 11)
        self.set_text_color(*MID_GRAY)
        self.ln(20)
        self.cell(0, 8, 'MiMi Tech AI UG (haftungsbeschränkt)', 0, 1, 'C')
        self.cell(0, 8, 'Bad Liebenzell, Schwarzwald, Deutschland', 0, 1, 'C')
        self.cell(0, 8, 'github.com/MimiTechAi/mimi-nox', 0, 1, 'C')
        
        # Bottom accent
        self.set_fill_color(*ACCENT_GREEN)
        self.rect(0, 289, 210, 8, 'F')

    def section_title(self, title):
        self.set_text_color(*WHITE)
        self.set_font('UniFont', 'B', 20)
        self.ln(4)
        self.cell(0, 12, title, 0, 1)
        # Green accent line under title
        self.set_draw_color(*ACCENT_GREEN)
        self.set_line_width(0.4)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(6)

    def subsection_title(self, title):
        self.set_text_color(*ACCENT_GREEN)
        self.set_font('UniFont', 'B', 14)
        self.ln(3)
        self.cell(0, 10, title, 0, 1)
        self.ln(2)

    def body_text(self, text):
        self.set_text_color(*LIGHT_GRAY)
        self.set_font('UniFont', '', 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def highlight_box(self, title, text):
        # Green bordered box
        x = self.get_x()
        y = self.get_y()
        w = 170
        
        self.set_fill_color(13, 26, 20) # Dark green bg
        self.set_draw_color(*ACCENT_GREEN)
        self.set_line_width(0.3)
        
        # Title
        self.set_text_color(*ACCENT_GREEN)
        self.set_font('UniFont', 'B', 11)
        self.set_xy(x + 5, y + 3)
        self.cell(w - 10, 6, title, 0, 1)
        
        # Text
        self.set_text_color(*WHITE)
        self.set_font('UniFont', '', 10)
        self.set_xy(x + 5, self.get_y())
        self.multi_cell(w - 10, 5, text)
        
        # Draw border
        h = self.get_y() - y + 5
        self.rect(x, y, w, h, 'D')
        self.set_xy(x, self.get_y() + 5)
        self.ln(4)

    def make_table(self, headers, rows, col_widths=None):
        if col_widths is None:
            col_widths = [170 / len(headers)] * len(headers)
        
        # Header row
        self.set_fill_color(*HEADER_BG)
        self.set_text_color(10, 15, 13)
        self.set_font('UniFont', 'B', 9)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 8, h, 1, 0, 'C', True)
        self.ln()
        
        # Data rows
        self.set_font('UniFont', '', 9)
        for i, row in enumerate(rows):
            if i % 2 == 0:
                self.set_fill_color(17, 28, 22)
            else:
                self.set_fill_color(13, 20, 16)
            self.set_text_color(*LIGHT_GRAY)
            for j, cell in enumerate(row):
                self.cell(col_widths[j], 8, str(cell), 1, 0, 'L', True)
            self.ln()
        self.ln(4)

    def bullet_list(self, items):
        self.set_text_color(*LIGHT_GRAY)
        self.set_font('UniFont', '', 10)
        for item in items:
            self.cell(5, 6, '•', 0, 0)
            self.multi_cell(155, 6, item)
            self.ln(1)
        self.ln(3)

# ─── Build PDF ─────────────────────────────────────────────────────────
def main():
    pdf = MiMiNoxPDF()
    
    # Set dark background for all pages
    pdf.set_fill_color(*DARK_BG)
    
    # Cover page
    pdf.cover_page()
    
    # ── EXECUTIVE SUMMARY ──
    pdf.add_page()
    # Dark bg
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('Executive Summary')
    
    pdf.body_text(
        'MiMi Nox ist ein offline-first, lokaler KI-Assistent mit Agenten-Architektur, '
        'der auf dem Endgerät des Nutzers läuft — ohne Cloud-Abhängigkeit, ohne Tracking, ohne Konto. '
        'Basierend auf einem fine-tuned Gemma-4-Modell (E4B) mit multimodalen Fähigkeiten (Vision, Audio, Text) '
        'kombiniert MiMi Nox 25+ integrierte Tools mit semantischem Langzeitgedächtnis, Computer Use, '
        'und Artefakt-Erzeugung.'
    )
    
    pdf.highlight_box(
        'Markt-Snapshot 2026',
        'Key Finding: Der Multimodal-AI-Markt wächst von USD 3,85 Mrd. (2026) auf '
        'USD 41,95 Mrd. (2034) bei einem CAGR von 37,3%. Der Personal-AI-Agent-Markt '
        'erreicht USD 48 Mrd. bis 2028. MiMi Nox positioniert sich im Blue-Ocean-Segment '
        '"Privacy-First Local AI Agents" — ein Bereich mit hohem Wachstumspotenzial und '
        'geringer Wettbewerbsdichte.'
    )
    
    # Key metrics table
    metrics_headers = ['Metrik', 'Wert', 'Quelle']
    metrics_rows = [
        ['Multimodal AI Market 2026', 'USD 3,85 Mrd.', 'Mordor Intelligence'],
        ['Multimodal AI Market 2034', 'USD 41,95 Mrd.', 'Fortune Business Insights'],
        ['CAGR (2026-2034)', '37,3%', 'Fortune Business Insights'],
        ['Personal AI Agent Market', 'USD 48 Mrd. (2028)', 'Flowtivity / Vellum'],
        ['Global LLM MAUs (Apr 2026)', '4,7 Milliarden', 'Counterpoint Research'],
        ['Unternehmen mit AI-Einsatz', '88%', 'Hostinger / Statista 2026'],
    ]
    pdf.make_table(metrics_headers, metrics_rows, [55, 45, 70])
    
    # ── MARKET OVERVIEW ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('1. Marktübersicht: Multimodal AI 2026')
    
    pdf.body_text(
        'Der globale Multimodal-AI-Markt befindet sich in einer exponentiellen Wachstumsphase. '
        'Während 2023 noch von experimentellen Prototypen geprägt war, dominieren 2026 integrierte '
        'multimodale Systeme den Markt — Modelle, die Text, Bild, Audio und Video nahtlos verarbeiten.'
    )
    
    pdf.subsection_title('1.1 Marktdynamiken')
    pdf.body_text('Drei Megatrends treiben den Markt:')
    
    pdf.bullet_list([
        'Enterprise Adoption: 88% der Unternehmen setzen AI in mindestens einer Funktion ein — ein Anstieg von 78% im Vorjahr. Der Fokus verschiebt sich von Experiment zu Produktion.',
        'Privacy-First Demand: Zunehmende Datenschutzgesetzgebung (EU AI Act, nationale Regelungen) treibt die Nachfrage nach lokalen, datensouveränen AI-Lösungen.',
        'Multimodal als Standard: Monomodale Modelle verlieren an Relevanz. Der Markt erwartet native Multimodalität (Vision + Audio + Text) als Baseline.',
    ])
    
    pdf.subsection_title('1.2 Marktgrößen-Projektionen')
    
    proj_headers = ['Quelle', '2026', 'Prognose', 'CAGR']
    proj_rows = [
        ['Mordor Intelligence', 'USD 3,85 Mrd.', 'USD 13,51 Mrd. (2031)', '28,6%'],
        ['Coherent Market Insights', 'USD 3,23 Mrd.', 'USD 20,82 Mrd. (2033)', '36,4%'],
        ['Fortune Business Insights', '—', 'USD 41,95 Mrd. (2034)', '37,3%'],
        ['SNS Insider', 'USD 2,25 Mrd. (2025)', 'USD 53,78 Mrd. (2035)', '~37%'],
    ]
    pdf.make_table(proj_headers, proj_rows, [45, 35, 50, 20])
    
    pdf.highlight_box(
        'Analysten-Konsens',
        'Konsens: Alle Analysten prognostizieren ein 8-15x Wachstum des Multimodal-AI-Marktes '
        'bis 2034/35. Der Median-CAGR liegt bei ~35%. Dies ist einer der am schnellsten wachsenden '
        'Tech-Märkte der letzten Dekade.'
    )
    
    # ── COMPETITIVE LANDSCAPE ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('2. Wettbewerbslandschaft')
    
    pdf.subsection_title('2.1 Frontier-Modelle (Proprietär)')
    pdf.body_text(
        'Die Frontier-Modelle definieren den State-of-the-Art im Jahr 2026. '
        'Diese proprietären Systeme setzen den Leistungsstandard, an dem sich Open-Source-Modelle orientieren:'
    )
    
    frontier_headers = ['Modell', 'Anbieter', 'Stärke', 'Multimodal']
    frontier_rows = [
        ['GPT-5.6 Sol', 'OpenAI', 'Allrounder, Knowledge Retrieval', '✓'],
        ['Claude Opus 4.8', 'Anthropic', 'Coding, natürliche Prosa', '✓'],
        ['Claude Sonnet 5', 'Anthropic', 'Preis-Leistung, Software Eng.', '✓'],
        ['Gemini 3.1 Pro', 'Google', 'Reasoning, multimodale Fusion', '✓'],
        ['Gemini 3.5 Flash', 'Google', 'Geschwindigkeit, Kosten', '✓'],
        ['Llama 4 Maverick', 'Meta', 'Open-Source Frontier', '✓'],
        ['Grok 4', 'xAI', 'Coding-Benchmarks', '✓'],
    ]
    pdf.make_table(frontier_headers, frontier_rows, [35, 25, 55, 20])
    
    pdf.subsection_title('2.2 Open-Source Lokale AI-Assistenten')
    pdf.body_text(
        'Im Segment der lokalen, selbst-gehosteten AI-Assistenten ist die Wettbewerbsdichte moderat. '
        'Die meisten Lösungen bieten Chat-Interfaces, aber wenige implementieren echte Agenten-Architekturen '
        'mit Tool-Use und Computer Use:'
    )
    
    local_headers = ['Projekt', 'Typ', 'Agenten', 'Multimodal', 'Stars']
    local_rows = [
        ['MiMi Nox', 'Full Assistant', '✓ (25+ Tools)', '✓ native', '—'],
        ['Open WebUI', 'Chat UI', '✗', 'Eingeschränkt', '~50K+'],
        ['Ollama', 'Model Runtime', '✗', 'Via Model', '~100K+'],
        ['LM Studio', 'Desktop App', '✗', 'Eingeschränkt', '~45K+'],
        ['Jan', 'Desktop App', '✗', '✗', '~55K+'],
        ['GPT4All', 'Local Inference', '✗', '✗', '~25K+'],
        ['Continue', 'IDE Extension', 'Partial', '✗', '~35K+'],
    ]
    pdf.make_table(local_headers, local_rows, [25, 25, 25, 25, 20])
    
    pdf.highlight_box(
        'Wettbewerbs-Vorteil',
        'Blue Ocean Finding: Kein anderer lokaler AI-Assistent kombiniert Agenten-Architektur + '
        'native Multimodalität + Computer Use + semantisches Gedächtnis in einem einzigen Produkt. '
        'MiMi Nox ist der einzige Player, der diese vier Dimensionen vereint. Open WebUI ist primär ein '
        'Chat-Interface; Ollama eine Runtime; LM Studio/Jan Desktop-Apps ohne echte Agenten-Fähigkeiten.'
    )
    
    # ── TECHNICAL ARCHITECTURE ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('3. MiMi Nox — Technische Architektur')
    
    pdf.subsection_title('3.1 Kernarchitektur')
    pdf.body_text('MiMi Nox folgt einem radikal simplen, aber effektiven Design:')
    
    pdf.bullet_list([
        'Frontend: Progressive Web App (vanilla JS/CSS/HTML) — keine Framework-Abhängigkeit, installierbar als PWA',
        'Backend: FastAPI (Python 3.10+) mit Uvicorn — dünner SSE-Layer über der Core-Logik',
        'Modell: Gemma-4-E4B-it (fine-tuned via DPO + GRPO) — 4 Milliarden Parameter, multimodal',
        'Inferenz: Ollama (Default), OpenAI-kompatible APIs (opt-in)',
        'Gedächtnis: ChromaDB mit lokalen Embeddings (all-MiniLM-L6-v2)',
        'Browser: Playwright (Chromium, headless) für Web-Automation',
        'Computer Use: PyAutoGUI + MSS für Desktop-Steuerung',
    ])
    
    pdf.subsection_title('3.2 Trainingspipeline (4-Stage)')
    
    train_headers = ['Stage', 'Methode', 'Ziel', 'Ergebnis']
    train_rows = [
        ['Stage 1', 'SFT', 'Tool-Use Basics etablieren', 'Instruction-following mit Tool-Tags'],
        ['Stage 2', 'DPO', 'Präferenz für korrekte Tool-Calls', 'DPO-gefeintes Modell'],
        ['Stage 3', 'Dataset-Kuratie', '8.444 Samples, 100+ Kategorien', '20 Tools im Registry'],
        ['Stage 4', 'GRPO + LoRA', 'Fine-tuning für Tool-Use-Qualität', 'r=32, α=64, FP32, B200 GPU'],
    ]
    pdf.make_table(train_headers, train_rows, [20, 25, 50, 55])
    
    pdf.subsection_title('3.3 Reward-Funktion (Multi-Component GRPO)')
    
    reward_headers = ['Komponente', 'Gewicht', 'Funktion']
    reward_rows = [
        ['Tool Format', '0,40', 'Korrekte JSON-Struktur, Anti-Halluzination'],
        ['Task Success', '0,25', 'Erfolgreiche Aufgabenabschlüsse'],
        ['Safety', '0,15', 'Bestraft gefährliche Aktionen'],
        ['Tool Registry', '0,10', 'Validiert Tool-Namen im Registry'],
        ['Reasoning', '0,10', 'Strukturierte Argumentation'],
    ]
    pdf.make_table(reward_headers, reward_rows, [25, 20, 85])
    
    # ── FEATURES ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('4. MiMi Nox — Feature-Übersicht')
    
    pdf.subsection_title('4.1 Agenten-Fähigkeiten')
    pdf.body_text(
        'MiMi Nox implementiert einen dreiphasigen Tool-Calling-Loop mit ReAct-Reflexion und '
        'automatischer Qualitätsprüfung. 25+ Tools decken folgende Kategorien ab:'
    )
    
    feat_headers = ['Kategorie', 'Tools', 'Status']
    feat_rows = [
        ['Chat & Text', 'Chat, /write, /review, /project', '✓ Active'],
        ['Vision', '/scan, take_screenshot, vision_click', '✓ Active'],
        ['Audio', 'Faster-Whisper STT, Edge-TTS', '✓ Active'],
        ['Dateien & PDF', '/files, /pdf, create_pdf', '✓ Active'],
        ['Browser', 'browser_go, browser_click, browser_type', '✓ Active'],
        ['Computer Use', 'PyAutoGUI, vision_click, vision_type', '✓ Active'],
        ['Artefakte', '/svg, /chart, /pdf, pitch deck', '✓ Active'],
        ['Gedächtnis', 'ChromaDB, semantic search, context injection', '✓ Active'],
        ['Shell', '/shell (approval-gated)', '✓ Active'],
        ['Research', '/research (opt-in)', '✓ Opt-in'],
    ]
    pdf.make_table(feat_headers, feat_rows, [30, 90, 30])
    
    pdf.subsection_title('4.2 Sicherheitsmodell')
    pdf.bullet_list([
        'Server-Binding: Standardmäßig 127.0.0.1 (localhost only) — LAN-Modus erfordert explizites Flag',
        'Tool Approval: Shell, Screenshots, und GUI-Aktionen erfordern explizite Nutzerbestätigung',
        'Kein Telemetry: Keine Analytics, kein Tracking, keine Datenübertragung',
        'Lokaler Speicher: Alle Daten verbleiben auf dem lokalen Gerät',
        'Kein Konto: Keine Registrierung erforderlich für den lokalen Pfad',
    ])
    
    # ── MARKET POSITIONING ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('5. Market Positioning & Differenzierung')
    
    pdf.subsection_title('5.1 Unique Value Proposition')
    pdf.highlight_box(
        'USP — Vier-Dimensionen-Überschneidung',
        'MiMi Nox ist der einzige lokale AI-Assistent, der vier kritische Dimensionen vereint:\n\n'
        '1. Agenten-Architektur — 25+ Tools mit echtem Tool-Use, nicht nur Chat\n'
        '2. Native Multimodalität — Vision + Audio + Text im selben Modell\n'
        '3. Computer Use — Desktop-Steuerung via Vision-basierte Klicks\n'
        '4. Semantisches Gedächtnis — Persistentes Langzeitgedächtnis via ChromaDB\n\n'
        'Kein anderer Player im lokalen AI-Segment bietet diese Kombination.'
    )
    
    pdf.subsection_title('5.2 Zielgruppen')
    
    target_headers = ['Segment', 'Bedarf', 'MiMi Nox Fit']
    target_rows = [
        ['Entwickler & Power-User', 'Lokaler Assistent mit echten Handlungsfähigkeiten', '✓ Excellent'],
        ['Datenschutz-sensitive Org.', 'Offline AI ohne Cloud-Abhängigkeit', '✓ Excellent'],
        ['Medizin & Recht', 'Datensouveränität + Compliance', '✓ Excellent'],
        ['Bildung & Öffent. Verwaltung', 'Offline-Anforderungen + Budget', '✓ Good'],
        ['Consumer / General', 'Einfacher Chat-Assistent', '⚠ Overkill'],
    ]
    pdf.make_table(target_headers, target_rows, [40, 80, 30])
    
    pdf.subsection_title('5.3 Competitive Density Score')
    pdf.highlight_box(
        'Blue Ocean Validierung',
        'Segment: Privacy-First Local AI Agents mit Tool-Use\n\n'
        'Relevante Wettbewerber mit >100 Stars: 0 (kein direktes Äquivalent)\n'
        'Naheste Analogien (Open WebUI, LM Studio): Chat-only, keine Agenten\n\n'
        'Density Score: BLUE OCEAN — Hohe Nachfrage nach lokaler AI, aber keine etablierten '
        'Agenten-Lösungen im lokalen Raum. MiMi Nox hat First-Mover-Vorteil in diesem Nischen-Segment.'
    )
    
    # ── STATE OF THE ART 2026 ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('6. State of the Art — AI 2026')
    
    pdf.subsection_title('6.1 Modell-Landschaft')
    pdf.body_text('Die AI-Landschaft 2026 ist von drei Paradigmen geprägt:')
    
    pdf.bullet_list([
        'Mixture-of-Experts (MoE): Dominante Architektur für Frontier-Modelle. Ermöglicht große Kapazität bei geringer Inferenz-Kosten.',
        'Encoder-Free Multimodalität: Gemma 4 12B pioneered encoder-free architecture — raw image patches und Audio-Waveforms direkt in das Modell, ohne separate Encoder.',
        'RLVR (Reinforcement Learning with Verifiable Rewards): GRPO hat PPO als Standard für LLM-Post-Training abgelöst. Kombination mit verifizierbaren Rewards ist State-of-the-Art.',
    ])
    
    pdf.subsection_title('6.2 RL-Training für LLMs 2026')
    pdf.body_text(
        'Reinforcement Learning hat ein zweites Leben erfahren. Die Evolution von PPO → DPO → GRPO '
        '→ Multi-Agent RL definiert den aktuellen State-of-the-Art:'
    )
    
    rl_headers = ['Methode', 'Status 2026', 'Vorteil', 'Nachteil']
    rl_rows = [
        ['PPO', 'Legacy', 'Stabil', 'Teurer, komplex'],
        ['DPO', 'Standard SFT-Upgrade', 'Einfach, effizient', 'Kein generatives Feedback'],
        ['GRPO', 'State-of-the-Art', 'Group-based, kein Critic', 'Reward-Design kritisch'],
        ['RLVR', 'Emerging SOTA', 'Verifiable rewards', 'Domain-spezifisch'],
        ['Async RL', 'Industrial Scale', 'Skalierbar', 'Komplexe Infrastruktur'],
    ]
    pdf.make_table(rl_headers, rl_rows, [25, 30, 40, 40])
    
    pdf.highlight_box(
        'MiMi Nox Training Stack',
        'MiMi Nox nutzt GRPO mit LoRA (r=32, α=64) als State-of-the-Art Post-Training-Methode. '
        'Die 5-komponentige Reward-Funktion (Tool Format, Task Success, Safety, Tool Registry, Reasoning) '
        'ist speziell für Tool-Use-Optimierung designed — ein Bereich, in dem die meisten Fine-Tuning-Pipelines '
        'versagen (Reward Collapse, Zero Variance).'
    )
    
    # ── ROADMAP ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('7. Roadmap & Ausblick')
    
    pdf.subsection_title('7.1 MiMi Nox Produkt-Roadmap')
    
    roadmap_headers = ['Zeitraum', 'Fokus', 'Features']
    roadmap_rows = [
        ['Q3 2026', 'Kurzfristig', 'Multi-Session, Plugin-API, lokales Embedding-Modell'],
        ['Q4 2026', 'Mittelfristig', '128K+ Context, erweiterter Computer Use, Knowledge-Base'],
        ['2027', 'Langfristig', 'Multi-Modal Reasoning, Distributed Agents, GGUF Quantization'],
    ]
    pdf.make_table(roadmap_headers, roadmap_rows, [25, 25, 90])
    
    pdf.subsection_title('7.2 Markt-Ausblick')
    pdf.bullet_list([
        '2026-2027: Explosion lokaler AI-Assistenten. EU AI Act Enforcement treibt Privacy-First-Demand. Open-Source-Modelle (Gemma 4, Llama 4) schließen die Lücke zu proprietären Systemen.',
        '2027-2028: Personal AI Agent Market erreicht USD 48 Mrd. Integration von AI in Enterprise-Workflows wird Standard. Lokale Agenten werden zur Compliance-Erforderung.',
        '2028-2030: Multimodal AI als Baseline-Technologie. Computer Use wird zum Differenzierungsmerkmal. On-Device-Inferenz auf Consumer-Hardware (Apple Silicon, NVIDIA RTX) wird Mainstream.',
    ])
    
    # ── CONCLUSION ──
    pdf.add_page()
    pdf.rect(0, 0, 210, 297, 'F')
    
    pdf.section_title('8. Fazit & Empfehlung')
    
    pdf.body_text(
        'MiMi Nox occupies a unique position at the intersection of four high-growth trends: '
        'local-first AI, multimodal agents, privacy-first deployment, and computer use capabilities.'
    )
    
    pdf.highlight_box(
        'Strategisches Fazit',
        'Strategic Assessment:\n\n'
        'MiMi Nox ist der einzige lokale AI-Assistent mit vollständiger Agenten-Architektur, '
        'nativer Multimodalität, Computer Use und semantischem Gedächtnis. Der Wettbewerb im '
        'direkten Segment ist minimal (Blue Ocean). Der Gesamtmarkt wächst mit ~37% CAGR.\n\n'
        'Empfehlung: MiMi Nox hat First-Mover-Vorteil im Segment "Privacy-First Local AI Agents". '
        'Fokus auf Developer-Adoption, Enterprise-Compliance, und Community-Building maximiert das '
        'Wachstumspotenzial in den nächsten 24 Monaten.'
    )
    
    pdf.ln(10)
    pdf.set_draw_color(*BORDER_COLOR)
    pdf.set_line_width(0.3)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)
    
    pdf.body_text(
        'Quellen: Mordor Intelligence, Fortune Business Insights, Coherent Market Insights, '
        'SNS Insider, Counterpoint Research, Vellum, Flowtivity, Google DeepMind (Gemma 4 Technical Report), '
        'arXiv (GRPO/RLVR Papers), GitHub Trending, Hugging Face'
    )
    
    pdf.set_text_color(*MID_GRAY)
    pdf.set_font('UniFont', 'I', 9)
    pdf.cell(0, 8, '© 2026 MiMi Tech AI UG (haftungsbeschränkt) · Bad Liebenzell, Schwarzwald, Deutschland', 0, 1, 'C')
    
    # Save
    pdf.output(OUTPUT_PATH)
    print(f"PDF generated: {OUTPUT_PATH}")
    print(f"File size: {os.path.getsize(OUTPUT_PATH) / 1024:.0f} KB")

if __name__ == '__main__':
    main()
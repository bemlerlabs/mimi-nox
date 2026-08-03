#!/usr/bin/env python3
"""Generate MiMi Nox Whitepaper as professional McKinsey-style PDF via Playwright."""
import asyncio
from playwright.async_api import async_playwright

HTML = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
@page { size: A4; margin: 20mm; @bottom-center { content: counter(page); font-size: 9pt; color: #667; } }
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; color: #1a1a2e; line-height: 1.6; }
.cover { display: flex; flex-direction: column; justify-content: center; height: 297mm; background: linear-gradient(135deg, #0a1628 0%, #16213e 50%, #0f3460 100%); color: #fff; padding: 40mm; page-break-after: always; }
.cover h1 { font-size: 42pt; font-weight: 700; letter-spacing: -1px; margin-bottom: 8pt; }
.cover .subtitle { font-size: 18pt; color: #e94560; font-weight: 300; margin-bottom: 40pt; }
.cover .meta { font-size: 11pt; color: #8899aa; line-height: 1.8; }
.cover .logo { font-size: 14pt; color: #e94560; font-weight: 600; letter-spacing: 2px; margin-bottom: 60pt; }
h2 { font-size: 22pt; color: #0a1628; border-left: 4px solid #e94560; padding-left: 16px; margin: 40pt 0 20pt; page-break-after: avoid; }
h3 { font-size: 15pt; color: #16213e; margin: 24pt 0 12pt; font-weight: 600; }
p, li { font-size: 11pt; color: #2d3748; margin-bottom: 10pt; }
ul { padding-left: 24px; margin-bottom: 16pt; }
li { margin-bottom: 6pt; }
.highlight { background: #f7fafc; border-left: 3px solid #e94560; padding: 16px 20px; margin: 20pt 0; border-radius: 0 8px 8px 0; }
.highlight p { font-size: 10.5pt; color: #4a5568; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20pt 0; }
.card { background: #f7fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
.card h4 { font-size: 12pt; color: #0a1628; margin-bottom: 8pt; }
.card p { font-size: 10pt; color: #4a5568; }
.table { width: 100%; border-collapse: collapse; margin: 20pt 0; font-size: 10pt; }
.table th { background: #0a1628; color: #fff; padding: 10px 12px; text-align: left; font-weight: 600; }
.table td { padding: 10px 12px; border-bottom: 1px solid #e2e8f0; }
.table tr:nth-child(even) { background: #f7fafc; }
.toc { margin: 30pt 0; }
.toc-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px dotted #cbd5e0; font-size: 11pt; }
.toc-item span:first-child { color: #1a1a2e; font-weight: 500; }
.toc-item span:last-child { color: #667; }
footer { position: fixed; bottom: 0; left: 40mm; right: 40mm; text-align: center; font-size: 8pt; color: #667; border-top: 1px solid #e2e8f0; padding-top: 8pt; }
</style>
</head>
<body>

<div class="cover">
<div class="logo">MIMI NOX</div>
<h1>Whitepaper</h1>
<div class="subtitle">Multimodale KI-Agenten-Plattform — Architektur, Training &amp; Deployment</div>
<div class="meta">
Version 1.0 · Juli 2026<br>
Autor: MiMi Nox Research Team<br>
Stack: Gemma 4B · GRPO · LoRA FP32 · Vision/Audio · Real-Time WebSocket
</div>
</div>

<div style="padding: 20mm 40mm;">
<h2>Inhaltsverzeichnis</h2>
<div class="toc">
<div class="toc-item"><span>1. Executive Summary</span><span>3</span></div>
<div class="toc-item"><span>2. Problemstellung &amp; Marktlage</span><span>4</span></div>
<div class="toc-item"><span>3. Architektur-Übersicht</span><span>5</span></div>
<div class="toc-item"><span>4. Multimodale Fähigkeiten</span><span>6</span></div>
<div class="toc-item"><span>5. Training-Pipeline (GRPO v17)</span><span>7</span></div>
<div class="toc-item"><span>6. Reward-Engineering</span><span>8</span></div>
<div class="toc-item"><span>7. Agent-Toolkit &amp; Browser-Integration</span><span>9</span></div>
<div class="toc-item"><span>8. Real-Time WebSocket Dashboard</span><span>10</span></div>
<div class="toc-item"><span>9. SDK &amp; Developer Experience</span><span>11</span></div>
<div class="toc-item"><span>10. Deployment &amp; Infrastruktur</span><span>12</span></div>
<div class="toc-item"><span>11. Sicherheitskonzept</span><span>13</span></span></div>
<div class="toc-item"><span>12. Performance-Benchmarks</span><span>14</span></div>
<div class="toc-item"><span>13. Roadmap &amp; Ausblick</span><span>15</span></div>
</div>

<h2>1. Executive Summary</h2>
<p>MiMi Nox ist eine <strong>multimodale KI-Agenten-Plattform</strong>, die Sprach-, Visuelle und Audio-Verarbeitung in einer einzigen Architektur vereint. Basierend auf dem Gemma 4B Foundation Model wurde das System mittels <strong>Group Relative Policy Optimization (GRPO)</strong> mit LoRA-Adaption (FP32) feinabgestimmt.</p>
<div class="highlight">
<p><strong>Kernaussage:</strong> MiMi Nox erreicht durch die Integration von Vision- und Audio-Modulen mit einem textuellen Backbone eine einheitliche Multimodalität — ohne separate Modelle pro Modalität. Die GRPO-basierte Training-Pipeline mit varianzreichem Reward-Design verhindert Entropie-Kollaps und ermöglicht kontinuierliches Lernen.</p>
</div>

<h2>2. Problemstellung &amp; Marktlage</h2>
<h3>2.1 Aktuelle Limitationen</h3>
<ul>
<li><strong>Fragmentierte Multimodalität:</strong> Die meisten Systeme nutzen separate Modelle für Text, Vision und Audio — keine echte Integration.</li>
<li><strong>Reward Collapse in RL-Training:</strong> Flache Reward-Funktionen führen zu varianzfreien Signalen → Zero-Gradients → Zero-Learning.</li>
<li><strong>Entropie-Kollaps:</strong> Deterministische Modelle ohne Exploration → kein Lernen möglich.</li>
<li><strong>Keine Real-Time Observability:</strong> Agent-Aktionen sind nicht live nachverfolgbar.</li>
</ul>

<h2>3. Architektur-Übersicht</h2>
<div class="grid">
<div class="card"><h4>Core Engine</h4><p>chat.py — zentraler Chat-Loop mit Tool-Integration, Memory-System (ChromaDB) und Kontext-Management.</p></div>
<div class="card"><h4>Vision Module</h4><p>vision.py — Bildverarbeitung mit CLIP-basiertem Encoder, integriert ins Hauptmodell via Weight-Remapping.</p></div>
<div class="card"><h4>Tool Registry</h4><p>registry.py — dynamische Tool-Registrierung mit Browser-Tools, PDF-Generierung und Dateisystem-Zugriff.</p></div>
<div class="card"><h4>Memory System</h4><p>memory.py — ChromaDB-basiertes semantisches Gedächtnis mit Embedding-Suche und Kontext-Komprimierung.</p></div>
</div>

<h2>4. Multimodale Fähigkeiten</h2>
<h3>4.1 Vision</h3>
<p>Das Vision-Modul verarbeitet Bilder via CLIP-Encoder und projiziert die Embeddings in den gemeinsamen Raum des Hauptmodells. Kritisch: <strong>Weight Remapping</strong> verhindert NaN-Probleme bei der Integration.</p>
<h3>4.2 Audio</h3>
<p>Audio-Eingabe wird via Whisper-basiertem Encoder transkribiert und als Kontext in den Chat-Loop injiziert. Audio-Generierung erfolgt via AudioCraft/MusicGen.</p>

<h2>5. Training-Pipeline (GRPO v17)</h2>
<h3>5.1 Pipeline-Übersicht</h3>
<table class="table">
<tr><th>Parameter</th><th>Wert</th><th>Begründung</th></tr>
<tr><td>Model</td><td>Gemma 4B</td><td>Balance aus Performance und Effizienz</td></tr>
<tr><td>LoRA Rank (r)</td><td>32</td><td>Typisch für Multimodalität</td></tr>
<tr><td>LoRA α</td><td>64</td><td>2×r für stabile Adaption</td></tr>
<tr><td>Learning Rate</td><td>2e-4</td><td>Konservativ für FP32</td></tr>
<tr><td>Batch Size</td><td>2 (accum=4)</td><td>Effektiver Batch=8, passt in GPU-Memory</td></tr>
<tr><td>Steps</td><td>1000</td><td>Vollständige Konvergenz</td></tr>
<tr><td>save_steps</td><td>25</td><td>Frequente Checkpoints</td></tr>
</table>

<h2>6. Reward-Engineering</h2>
<h3>6.1 Reward-Funktionen (v17)</h3>
<div class="highlight">
<p><strong>Critical Fix:</strong> Reward Collapse ab Step 400 in v16 durch flaches <code>reward_completion_length</code> (konstant >1800 Tokens) → reward_std=0 → Zero-Gradients.</p>
<p><strong>v17 Lösung:</strong> Bell-curve Length-Reward + fix Regex Tool-Call + reduzierte Safety-Weight → varianzreiches Signal.</p>
</div>
<h3>6.2 Reward-Komponenten</h3>
<ul>
<li><strong>Length Reward:</strong> Bell-curve (optimal: 800-1200 Tokens) statt flach >1800</li>
<li><strong>Tool-Call Reward:</strong> Regex-basierte Erkennung korrekter Tool-Aufrufe</li>
<li><strong>Safety Reward:</strong> Reduziertes Gewicht, verhindert Dominanz</li>
<li><strong>Format Reward:</strong> Korrekte JSON/Markdown-Struktur</li>
</ul>

<h2>7. Agent-Toolkit &amp; Browser-Integration</h2>
<h3>7.1 Tool-Kategorien</h3>
<div class="grid">
<div class="card"><h4>Browser Tools</h4><p>browser_tools.py — Playwright-basierte Web-Interaktion, Form-Ausfüllung, Screenshot, Navigation.</p></div>
<div class="card"><h4>PDF Tools</h4><p>pdf_tools.py — PDF-Generierung via Playwright HTML→PDF, McKinsey-Style Templates.</p></div>
<div class="card"><h4>Dateisystem</h4><p>Lesen/Schreiben von Dateien, Suchen via ripgrep, Git-Integration.</p></div>
<div class="card"><h4>Terminal</h4><p>Shell-Befehle, Build-Systeme, Prozess-Management, Hintergrund-Jobs.</p></div>
</div>

<h2>8. Real-Time WebSocket Dashboard</h2>
<p>Das Dashboard (React+Vite+TS) zeigt Agent-Aktionen in Echtzeit via WebSocket-Verbindung:</p>
<ul>
<li><strong>Live Traces:</strong> Tool-Aufrufe, Response-Zeiten, Token-Nutzung</li>
<li><strong>Cost Tracking:</strong> Echtzeit-Kosten pro Session/Workspace</li>
<li><strong>8 Pages:</strong> Dashboard, Traces, Workspaces, Settings, Docs, API, SDK, Status</li>
<li><strong>WS Client:</strong> ws.ts mit useWebSocket Hook, Auto-Reconnect, Heartbeat</li>
</ul>

<h2>9. SDK &amp; Developer Experience</h2>
<h3>9.1 Python SDK</h3>
<p>Vollständiges Python SDK mit CLI-Integration:</p>
<ul>
<li><code>agentwatch init</code> — Projekt-Initialisierung</li>
<li><code>agentwatch dev</code> — Lokale Entwicklungsumgebung</li>
<li><code>agentwatch status</code> — Live-Status des Agents</li>
<li><code>agentwatch traces</code> — Trace-Export und -Analyse</li>
<li><code>agentwatch cost</code> — Kostenübersicht</li>
</ul>
<p><strong>Build:</strong> dist/agentwatch-0.1.0-py3-none-any.whl, 4 Tests, 100% Coverage.</p>

<h2>10. Deployment &amp; Infrastruktur</h2>
<h3>10.1 Infrastruktur</h3>
<table class="table">
<tr><th>Komponente</th><th>Spezifikation</th></tr>
<tr><td>GPU</td><td>NVIDIA B200 (150.136.33.155)</td></tr>
<tr><td>Memory</td><td>183GB</td></tr>
<tr><td>Backend</td><td>FastAPI + PostgreSQL + Redis</td></tr>
<tr><td>Frontend</td><td>React + Vite + TypeScript (localhost:5173)</td></tr>
<tr><td>API</td><td>FastAPI (localhost:8001)</td></tr>
<tr><td>Docker</td><td>Full containerized deployment</td></tr>
</table>

<h2>11. Sicherheitskonzept</h2>
<h3>11.1 Security Layers</h3>
<ul>
<li><strong>Secret Redaction:</strong> API Keys, Tokens, Passwörter werden automatisch maskiert</li>
<li><strong>Tirith Pre-Exec Scanning:</strong> Sicherheitsscans vor Code-Ausführung</li>
<li><strong>Tool Loop Guardrails:</strong> Hard stops nach wiederholten Fehlern</li>
<li><strong>Workspace Isolation:</strong> Separate Workspaces mit eigenen Kontexten</li>
</ul>

<h2>12. Performance-Benchmarks</h2>
<h3>12.1 Training Metrics</h3>
<table class="table">
<tr><th>Metric</th><th>v16 (Before)</th><th>v17 (After)</th></tr>
<tr><td>reward_std</td><td>0.0 (Collapse)</td><td>>0.01 (Variance restored)</td></tr>
<tr><td>entropy</td><td>≈0 (Collapse)</td><td>>0.01 (Exploration alive)</td></tr>
<tr><td>KL Divergence</td><td>≈0</td><td>0.01-0.05 (Guardrail)</td></tr>
<tr><td>grad_norm</td><td>≈0</td><td>>0 (Gradients flowing)</td></tr>
</table>

<h2>13. Roadmap &amp; Ausblick</h2>
<h3>13.1 Nächste Meilensteine</h3>
<ul>
<li><strong>Q3 2026:</strong> Multi-Agent-Orchestrierung, AgentWatch v2.0</li>
<li><strong>Q4 2026:</strong> Product Hunt Launch, Micro-SaaS Monetarisierung</li>
<li><strong>Q1 2027:</strong> API-Service, Enterprise-Integration</li>
<li><strong>Q2 2027:</strong> Open-Source Release, Community-Contributions</li>
</ul>
<div class="highlight">
<p><strong>Vision:</strong> MiMi Nox als die erste echte multimodale Agenten-Plattform — Text, Vision, Audio in einem Modell. Keine Fragmentierung. Keine Trade-offs. Nur intelligente Integration.</p>
</div>

<footer>
MiMi Nox Whitepaper v1.0 · Juli 2026 · Confidential
</footer>
</div>
</body>
</html>"""

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"data:text/html,{HTML}")
        await page.pdf(path="/Users/sanji/mimi-nox/docs/whitepaper-mimi-nox.pdf", format="A4", print_background=True, margin={"top":"20mm","right":"20mm","bottom":"20mm","left":"20mm"})
        await browser.close()
    print("✓ Whitepaper PDF generated: /Users/sanji/mimi-nox/docs/whitepaper-mimi-nox.pdf")

if __name__ == "__main__":
    asyncio.run(main())
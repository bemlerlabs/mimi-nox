# MiMiNox v2 — Node.js Preview

> ⚠️ **Dies ist die experimentelle Node.js-Reimplementierung.**
> Für die stabile Version: → [Haupt-README](../README.md)

---

## Was ist v2?

`v2/` ist eine von Grund auf neu geschriebene Version des MiMiNox-Backends in **Node.js / Express**.

Sie enthält das neue **Krisen-Team-Konzept** mit 4 spezialisierten Agenten (Medic, Engineer, Navigator, Sensor), einem eigenen Offline-RAG-System und einem React-Dashboard.

## Status

| Feature | Status |
|---|---|
| Krisen-Orchestrator | ✅ Fertig |
| Offline RAG (TF-IDF) | ✅ Fertig |
| Streaming (SSE) | ✅ Fertig |
| Dashboard (React) | ✅ Fertig |
| Memory-Kommandos | ✅ Fertig |
| Vision / PyAutoGUI | ❌ Nur in v1 |
| 248 Unit Tests | ❌ In Arbeit (vitest) |

## Quick Start (v2)

```bash
cd v2
npm install
npm run dev
```

Öffne `http://localhost:3000`

> **Für alle anderen:** `./install.sh` im Haupt-Verzeichnis ist der richtige Einstieg.

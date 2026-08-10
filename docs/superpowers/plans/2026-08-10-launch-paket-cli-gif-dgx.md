# MiMi Nox Launch-Paket + DGX-Spark-GIFs — Implementierungsplan

> **Für agentic worker:** REQUIRED: super-sdd Skill nutzen, Task-für-Task implementieren.

**Goal:** Launch-fähiges MiMi Nox Paket: CLI/TUI kann OpenAI-kompatible Engines anbinden (DGX-Spark ds4), README wahrheitsgetreu aktualisieren, CLI-Demo-GIF mit DGX-Spark-Modell aufnehmen.
**Architecture:** Engine-URL konfigurierbar machen (statt nur Ollama), OpenAI-kompatible Anfrage an ds4-Server, CLI-Flag `--api-url`/`--engine`, GIF-Aufnahme via asciinema→agg.
**Tech Stack:** Python (Textual TUI), OpenAI-kompatible REST, asciinema 2.4.0, agg 1.9.0, DGX-Spark ds4 v0.5.3.

## Global Constraints
- TUI offline-first: Default bleibt lokale Ollama (gemma4:e4b). DGX-Spark als opt-in Engine.
- `--api-url`/`--model` CLI-Flags; Konfig nicht hard-coded.
- README muss der Wahrheit entsprechen (keine CEO/CTO/Zero-Human-Positionierung — AGENTS.md).
- GIFs: immer `.venv/bin/` Binaries, asciinema 2.x Flags (`-i`, `--overwrite`, `-q`).

## Task 1: Engine-Abstraktion in ui/
**Files:** Modify `ui/provider.py` (oder wo `chat_with_tools` lebt), `ui/app.py:22-26,146-180,387-405`
- [ ] **Step 1:** Failing test: `chat_with_tools(model, api_url=...)` sendet an `api_url/v1/chat/completions` statt `11434`.
- [ ] **Step 2:** Run — confirm FAIL.
- [ ] **Step 3:** Implement: `check_ollama_connection` → `check_engine_connection(api_url, model)`; `chat_with_tools` akzeptiert `api_url` (Default `http://127.0.0.1:11434`). OpenAI-kompatibel für ds4.
- [ ] **Step 4:** Run — PASS.
- [ ] **Step 5:** Full pytest — grün.
- [ ] **Step 6:** Commit: `feat(ui): engine-agnostic chat (api_url konfigurierbar)`.

## Task 2: CLI-Flags `--api-url` + `--model`
**Files:** Modify `ui/app.py` (ArgumentParser), `miminox` CLI-Einstieg
- [ ] **Step 1:** Test: `--api-url` wird an Provider durchgereicht.
- [ ] **Step 2:** Run — FAIL.
- [ ] **Step 3:** Implement Flags; Default Ollama.
- [ ] **Step 4/5:** Tests + Full suite grün.
- [ ] **Step 6:** Commit: `feat(cli): --api-url/--model flags`.

## Task 3: GIF-Aufnahme mit DGX-Spark
**Files:** Modify `scripts/record-cli-gif.sh` (API-URL + Modell aus env `MIMINOX_API_URL`)
- [ ] **Step 1:** Env-Vars `MIMINOX_API_URL=http://spark-2c73...:8000/v1`, `MIMINOX_MODEL=deepseek-v4-flash` ins Skript.
- [ ] **Step 2:** CLI mit Flags starten; TUI läuft gegen DGX-Spark.
- [ ] **Step 3:** asciinema `-i 2` aufnehmen, agg konvertieren.
- [ ] **Step 4:** GIF validieren (GIF89a) + visuell prüfen (TUI-Demo sichtbar).
- [ ] **Step 5:** Commit: `feat(media): CLI demo GIF (DGX-Spark)`.

## Task 4: README wahrheitsgetreu aktualisieren
**Files:** Modify `README.md`
- [ ] **Step 1:** Engine-Sektion: Ollama Default, OpenAI-kompatible Engines (DGX-Spark ds4) opt-in, Flags dokumentieren.
- [ ] **Step 2:** GIF einbetten; Launch-Status.
- [ ] **Step 3:** Keine CEO/CTO/Zero-Human-Positionierung.
- [ ] **Step 4:** Commit: `docs(readme): engine config + CLI demo GIF`.

## Task 5: Launch-Paket
**Files:** Release-Check (pytest grün, GIF, README, git log sauber)
- [ ] **Step 1:** `pytest` voll grün.
- [ ] **Step 2:** `git status` sauber, alle Commits gepusht.
- [ ] **Step 3:** Zusammenfassung + nächste Launch-Schritte.

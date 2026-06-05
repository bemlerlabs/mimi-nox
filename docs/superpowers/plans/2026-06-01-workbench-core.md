# MiMi Nox Workbench Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable long-chat context, Mac project discovery/analysis, and higher-quality generated reports to the current Root PWA.

**Architecture:** Keep the UI stable and extend the existing tool-calling architecture. Add focused backend modules for project discovery and conversation compaction, expose them through normal tools, and wire a `/project` built-in skill to those tools.

**Tech Stack:** Python 3.12, FastAPI, Ollama tool calling, reportlab, pytest, Playwright smoke checks.

---

### Task 1: Project Discovery And Analysis

**Files:**
- Create: `core/project_discovery.py`
- Modify: `core/tools.py`
- Create: `skills/project-assistant.md`
- Test: `tests/test_project_discovery.py`

- [ ] Write tests for discovering code projects in allowed roots, recognizing stacks, and producing an actionable status report.
- [ ] Implement project scoring from marker files such as `.git`, `pyproject.toml`, `package.json`, `README.md`, `Dockerfile`, and test directories.
- [ ] Expose `discover_projects` and `analyze_project` tools in `TOOL_MAP` and `get_tool_schemas()`.
- [ ] Add `/project` skill with tool scope `discover_projects, analyze_project, read_file, list_directory, file_search`.

### Task 2: Long Conversation Compaction

**Files:**
- Create: `core/conversation_compactor.py`
- Modify: `core/chat.py`
- Test: `tests/test_conversation_compactor.py`

- [ ] Write tests showing long history is compacted into a stable system context while recent turns remain intact.
- [ ] Implement deterministic extractive compaction with project facts, decisions, open tasks, and recent summary.
- [ ] Inject compaction before model calls when history exceeds configured length.

### Task 3: High-End Report Output

**Files:**
- Modify: `core/tools.py`
- Test: `tests/test_pdf_reading.py`

- [ ] Write tests that generated PDFs include clean metadata, section hierarchy, bullets, and extractable text.
- [ ] Improve `create_pdf()` layout with cover metadata, footer page numbers, stronger section styling, and safe filename handling.
- [ ] Keep output local in `~/Downloads` and preserve the existing `PDF_FILE:` contract.

### Task 4: Verification

**Files:**
- Existing tests and Root PWA.

- [ ] Run focused tests for new modules.
- [ ] Run full `pytest -q`.
- [ ] Run syntax/compile checks.
- [ ] Start Root PWA on `127.0.0.1:9876` and run a browser smoke for health, skills, and console errors.

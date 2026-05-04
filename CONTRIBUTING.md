# Contributing to MiMi Nox

Thank you for your interest in contributing! MiMi Nox is built by [MiMi Tech AI UG](https://mimiai.de) — external contributions are welcome as long as they align with our core principles:

> **Private. Local. Zero Cloud.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/MimiTechAi/mimi-nox.git
cd mimi-nox
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,voice]"
playwright install chromium   # for headless browser tests
```

---

## 📏 Coding Standards

| Area | Standard |
|------|----------|
| **Python** | PEP 8, type hints everywhere, `async/await` consistently |
| **JavaScript** | ES2022+, ES Modules (`import/export`), no framework, no bundler |
| **CSS** | Custom Properties (`var(--green)` etc.), no Tailwind, no SCSS |
| **Tests** | TDD — write tests first, BDD notation (Given-When-Then) |
| **Commits** | [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`) |

---

## 🧪 Running Tests

```bash
# All tests
pytest tests/ -v

# Single module
pytest tests/test_artifact_detector.py -v

# Without integration tests (no Ollama needed)
pytest tests/ -v -m "not integration"
```

> **Rule:** New features **must** include tests. No tests → no merge.

---

## 🛠 Adding Features

### New Tool

1. Implement the function in `core/tools.py` (async, type-annotated)
2. Register it in the `TOOLS` list
3. Write tests in `tests/test_tools.py`

### New API Endpoint

1. Create route in `server/routes/<name>.py`
2. Register in `server/main.py`
3. Add tests in `tests/test_api.py`
4. Update README API reference

### New Skill

Simply add a Markdown file to `skills/` — no Python required.

---

## 🎯 Project Principles

| ✅ Do | ❌ Don't |
|-------|---------|
| Local execution, zero cloud dependencies | Add mandatory API keys |
| Privacy by design | Add external analytics/telemetry |
| Async everywhere (no blocking calls in main thread) | Use React/Vue/Angular in frontend |
| Support all platforms (macOS, Linux, Windows) | Break cross-platform compatibility |

---

## 📋 Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests (Given-When-Then)
4. Commit with Conventional Commits
5. Ensure all tests pass (`pytest tests/ -v`)
6. Open a Pull Request using our PR template

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

*MiMi Tech AI UG — Bad Liebenzell, Black Forest, Germany 🌲*

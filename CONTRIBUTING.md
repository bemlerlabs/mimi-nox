# Contributing to MiMi Nox

Thank you for your interest in contributing! MiMi Nox is built by [MiMi Tech AI UG](https://mimiai.de) — external contributions are welcome as long as they align with our core principles:

> **Offline-first by default. Online integrations only by explicit opt-in.**

---

## 🚀 Quick Start

```bash
git clone https://github.com/bemlerlabs/mimi-nox.git
cd mimi-nox
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Frontend (PWA):

```bash
cd app
npm ci
npm run dev      # Vite dev server
```

---

## 📏 Coding Standards

| Area | Standard |
|------|----------|
| **Python** | PEP 8, type hints everywhere, `async/await` consistently |
| **JavaScript/TypeScript** | ES2022+, TypeScript strict mode (PWA in `app/`) |
| **CSS** | Custom Properties (`var(--green)` etc.), no Tailwind, no SCSS |
| **Commits** | [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`) |

---

## 🧪 Validation

The public repository ships the **CI quality gates** — every push and pull request runs:

- **Integration checks** (`tests.yml`): package import integrity, installer syntax
  (bash + PowerShell), security-default audit (conservative server binding),
  Docker image build
- **Frontend build** (`frontend-build.yml`): TypeScript type check, Vite production
  build, ESLint

Before opening a PR, verify locally:

```bash
# Backend: import integrity
python -c "import miminox; import miminox_cli; print('OK')"

# Installers: syntax
bash -n install.sh

# Frontend: type check + build
cd app && npx tsc --noEmit && npm run build
```

> **Note:** The Python test suite is maintained privately (maintainer-only) and is
> not part of the public repository. CI enforces the quality gates above. If you are
> a maintainer, run the full suite locally before release.

---

## 🛠 Adding Features

### New Tool

1. Implement the function in `core/tools.py` (async, type-annotated)
2. Register it in the `TOOLS` list
3. Update the README tool reference

### New API Endpoint

1. Create route in `server/routes/<name>.py`
2. Register in `server/main.py`
3. Update README API reference

### New Skill

Simply add a Markdown file to `skills/` — no Python required.

---

## 🎯 Project Principles

| ✅ Do | ❌ Don't |
|-------|---------|
| Local execution and offline-first defaults | Add mandatory API keys |
| Privacy by design | Add external analytics/telemetry |
| Async everywhere (no blocking calls in main thread) | Break cross-platform compatibility |
| Keep server binding conservative (127.0.0.1 default) | Bind to 0.0.0.0 without explicit opt-in |

---

## 📋 Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Run the local validation commands above
4. Commit with Conventional Commits
5. Open a Pull Request using our PR template

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

*MiMi Tech AI UG — Black Forest, Germany 🌲*

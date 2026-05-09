# MiMi Nox Agent Instructions

## Product Positioning

- Treat the root PWA as the main product.
- Keep MiMi Nox offline-first by default: local Ollama, `gemma4:e4b`, no account requirement.
- Mark custom Ollama, public mobile access, web search, TTS APIs, and OpenAI-compatible APIs as optional opt-in paths.
- Do not reintroduce company/CEO/CTO/crisis-team/Zero Human positioning into public README or UI.

## Engineering Workflow

- Start with `git status --short` and inspect relevant existing code before editing.
- Prefer WGT/TDD: add or update tests for security, installer, provider, UI, and repo hygiene behavior before or with changes.
- Keep edits focused and avoid reverting unrelated local changes.
- Use `rg` for search and run the narrowest relevant tests before broad validation.

## Release Bar

- One-command install is a first-class product surface.
- Root-PWA changes need desktop/mobile visual checks.
- Security defaults must keep server binding, CORS, mobile pairing, and tool approval conservative.
- Git must not track `node_modules`, local databases, WAL/SHM files, secrets, caches, or generated local artifacts.

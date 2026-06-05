# MiMi Nox Vision 2026

This document tracks the current product direction for MiMi Nox.

## Positioning

MiMi Nox is an offline-first local AI assistant. The root PWA is the main product surface. The default model path is local Ollama with `gemma4:12b`.

Optional online paths are allowed only when they are visible and user-controlled:

- web research
- public mobile access
- external text-to-speech services
- OpenAI-compatible APIs
- custom remote model endpoints

## Product Principles

| Principle | Requirement |
|---|---|
| Local first | Fresh setup defaults to `local_ollama` |
| Honest copy | No absolute offline claims for optional online features |
| Repairable setup | Missing Ollama or missing model states produce clear commands |
| Mobile trust | QR pairing is LAN-first; public mode is explicit opt-in |
| Approval gates | Shell, screenshot, and GUI actions require confirmation |
| Testable UI | Desktop, tablet, and mobile flows need Playwright coverage |

## Near-Term Roadmap

1. Keep the one-command installer reliable across macOS and Linux.
2. Improve `miminox doctor` until it explains every common failed-start state.
3. Keep README and in-app onboarding aligned around offline-first setup.
4. Expand visual QA for desktop, tablet, and mobile.
5. Keep provider routing centralized so chat, vision, files, and skills do not create separate clients.
6. Keep v2 work clearly marked as experimental until it matches the root PWA release bar.

## Release Bar

Before a public release candidate:

- `install.sh` syntax check passes.
- Installer and CLI tests pass.
- Offline positioning tests pass.
- Security default tests pass.
- QR and mobile visual tests pass.
- README media is regenerated and referenced files exist.
- Repo hygiene tests confirm no dependency folders, local DBs, secrets, or generated frame files are tracked.

# MiMi Nox TDD Backlog

This backlog keeps the root PWA release path test-driven.

## Current Release Scope

- Offline-first desktop PWA.
- LAN-first mobile PWA via QR code.
- Local Ollama provider with `gemma4:e4b`.
- Optional online features only after visible opt-in.
- Approval-gated shell, screenshot, and GUI actions.

## WGT Scenarios

### Installer

GIVEN a fresh checkout on macOS or Linux
WHEN the user runs the documented install command
THEN MiMi Nox installs into the expected folder, checks Ollama, checks `gemma4:e4b`, starts the server, and prints one local URL.

### Missing Model

GIVEN Ollama is running but `gemma4:e4b` is missing
WHEN the user starts chat
THEN the UI explains the missing model and shows `miminox doctor` plus `miminox start`.

### Online Opt-In

GIVEN the user selects `/research`
WHEN the user presses send
THEN the desktop and mobile UI show an online warning before sending a request.

### Mobile QR

GIVEN the user opens mobile pairing
WHEN the QR code is generated without public mode
THEN the URL is LAN scoped and `requires_internet` is false.

### Approval-Gated Tools

GIVEN a tool can modify the system or interact with the screen
WHEN no approval exists
THEN the backend blocks execution and the UI shows an approval step.

### README Trust

GIVEN a GitHub visitor reads the repository
WHEN README, contribution docs, and security docs are scanned
THEN claims are factual, demo media exists, online features are labeled, and stale test counts are not hard-coded.

## Focused Test Commands

```bash
pytest tests/test_installer_cli.py -q
pytest tests/test_offline_first_positioning.py tests/test_repo_hygiene.py -q
pytest tests/test_model_provider.py tests/test_security_offline_defaults.py tests/test_offline_qr.py -q
pytest tests/test_pwa_visual.py -q
bash -n install.sh
```

## Done Criteria

- Tests are added before or with implementation.
- Public copy matches actual behavior.
- UI changes have desktop and mobile visual checks.
- Generated README media is reproducible with `python scripts/create_demo_media.py`.
- No local artifacts, generated frames, caches, dependency folders, or local databases are tracked.

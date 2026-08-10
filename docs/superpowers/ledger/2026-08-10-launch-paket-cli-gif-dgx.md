# Ledger — Launch-Paket + DGX-Spark-GIFs

Session: 20260810_191738_35ab85 (Fortsetzung)
Datum: 2026-08-10
Rollen: backend-developer, terminal-integration-specialist, devops-automator, document-generator

## Ziel
Launch-fähiges MiMi Nox: CLI/TUI bindet OpenAI-kompatible Engines an (DGX-Spark ds4),
README wahrheitsgetreu, CLI-Demo-GIF mit DGX-Spark-Modell.

## Tasks
1. Engine-Abstraktion in core + ui (build_engine_provider, _resolve_provider, check_engine_connection, api_url-Durchreichung)
2. CLI-Flags --api-url + --model
3. GIF-Aufnahme mit DGX-Spark (env MIMINOX_API_URL / MIMINOX_MODEL)
4. README wahrheitsgetreu (Engine-Sektion, GIF, Launch-Status)
5. Launch-Paket (pytest grün, git sauber, Commits gepusht)

## Fortschritt (Task 1 — abgeschlossen)
- core/model_provider.py: api_key optional, `requires_api_key` Feld (Engine=False), `build_engine_provider`, `ensure_provider_ready` nur bei requires_api_key.
- core/chat.py: `_resolve_provider`, `check_engine_connection`, Signaturen um api_url erweitert.
- core/react.py: reflect + react_loop + chat_with_tools/reflect-Calls reichen api_url durch.
- ui/app.py: __init__(api_url), _async_check_connection (engine vs ollama), react_loop api_url.
- tests/test_model_provider.py: 3 neue TDD-Tests (build_engine_provider, check_engine_connection reachable/offline).
- pytest: 16 passed.

## Entscheidungen
- api_url: str | None = None; None → aktive Ollama-Config; != DEFAULT_OLLAMA_BASE_URL → OpenAI-kompatible Engine.
- Remote-Engine kann keine Modelle lokal listen → available_models leer, Status "connected".
- OpenAICompatibleAsyncClient.api_key optional (lokale Engine ohne Auth); `requires_api_key=False` für Engine-Configs, damit ensure_provider_ready nicht blockt.
- GIF: .venv/bin/ Binaries, asciinema 2.x Flags (-i, --overwrite, -q), agg Konvertierung, GIF89a-Validierung.

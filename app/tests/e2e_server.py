#!/usr/bin/env python3
"""E2E Test-Server: MiMi Nox FastAPI-Server mit isoliertem, deterministischem Config.

Startet den ECHTEN FastAPI-Server (uvicorn) auf 127.0.0.1:8765 mit:
- Frischem, leerem Config-Dir unter <repo>/.e2e-runtime/config
  (keine engine.json → configured=false → Setup-Page-Flow ist testbar)
- PWA-Build aus app/dist (muss vorher `npm run build` existieren)
- Isolierten Audio/Image-Dirs (keine Überschreibung der User-Daten)

Deterministischer Pfad (nicht tempfile.gettempdir()): Das Config-Dir liegt
unter <repo>/.e2e-runtime/ — so können Server (via __file__) und der
Playwright-Spec (via __dirname) denselben Pfad berechnen und der Test kann
die persistierte engine.json direkt lesen.

Kein Mock, kein Stub — produktionsgleicher Server, nur isoliertes Config.

Start:  .venv/bin/python app/tests/e2e_server.py   (von Repo-Root)
Stop:   kill $PID (oder Playwright webServer-Teardown)
"""
import os
import shutil
import sys
from pathlib import Path

# ── Pfade (deterministisch, unter Repo-Root) ───────────────────────────────
# File liegt bei: <repo>/app/tests/e2e_server.py
project_root = Path(__file__).resolve().parent.parent.parent
runtime_dir = project_root / ".e2e-runtime"
config_dir = runtime_dir / "config"
data_dir = runtime_dir / "data"

# Frisches, leeres Config-Dir → load_engine_config() → None → configured=false.
# (Re-Cleanup: ein alter engine.json aus einem vorherigen Lauf würde den
# First-Run-Flow überspringen lassen.)
for d in (runtime_dir, config_dir, data_dir):
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
(data_dir / "audio").mkdir(parents=True, exist_ok=True)
(data_dir / "images").mkdir(parents=True, exist_ok=True)

# ── Env-Vars für den Server-Start ──────────────────────────────────────────
os.environ["MIMI_NOX_CONFIG_DIR"] = str(config_dir)
os.environ["MIMI_NOX_FRONTEND_DIR"] = str(project_root / "app" / "dist")
os.environ["MIMI_NOX_AUDIO_DIR"] = str(data_dir / "audio")
os.environ["MIMI_NOX_IMAGE_DIR"] = str(data_dir / "images")

# ── Server-Start ────────────────────────────────────────────────────────────
sys.path.insert(0, str(project_root))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    print(f"[e2e] config_dir={config_dir}", flush=True)
    print(f"[e2e] frontend={os.environ['MIMI_NOX_FRONTEND_DIR']}", flush=True)
    print("[e2e] server starting on 127.0.0.1:8765 ...", flush=True)
    uvicorn.run(
        "server.main:app",
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )

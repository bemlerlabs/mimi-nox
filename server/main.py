"""
◑ MiMi Nox – FastAPI Server
server/main.py

Startet den API-Server für die Desktop App.
Pfade für Memory/Profile/etc. werden über Env-Variablen konfiguriert
damit Tests isolierte tmp-Verzeichnisse nutzen können.

LAN Mode: Wenn --lan aktiv, wird ein Auth-Token generiert und alle
API-Endpunkte müssen X-Auth-Token im Header mitsenden.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.observability import (
    REQUEST_ID_HEADER,
    ErrorCode,
    error_payload,
    make_observability_middleware,
)

from server.routes import (
    audio,
    chat,
    export,
    feedback,
    health,
    memory,
    mobile,
    model_provider,
    profile,
    schedule,
    settings,
    skills,
    tasks,
    vision,
)
from core import __version__, __edition__, __tagline__
from contextlib import asynccontextmanager
import asyncio

@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Lifecycle events: Start background warmup tasks."""
    # Warmup STT Model in background to prevent lag on first request
    def warmup_whisper():
        try:
            from core.transcribe import _get_model
            _get_model()
        except Exception:
            pass
            
    asyncio.create_task(asyncio.to_thread(warmup_whisper))

    # --- GUI Automation Safety Setup ---
    def configure_gui_safety():
        import sys
        import logging
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            if sys.platform == "darwin":
                logging.getLogger("uvicorn.error").warning(
                    "⚡ [GUI Automation] Ensure MiMi Nox (Terminal/App) has 'Accessibility' "
                    "and 'Screen Recording' permissions in macOS System Settings > Privacy & Security, "
                    "otherwise vision_click tools will crash immediately."
                )
        except Exception:
            pass

    asyncio.create_task(asyncio.to_thread(configure_gui_safety))

    # --- Background Scheduler ---
    def start_scheduler():
        try:
            from core.scheduler import nox_scheduler
            nox_scheduler.start()
        except Exception:
            pass

    asyncio.create_task(asyncio.to_thread(start_scheduler))

    yield

    try:
        from core.scheduler import nox_scheduler
        nox_scheduler.stop()
    except Exception:
        pass

def create_app(lan_mode: bool = False) -> FastAPI:
    """
    FastAPI App Factory.
    Genutzt in Tests (TestClient) und in run.py (uvicorn).

    lan_mode: Wenn True, wird Auth-Token generiert + Security/Rate-Limit aktiviert.
    """
    # ── Auth initialisieren (generiert Token bei LAN Mode) ──────────────
    from server.middleware import init_auth, SecurityHeadersMiddleware, RateLimitMiddleware, AuthMiddleware
    init_auth(lan_mode=lan_mode)

    app = FastAPI(
        title=f"{__edition__} MiMi Nox API",
        description=__tagline__,
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
    )

    # ── Security Middleware ─────────────────────────────────────────────────
    app.add_middleware(SecurityHeadersMiddleware)
    if lan_mode:
        app.add_middleware(AuthMiddleware)
        app.add_middleware(RateLimitMiddleware, max_requests=60, window=60)

    # ── CORS für lokale WebView/Dev-Origins ────────────────────────────────
    # LAN/mobile nutzt same-origin über die vom Server gelieferte PWA. Fremde
    # Webseiten bekommen keine Schreibrechte auf die lokalen APIs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["tauri://localhost"],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Observability (Phase 4 Item 15): Request-ID + strukturierte Logs ──
    # Zuletzt add_middleware ⇒ outermost: request.state.rid ist für alle
    # inneren Middlewares (Auth 401, RateLimit) + Handler gesetzt.
    app.middleware("http")(make_observability_middleware(prefix="api"))

    # Registrierung am Starlette-Base: FastAPI's eigener HTTPException
    # (Subclass) löst über MRO denselben Handler auf, und Router-404/405
    # (echte Starlette-HTTPException) werden damit ebenfalls erwischt.
    async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Starlette/FastAPI HTTPException tragen status_code + detail;
        # getattr hält den Handler für beide Klassen typsicher.
        rid = getattr(request.state, "rid", None)
        detail = getattr(exc, "detail", None)
        message = detail if isinstance(detail, str) else str(detail or "Error")
        status_code = int(getattr(exc, "status_code", 500))
        if status_code == 401:
            code_id = ErrorCode.AUTH
        elif status_code in (404, 405):
            code_id = ErrorCode.NOT_FOUND
        elif status_code in (400, 422):
            code_id = ErrorCode.VALIDATION
        elif status_code == 429:
            code_id = ErrorCode.USAGE
        elif status_code in (502, 503):
            code_id = ErrorCode.UPSTREAM
        else:
            code_id = ErrorCode.INTERNAL
        return JSONResponse(
            error_payload(code_id, message, rid),
            status_code=status_code,
            headers={REQUEST_ID_HEADER: rid or ""},
        )

    # Starlette-Base (Router-404/405) + FastAPI-Subclass (raised in Routen)
    # — MRO-Lookup der Exception-Middleware ist klassenexakt, daher beide.
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)

    # ── API Routen ─────────────────────────────────────────────────────────
    app.include_router(health.router,   prefix="/api")
    app.include_router(chat.router,     prefix="/api")
    app.include_router(memory.router,   prefix="/api")
    app.include_router(skills.router,   prefix="/api")
    app.include_router(profile.router,  prefix="/api")
    app.include_router(feedback.router, prefix="/api")
    app.include_router(audio.router,    prefix="/api")
    app.include_router(mobile.router,   prefix="/api")
    app.include_router(schedule.router,   prefix="/api")
    app.include_router(settings.router,   prefix="/api")
    app.include_router(vision.router,   prefix="/api")
    app.include_router(tasks.router,    prefix="/api")
    app.include_router(export.router,   prefix="/api")
    app.include_router(model_provider.router, prefix="/api")

    # ── Statische Dateien (Audio-Aufnahmen für Playback) ───────────────────
    audio_dir = Path(
        os.environ.get("MIMI_NOX_AUDIO_DIR",
                       str(Path.home() / ".mimi-nox" / "sessions" / "audio"))
    )
    audio_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")

    # ── Statische Dateien (Bilder/Screenshots für Remote) ──────────────────
    image_dir = Path(
        os.environ.get("MIMI_NOX_IMAGE_DIR",
                       str(Path.home() / ".mimi-nox" / "sessions" / "images"))
    )
    image_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/images", StaticFiles(directory=str(image_dir)), name="images")

    # ── Statische Dateien (Charts aus /tmp) ───────────────────────────────
    import tempfile
    app.mount("/charts", StaticFiles(directory=tempfile.gettempdir()), name="charts")

    # ── Statische Dateien (Web-Frontend / PWA) ──────────────────────────────
    mount_frontend(app)

    return app


# ── Frontend (PWA) Auflösung ─────────────────────────────────────────────────
# Der PWA-Build liegt in app/dist (git-ignoriertes Build-Artefakt). app/src ist
# nur die Vite-Quelle (kein index.html) — ein Mount darauf lieferte Silent-404.
# MIMI_NOX_FRONTEND_DIR erlaubt Tests/CI, ein isoliertes Build-Verzeichnis
# einzuhängen, ohne den Produktionspfad zu überschreiben.
def resolve_frontend_dir() -> Path:
    override = os.environ.get("MIMI_NOX_FRONTEND_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parent.parent / "app" / "dist"


def _frontend_missing_hint() -> HTMLResponse:
    """Root-Fallback, wenn der PWA-Build fehlt: Reparatur-Anleitung statt 404."""
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MiMi Nox — PWA-Setup</title>
<style>body{font-family:system-ui,sans-serif;max-width:40rem;margin:4rem auto;
line-height:1.6;color:#111}code{background:#f2f2f2;padding:.1rem .4rem;
border-radius:4px}pre{background:#111;color:#eee;padding:1rem;border-radius:8px;
overflow:auto}</style></head>
<body><h1>◑ MiMi Nox — PWA wird vorbereitet</h1>
<p>Die Web-App (PWA) wurde noch nicht gebaut. Der API-Server läuft bereits —
nur das Frontend fehlt noch. So baust du die PWA lokal:</p>
<pre>cd app
npm install
npm run build</pre>
<p>…und danach einfach diese Seite neu laden. Alternativ startet der
One-Command-Installer den Build für dich.</p>
<p>API-Endpunkte sind bereits erreichbar: <a href="/api/health">/api/health</a>
· <a href="/api/docs">/api/docs</a></p>
</body></html>""",
        status_code=200,
    )


def mount_frontend(app: FastAPI) -> None:
    """PWA unter `/` ausliefern.

    - Build vorhanden  → StaticFiles(html=True) (index.html + Assets)
    - Build fehlt      → Root zeigt die Build-Anleitung (200, kein 404)
    """
    frontend_dir = resolve_frontend_dir()
    if (frontend_dir / "index.html").is_file():
        app.mount(
            "/", StaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )
    else:
        @app.get("/", include_in_schema=False)
        async def _root_missing_build() -> HTMLResponse:
            return _frontend_missing_hint()


# Standalone-Instanz (für uvicorn direkt)
def get_app() -> FastAPI:
    """Erzeugt App mit LAN-Mode aus Umgebungsvariable."""
    lan = os.environ.get("MIMI_NOX_LAN", "0") == "1"
    return create_app(lan_mode=lan)


app = get_app()

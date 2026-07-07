#!/usr/bin/env python3
"""
◑ MiMi Nox – Server starten
run_server.py

Startet den FastAPI Server auf Port 8765.
Verwendung:
    python run_server.py             # Standard
    python run_server.py --port 9000 # Anderer Port
    python run_server.py --reload    # Dev-Modus mit Auto-Reload
"""
import argparse
import os
import sys
from pathlib import Path

# Sicherstellen dass das MiMi-Nox-Verzeichnis im Pfad ist
sys.path.insert(0, str(Path(__file__).parent))

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="◑ MiMi Nox API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    parser.add_argument("--port", default=8765, type=int, help="Port (default: 8765)")
    parser.add_argument("--lan", action="store_true", help="Expose on the local network for QR mobile pairing")
    parser.add_argument("--reload", action="store_true", help="Auto-Reload im Dev-Modus")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.lan:
        args.host = "0.0.0.0"
        os.environ["MIMI_NOX_LAN"] = "1"
    os.environ["MIMI_NOX_HOST"] = args.host
    os.environ["MIMI_NOX_PORT"] = str(args.port)

    print(f"\n  ◑ MiMi Nox API Server")
    print(f"  ─────────────────────────────────────")
    print(f"  URL:    http://{args.host}:{args.port}")
    if args.host == "0.0.0.0":
        print(f"  LAN:    scan the in-app QR code from a phone on the same Wi-Fi")
    print(f"  Docs:   http://{args.host}:{args.port}/api/docs")
    print(f"  Reload: {'aktiviert' if args.reload else 'deaktiviert'}")
    print(f"  ─────────────────────────────────────\n")

    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()

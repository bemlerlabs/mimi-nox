"""
◑ MiMi Nox – by MiMi Tech AI UG
Bad Liebenzell · Schwarzwald · Germany

Privat. Lokal. Yours.

Entry Point: mimi-nox [--model MODEL] [--reset]
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mimi-nox",
        description=(
            "◑ MiMi Nox – Local AI Assistant\n"
            "   Privat. Lokal. Yours.\n"
            "   MiMi Tech AI UG · Bad Liebenzell, Schwarzwald\n\n"
            "Slash commands:  /post  /debug  /idea  /explain  /commit\n"
            "Swarm agents:    /swarm <task>  (multi-agent parallel pipeline)\n"
            "Keyboard:        Ctrl+R=Reset  Ctrl+L=Clear  ↑↓=History  q=Quit"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  mimi-nox\n"
            "  mimi-nox --model gemma4:12b\n"
            "  mimi-nox --model llama3.1\n"
            "  mimi-nox --reset\n\n"
            "No cloud. No tracking. ◑ Open Source · github.com/bemlerlabs/mimi-nox"
        ),
    )
    parser.add_argument(
        "--model",
        default="gemma4:12b",
        metavar="MODEL",
        help="Ollama model name (default: gemma4:12b). "
             "Also great: phi4-mini, llama3.1, mistral",
    )
    parser.add_argument(
        "--api-url",
        default=None,
        metavar="URL",
        help="OpenAI-compatible engine base URL (e.g. DGX-Spark ds4 "
             "http://spark-...:8000/v1). Default: local Ollama.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear previous session on start",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="◑ MiMi Nox v1.0.0 – by MiMi Tech AI UG",
    )

    args = parser.parse_args()

    try:
        from ui.app import MiMiNoxApp
    except ImportError as e:
        print(f"[Error] Failed to import MiMi Nox: {e}", file=sys.stderr)
        print("Run: ./install.sh  or  pip install -e '.'", file=sys.stderr)
        sys.exit(1)

    app = MiMiNoxApp(model=args.model, reset=args.reset, api_url=args.api_url)
    app.run()


if __name__ == "__main__":
    main()

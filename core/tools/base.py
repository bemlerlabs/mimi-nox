"""MiMi Nox – Base exceptions, helpers, and constants for tool modules."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


# Module-level shared Ollama client (reuse TCP connection)
_shared_client: Any | None = None
TOOL_SCHEMA_CACHE_TTL_SECONDS = 60.0
_TOOL_SCHEMA_CACHE: tuple[float, list[dict]] | None = None


def _get_shared_client() -> Any:
    """Lazy-initialized shared AsyncClient. Reuses TCP connection across calls.

    `ollama` wird hier (nicht modul-global) importiert: das Paket muss
    offline-first importierbar bleiben (offline-first Positioning, AGENTS.md),
    auch wenn der Ollama-Client/Modul in der aktuellen Umgebung fehlt.
    """
    global _shared_client
    if _shared_client is None:
        import ollama
        _shared_client = ollama.AsyncClient()
    return _shared_client


# ── Custom Exceptions ────────────────────────────────────────────────────────

class WebSearchError(Exception):
    """DuckDuckGo nicht erreichbar oder anderer Suchfehler."""


class FileNotAllowedError(PermissionError):
    """Pfad ist nicht in der erlaubten Whitelist."""
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Zugriff verweigert: '{path}' ist nicht in den erlaubten Verzeichnissen.\n"
            f"Erlaubt: HOME, Desktop, Documents, Downloads, tmp"
        )


class DirectoryNotFoundError(FileNotFoundError):
    """Verzeichnis existiert nicht."""
    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Verzeichnis nicht gefunden: '{path}'")


class ShellConfirmationRequired(Exception):
    """
    Wird von run_shell() geworfen.
    Signalisiert der App: "User muss bestätigen bevor ausgeführt wird."
    """
    def __init__(self, command: str) -> None:
        self.command = command
        super().__init__(f"Bestätigung erforderlich für: {command}")


class SandboxConfirmationRequired(Exception):
    """
    Wird von vision_* Tools geworfen wenn Sandbox-Modus an ist.
    Signalisiert dem Frontend (Web-UI/TUI): "Zeige Freigabe-Dialog".
    """
    def __init__(self, tool_name: str, args: dict) -> None:
        self.tool_name = tool_name
        self.args = args
        super().__init__(f"Sandbox Bestätigung erforderlich für: {tool_name}")


class ShellTimeoutError(TimeoutError):
    """Befehl hat das Timeout überschritten."""
    def __init__(self, command: str, timeout: int) -> None:
        self.command = command
        self.timeout = timeout
        super().__init__(f"Befehl '{command}' timed out nach {timeout}s")


# ── Shell Security Constants ─────────────────────────────────────────────────

SHELL_TIMEOUT_SECONDS = 30

ALLOWED_COMMANDS: set[str] = {
    "ls", "echo", "cat", "head", "tail", "wc", "pwd", "whoami", "uname",
    "python", "python3", "node", "npm", "pip", "pip3",
    "git", "docker", "docker-compose",
    "mkdir", "cp", "mv", "touch", "chmod",
    "curl", "wget",
    "date", "cal", "df", "du", "find", "grep", "sort", "cut", "tr",
    "ps", "top", "kill",
    "make", "cmake",
    "which", "type", "file", "stat",
    "open", "code", "vim", "nano",
}

BLOCKED_PATTERNS: list[str] = [
    "rm ", "rm -rf", "rmdir", "mkfs", "dd ", "format",
    ":(){ :|:& };:",
    "> /dev/", "> /", "| sh", "| bash", "| zsh",
    "sudo ", "su ", "chown", "passwd",
    "shutdown", "reboot", "halt", "poweroff",
    ">|", ">>/", "2>/dev/",
]

ALLOWED_ROOTS: list[Path] = [
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
    Path.home() / ".mimi-nox",
    Path.cwd(),
]

# ── File / Workspace Limits ──────────────────────────────────────────────────

MAX_FILE_CHARS = 100_000
MAX_WORKSPACE_CHARS = 200_000
MAX_WORKSPACE_DEPTH = 3

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# ── Deck Constants ───────────────────────────────────────────────────────────

ENTERPRISE_DECK_PROFILES = {
    "product-platform",
    "engineering-platform",
    "strategy-leadership",
    "gtm-growth",
    "finance-ir",
    "consumer-retail",
}
ENTERPRISE_DESIGN_THEMES = {"evergreen", "executive", "studio"}
AMATEUR_DECK_TERMS = {
    "awesome", "cool", "fun", "cute", "wow", "magic", "game changer",
    "revolutionary", "super", "mega", "kindisch", "lustig", "krass", "geil",
    "amazing", "unicorn",
}


# ── Whitelist Helpers ────────────────────────────────────────────────────────

def _get_allowed_roots() -> list[Path]:
    home = Path.home()
    return [
        home / "Desktop",
        home / "Documents",
        home / "Dokumente",
        home / "Downloads",
        home / "Developer",
        home / "Code",
        home / "Projects",
        home / "Projekte",
        home / "tmp",
        Path("/tmp"),
        Path(os.environ.get("TMPDIR", "/tmp")),
    ]


def _is_path_allowed(path: Path) -> bool:
    resolved = path.resolve()
    for root in _get_allowed_roots():
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False

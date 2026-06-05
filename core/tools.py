"""
◑ MiMi Nox – Tool Engine
core/tools.py

Alle Tool-Funktionen für Tool Calling via Ollama.

Sicherheitsmodell:
  - web_search, file_search, get_datetime:  read-only, immer sicher
  - read_file, list_directory:             nur erlaubte Pfade (Whitelist)
  - run_shell:                             IMMER ShellConfirmationRequired
  - execute_confirmed_shell:               nur nach expliziter Bestätigung

Ollama-Integration:
  get_tool_schemas() → JSON-Schema Liste für ollama.chat(tools=...)

Plattform-Support:
  - macOS:   mdfind (Spotlight) für file_search
  - Linux:   find für file_search
  - Windows: where für file_search (basic)
"""
from __future__ import annotations

import asyncio
import base64
import html
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama
from ddgs import DDGS
from core.project_discovery import analyze_project_path, discover_project_records, format_project_listing
from core.source_notebook import (
    create_source_notebook_index,
    export_source_brief_file,
    format_notebook_created,
    format_notebook_query,
    query_source_notebook_index,
)

# Lazy-import pdfplumber — nur wenn PDF tatsächlich gelesen wird
try:
    import pdfplumber as _pdfplumber
    _PDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    _pdfplumber = None  # type: ignore[assignment]
    _PDF_AVAILABLE = False


# Module-level shared Ollama client (reuse TCP connection)
_shared_client: Any | None = None
TOOL_SCHEMA_CACHE_TTL_SECONDS = 60.0
_TOOL_SCHEMA_CACHE: tuple[float, list[dict]] | None = None

OFFICIAL_SOURCE_DOMAINS = (
    "ai.google.dev",
    "developers.googleblog.com",
    "blog.google",
    "deepmind.google",
    "openai.com",
    "anthropic.com",
    "docs.github.com",
    "github.com",
    "ollama.com",
    "python.org",
)


def _get_shared_client() -> Any:
    """Lazy-initialized shared AsyncClient. Reuses TCP connection across calls."""
    global _shared_client
    if _shared_client is None:
        _shared_client = ollama.AsyncClient()
    return _shared_client


# ===========================================================================
# Custom Exceptions
# ===========================================================================

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


# ===========================================================================
# Whitelist
# ===========================================================================

SHELL_TIMEOUT_SECONDS = 30

MAX_FILE_CHARS = 100_000
MAX_WORKSPACE_CHARS = 200_000
MAX_WORKSPACE_DEPTH = 3

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

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
    "awesome",
    "cool",
    "fun",
    "cute",
    "wow",
    "magic",
    "game changer",
    "revolutionary",
    "super",
    "mega",
    "kindisch",
    "lustig",
    "krass",
    "geil",
    "amazing",
    "unicorn",
}


def _get_allowed_roots() -> list[Path]:
    """Rückgabe der erlaubten Basis-Verzeichnisse (Whitelist).

    SICHERHEIT: `home` selbst ist NICHT erlaubt – nur explizite Unter-
    verzeichnisse. Verhindert Zugriff auf ~/.ssh/, ~/.gnupg/, ~/.env etc.
    """
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
    """Gibt True zurück wenn path innerhalb einer erlaubten Wurzel liegt."""
    resolved = path.resolve()
    for root in _get_allowed_roots():
        try:
            resolved.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


# ===========================================================================
# Tool: web_search
# ===========================================================================

async def web_search(query: str, max_results: int = 5) -> str:
    """
    Sucht im Internet via DuckDuckGo (ddgs).

    Returns:
        Formatierter String mit nummerierten Ergebnissen inkl. URLs.

    Raises:
        ValueError:      leerer Query
        WebSearchError:  Netzwerk nicht erreichbar
    """
    query = query.strip()
    if not query:
        raise ValueError("Query darf nicht leer sein")

    def _search() -> list[dict]:
        with DDGS() as ddgs:
            raw = ddgs.text(query, max_results=max_results)
        return raw or []

    try:
        raw = await asyncio.to_thread(_search)
        if not raw:
            return "Keine Ergebnisse gefunden."

        def _source_quality(url: str) -> tuple[int, str]:
            lowered = (url or "").lower()
            if any(domain in lowered for domain in OFFICIAL_SOURCE_DOMAINS):
                return (0, "official")
            if any(domain in lowered for domain in ("wikipedia.org", "arxiv.org", "huggingface.co")):
                return (1, "reference")
            return (2, "general")

        raw = sorted(
            raw,
            key=lambda result: _source_quality(str(result.get("href", "")))[0],
        )

        # Formatierte Ausgabe damit das Modell die URLs und Quellenqualität sieht.
        formatted_parts = []
        for i, r in enumerate(raw, 1):
            title = r.get("title", "")
            url   = r.get("href", "")
            body  = r.get("body", "")
            _, quality = _source_quality(url)
            formatted_parts.append(
                f"[{i}] {title}\n"
                f"    URL: {url}\n"
                f"    Source quality: {quality}\n"
                f"    {body}"
            )
        return "\n\n".join(formatted_parts)

    except Exception as exc:
        raise WebSearchError(str(exc)) from exc


# ===========================================================================
# Tool: file_search
# ===========================================================================

async def file_search(query: str, path: str | None = None) -> str:
    """
    Durchsucht das Dateisystem nach Dateien (macOS: mdfind, Linux: find).

    Returns:
        Newline-getrennte Liste gefundener Pfade als String

    Raises:
        ValueError: leerer Query
    """
    query = query.strip()
    if not query:
        raise ValueError("Query darf nicht leer sein")

    search_path = path or str(Path.home() / "Desktop")

    # Whitelist prüfen
    if not _is_path_allowed(Path(search_path)):
        return f"Zugriff auf '{search_path}' nicht erlaubt (Sicherheits-Whitelist)."

    def _fallback_search(root: Path, needle: str) -> str:
        matches: list[str] = []
        needle_lower = needle.lower()
        try:
            for current_root, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for filename in files:
                    if needle_lower in filename.lower():
                        matches.append(str(Path(current_root) / filename))
                        if len(matches) >= 100:
                            matches.append("... [Suche auf 100 Ergebnisse gekürzt]")
                            return "\n".join(matches)
        except (PermissionError, OSError):
            pass
        return "\n".join(matches)

    try:
        if sys.platform == "darwin":
            cmd = ["mdfind", "-name", query]
            if path:
                cmd += ["-onlyin", search_path]
        elif sys.platform.startswith("win"):
            cmd = ["where", "/R", search_path, f"*{query}*"]
        else:
            # Linux / andere Unix
            cmd = ["find", search_path, "-iname", f"*{query}*", "-maxdepth", "10"]

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
        )
        output = result.stdout.strip()
        if output:
            lines = output.splitlines()
            if len(lines) > 100:
                lines = lines[:100]
                lines.append("... [Suche auf 100 Ergebnisse gekürzt]")
            output = "\n".join(lines)
        elif sys.platform == "darwin":
            output = await asyncio.to_thread(_fallback_search, Path(search_path), query)
        return output if output else f"Keine Dateien für '{query}' gefunden."

    except subprocess.TimeoutExpired:
        return f"Suche nach '{query}' hat zu lange gedauert."
    except FileNotFoundError:
        # mdfind/find nicht verfügbar
        return f"Dateisuche nicht verfügbar auf diesem System ({sys.platform})."


# ===========================================================================
# Tool: read_file
# ===========================================================================

async def read_file(path: str) -> str:
    """
    Reads a file and returns its text content.
    Supports: plain text, code files, Markdown, and PDF.

    Security: Only files within the whitelist are allowed.
    Large files are truncated to MAX_FILE_CHARS.

    Raises:
        FileNotAllowedError:  Path outside whitelist
        FileNotFoundError:    File does not exist
    """
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: '{resolved}'")

    # ── PDF: extract text via pdfplumber ─────────────────────────────────────
    if resolved.suffix.lower() == ".pdf":
        return _extract_pdf_text(resolved)

    # ── Plain text / code / Markdown ─────────────────────────────────────────
    content = resolved.read_text(encoding="utf-8", errors="replace")

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS]
        content += f"\n\n[File truncated: original had more than {MAX_FILE_CHARS} chars]"

    return content


def _extract_pdf_text(path: Path) -> str:
    """
    Extrahiert Text aus einer PDF-Datei mit pdfplumber.

    GIVEN: Eine gültige PDF-Datei
    THEN:  Text aller Seiten als String, getrennt durch Page-Marker

    GIVEN: Eine beschädigte / unlesbare PDF
    THEN:  Informativer Fehlertext (kein Crash)
    """
    if not _PDF_AVAILABLE:
        return (
            "[PDF reading requires 'pdfplumber'. "
            "Install it with: pip install pdfplumber]"
        )

    try:
        pages: list[str] = []
        with _pdfplumber.open(str(path)) as pdf:
            total = len(pdf.pages)
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(f"--- Page {i}/{total} ---\n{text.strip()}")

        if not pages:
            return f"[PDF '{path.name}' contains no extractable text — may be scanned image]"

        full = "\n\n".join(pages)
        if len(full) > MAX_FILE_CHARS:
            full = full[:MAX_FILE_CHARS]
            full += f"\n\n[PDF truncated: original had more than {MAX_FILE_CHARS} chars]"
        return full

    except Exception as exc:  # pragma: no cover
        return f"[Could not read PDF '{path.name}': {exc}]"


# ===========================================================================
# Tool: source notebook
# ===========================================================================

async def create_source_notebook(
    paths: list[str] | str,
    title: str = "MiMi Nox Source Notebook",
    notebook_id: str = "",
    extensions: list[str] | None = None,
) -> str:
    """Create a local NotebookLM-style source index with citeable chunks."""
    out = await asyncio.to_thread(
        create_source_notebook_index,
        paths=paths,
        title=title,
        notebook_id=notebook_id,
        extensions=extensions,
    )
    return format_notebook_created(out)


async def query_source_notebook(
    notebook_path: str,
    question: str,
    max_chunks: int = 6,
) -> str:
    """Query a local source notebook and return evidence-grounded citations."""
    result = await asyncio.to_thread(
        query_source_notebook_index,
        notebook_path=notebook_path,
        question=question,
        max_chunks=max_chunks,
    )
    return format_notebook_query(result)


async def export_source_brief(
    notebook_path: str,
    question: str = "",
    filename: str = "",
) -> str:
    """Export a source-grounded Markdown brief with evidence register."""
    out = await asyncio.to_thread(
        export_source_brief_file,
        notebook_path=notebook_path,
        question=question,
        filename=filename,
    )
    return f"SOURCE_BRIEF_FILE:{out}"


# ===========================================================================
# Tool: list_directory
# ===========================================================================

async def list_directory(path: str) -> list[str]:
    """
    Listet Inhalte eines Verzeichnisses auf.

    Sicherheit: Nur Pfade innerhalb der Whitelist erlaubt.

    Raises:
        FileNotAllowedError:    Pfad außerhalb Whitelist
        DirectoryNotFoundError: Verzeichnis existiert nicht
    """
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))

    if not resolved.exists():
        raise DirectoryNotFoundError(str(resolved))

    entries = [entry.name for entry in sorted(resolved.iterdir())]
    if len(entries) > 500:
        return entries[:500] + ["... [Liste auf 500 Einträge gekürzt]"]
    return entries


# ===========================================================================
# Tool: get_datetime
# ===========================================================================

GERMAN_WEEKDAYS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]

GERMAN_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


async def get_datetime() -> str:
    """
    Gibt aktuelles Datum und Uhrzeit auf Deutsch zurück.

    Returns:
        z.B. "Donnerstag, 02. April 2026, 19:45 Uhr"
    """
    now = datetime.now()
    weekday = GERMAN_WEEKDAYS[now.weekday()]
    month = GERMAN_MONTHS[now.month - 1]
    return f"{weekday}, {now.day:02d}. {month} {now.year}, {now.hour:02d}:{now.minute:02d} Uhr"


# ===========================================================================
# Tool: discover_projects / analyze_project
# ===========================================================================

async def discover_projects(query: str = "", root: str | None = None, max_results: int = 10) -> str:
    """
    Findet lokale Code-Projekte in erlaubten Mac-User-Verzeichnissen und bewertet sie.
    """
    roots = None
    if root:
        candidate = Path(root).expanduser()
        if not _is_path_allowed(candidate):
            return f"Zugriff auf '{candidate}' nicht erlaubt (Sicherheits-Whitelist)."
        roots = [candidate]
    records = await asyncio.to_thread(
        discover_project_records,
        query=query,
        roots=roots,
        max_results=max(1, min(int(max_results), 25)),
    )
    return format_project_listing(records)


async def analyze_project(path: str) -> str:
    """
    Analysiert einen lokalen Projektordner und liefert einen Ist-Zustand-Bericht.
    """
    return await asyncio.to_thread(analyze_project_path, path)


# ===========================================================================
# Tool: run_shell (IMMER Bestätigung erforderlich)
# ===========================================================================

async def run_shell(command: str) -> str:
    """
    SICHERHEITS-GATE: Wirft immer ShellConfirmationRequired.

    Diese Funktion führt NIE direkt aus.
    Die App muss den User fragen und dann execute_confirmed_shell() aufrufen.

    Raises:
        ShellConfirmationRequired: immer
    """
    raise ShellConfirmationRequired(command)


async def execute_confirmed_shell(command: str, confirmed: bool) -> str:
    """
    Führt einen Shell-Befehl aus — NUR wenn confirmed=True.

    Args:
        command:   Der Shell-Befehl
        confirmed: Muss explizit True sein (User hat bestätigt)

    Returns:
        stdout + stderr kombiniert als String

    Raises:
        ShellTimeoutError: wenn Befehl > SHELL_TIMEOUT_SECONDS dauert
    """
    if not confirmed:
        return "Abgebrochen."

    try:
        result = await asyncio.to_thread(
            subprocess.run,
            command,
            shell=True,          # noqa: S602
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT_SECONDS,
        )
        output = result.stdout.strip()
        if result.returncode != 0:
            error = result.stderr.strip()
            final_out = f"{output}\n[exit {result.returncode}] {error}".strip()
        else:
            final_out = output or "(kein Output)"
            
        if len(final_out) > 10000:
            final_out = final_out[:10000] + "\n\n... [Shell-Output sicherheitshalber auf 10.000 Zeichen gekürzt]"
            
        return final_out

    except subprocess.TimeoutExpired:
        raise ShellTimeoutError(command, SHELL_TIMEOUT_SECONDS)


# ===========================================================================
# Tool: load_workspace (128K Context – ganze Verzeichnisse laden)
# ===========================================================================

async def load_workspace(
    path: str,
    extensions: list[str] | None = None,
    max_depth: int = MAX_WORKSPACE_DEPTH,
) -> str:
    """
    Liest rekursiv alle Text-Dateien eines Verzeichnisses.
    Optimiert für Gemma4 12B's 128K Context Window.

    Args:
        path:       Verzeichnis-Pfad
        extensions: Nur diese Dateiendungen (z.B. [".py", ".md"]). None = alle Text-Dateien.
        max_depth:  Maximale Rekursionstiefe (Standard: 3)

    Returns:
        Zusammengefasster Dateiinhalt mit Pfad-Headern

    Raises:
        FileNotAllowedError:    Pfad außerhalb Whitelist
        DirectoryNotFoundError: Verzeichnis existiert nicht
    """
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))
    if not resolved.is_dir():
        raise DirectoryNotFoundError(str(resolved))

    allowed_ext = set(extensions) if extensions else None
    parts: list[str] = []
    total_chars = 0

    def _collect(dir_path: Path, depth: int) -> None:
        nonlocal total_chars
        if depth > max_depth or total_chars >= MAX_WORKSPACE_CHARS:
            return
        try:
            entries = sorted(dir_path.iterdir())
        except PermissionError:
            return
        for entry in entries:
            if total_chars >= MAX_WORKSPACE_CHARS:
                break
            if entry.is_dir() and not entry.name.startswith("."):
                _collect(entry, depth + 1)
            elif entry.is_file():
                if allowed_ext and entry.suffix.lower() not in allowed_ext:
                    continue
                if entry.name.startswith("."):
                    continue
                try:
                    content = entry.read_text(encoding="utf-8", errors="replace")
                    remaining = MAX_WORKSPACE_CHARS - total_chars
                    if len(content) > remaining:
                        content = content[:remaining] + "\n[... abgeschnitten]"
                    rel = entry.relative_to(resolved)
                    parts.append(f"\n### 📄 {rel}\n```\n{content}\n```")
                    total_chars += len(content)
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue

    _collect(resolved, 0)

    if not parts:
        return f"Keine passenden Dateien in '{resolved}' gefunden."

    header = f"## 📁 Workspace: {resolved}\n{len(parts)} Dateien geladen\n"
    result = header + "\n".join(parts)

    if total_chars >= MAX_WORKSPACE_CHARS:
        result += f"\n\n[⚠ Workspace gekürzt: Limit von {MAX_WORKSPACE_CHARS:,} Zeichen erreicht]"

    return result


# ===========================================================================
# Tool: analyze_image (Gemma4 12B Vision / OCR)
# ===========================================================================

async def analyze_image(
    path: str,
    question: str = "Beschreibe dieses Bild detailliert.",
) -> str:
    """
    Analysiert ein Bild via Gemma4 12B's native multimodale Fähigkeit.

    Args:
        path:     Pfad zum Bild
        question: Frage zum Bild (Default: Beschreibung)

    Returns:
        Bildbeschreibung / OCR-Ergebnis als Text

    Raises:
        FileNotAllowedError:  Pfad außerhalb Whitelist
        FileNotFoundError:    Bild existiert nicht
    """
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))
    if not resolved.exists():
        raise FileNotFoundError(f"Bild nicht gefunden: '{resolved}'")
    if resolved.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
        return (
            f"Nicht unterstütztes Bildformat: '{resolved.suffix}'. "
            f"Unterstützt: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
        )

    # Bild als Base64 für Ollama Vision API
    image_bytes = resolved.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    client = _get_shared_client()
    try:
        response = await client.chat(
            model=os.environ.get("MIMI_NOX_MODEL", "gemma4:12b"),
            messages=[
                {
                    "role": "user",
                    "content": question,
                    "images": [image_b64],
                },
            ],
            stream=False,
        )
        return str(response.message.content or "Keine Beschreibung generiert.")
    except Exception as exc:
        return f"[Vision-Fehler: {exc}]"


# ===========================================================================
# Tool: take_screenshot 
# ===========================================================================

async def take_screenshot() -> str:
    """
    Erstellt einen Desktop-Screenshot (Cross-Platform) und liefert die URL zurück.

    Plattform-Support:
      - macOS:   screencapture (nativ, beste Qualität)
      - Linux:   mss (headless-kompatibel, kein X11 nötig für Wayland)
      - Windows: mss

    Returns: Markdown-formatiertes Bild für den Chat-Verlauf.
    """
    import time

    image_dir = Path(os.environ.get("MIMI_NOX_IMAGE_DIR", str(Path.home() / ".mimi-nox" / "sessions" / "images")))
    image_dir.mkdir(parents=True, exist_ok=True)

    filename = f"screenshot_{int(time.time())}.png"
    filepath = image_dir / filename

    try:
        if sys.platform == "darwin":
            # macOS: Native screencapture (beste Qualität)
            await asyncio.to_thread(
                subprocess.run, ["screencapture", "-x", str(filepath)], check=True
            )
        else:
            # Linux / Windows: mss (bereits in dependencies)
            def _mss_capture():
                import mss
                with mss.mss() as sct:
                    sct.shot(output=str(filepath))
            await asyncio.to_thread(_mss_capture)

        return f"Hier ist der Bildschirm:\n\n![Screenshot](/images/{filename})"
    except subprocess.CalledProcessError as e:
        if sys.platform == "darwin":
            return (
                "[Screenshot fehlgeschlagen: macOS hat die Bildschirmaufnahme blockiert. "
                "Erlaube dem Terminal/Codex-Prozess in Systemeinstellungen > Datenschutz & Sicherheit "
                "> Bildschirmaufnahme den Zugriff und starte MiMi Nox danach neu.]"
            )
        return f"[Screenshot fehlgeschlagen: {e}]"
    except Exception as e:
        return f"[Screenshot fehlgeschlagen: {e}]"


# ===========================================================================
# Tool Execution Router
# ===========================================================================

# Lazy import: vision requires pyautogui which crashes on headless Linux (no DISPLAY)
def _get_vision_click():
    from core.vision import vision_click
    return vision_click

def _get_vision_type():
    from core.vision import vision_type
    return vision_type

async def _vision_click_wrapper(target_description: str) -> str:
    fn = _get_vision_click()
    return await fn(target_description)

async def _vision_type_wrapper(text: str, press_enter: bool = False) -> str:
    fn = _get_vision_type()
    return await fn(text, press_enter)

# Expose as module-level names for hasattr() checks in tests
vision_click = _vision_click_wrapper
vision_type = _vision_type_wrapper

def _get_browser_manager():
    from core.browser import browser_manager
    return browser_manager

async def browser_go(url: str) -> str:
    browser_manager = _get_browser_manager()
    return await browser_manager.go(url)

async def browser_screenshot() -> str:
    import time, base64
    browser_manager = _get_browser_manager()
    b64 = await browser_manager.screenshot()
    image_dir = Path(os.environ.get("MIMI_NOX_IMAGE_DIR", str(Path.home() / ".mimi-nox" / "sessions" / "images")))
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = f"browser_{int(time.time())}.jpeg"
    with open(image_dir / filename, "wb") as f:
        f.write(base64.b64decode(b64))
    return f"Browser Screenshot aufgenommen:\n\n![Browser](/images/{filename})"

async def browser_click(target_description: str) -> str:
    browser_manager = _get_browser_manager()
    return await browser_manager.click(target_description)

async def browser_type(text: str) -> str:
    browser_manager = _get_browser_manager()
    return await browser_manager.type_text(text)

async def browser_press(key: str) -> str:
    browser_manager = _get_browser_manager()
    return await browser_manager.press(key)


# ===========================================================================
# Tool: generate_chart  (matplotlib → PNG Base64)
# ===========================================================================

async def generate_chart(
    chart_type: str,
    title: str,
    labels: list,
    values: list,
    xlabel: str = "",
    ylabel: str = "",
    color: str = "#22c55e",
) -> str:
    """
    Erstellt einen Chart (bar / line / pie) mit matplotlib.
    Gibt den Dateipfad zurück; das Frontend zeigt ihn als Bild an.

    Args:
        chart_type: "bar", "line" oder "pie"
        title:      Titel des Charts
        labels:     X-Achsen-Labels oder Pie-Segmente
        values:     Numerische Werte
        xlabel:     X-Achsen-Beschriftung (optional)
        ylabel:     Y-Achsen-Beschriftung (optional)
        color:      Hex-Farbe (default: MiMiNox-Grün)
    """
    return _generate_svg_chart(chart_type, title, labels, values, xlabel=xlabel, ylabel=ylabel, color=color)


def _generate_svg_chart(
    chart_type: str,
    title: str,
    labels: list,
    values: list,
    xlabel: str = "",
    ylabel: str = "",
    color: str = "#16a34a",
) -> str:
    try:
        vals = [float(v) for v in values]
        clean_labels = [str(label)[:32] for label in labels]
        if len(clean_labels) != len(vals) or not vals:
            return "[chart: Labels und Werte muessen gleich lang und nicht leer sein]"
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip())[:48].strip("_") or "chart"
        out = downloads / f"mimi_nox_chart_{safe_title}_{int(time.time())}.svg"
        width, height = 960, 600
        margin_left, margin_bottom, margin_top, margin_right = 94, 88, 92, 54
        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom
        max_val = max(vals) or 1.0
        min_val = min(0.0, min(vals))
        val_span = max(max_val - min_val, 1.0)
        accent = color if re.match(r"^#[0-9a-fA-F]{6}$", color) else "#16a34a"

        def sx(index: int) -> float:
            if len(vals) == 1:
                return margin_left + plot_w / 2
            return margin_left + index * (plot_w / (len(vals) - 1))

        def sy(value: float) -> float:
            return margin_top + plot_h - ((value - min_val) / val_span) * plot_h

        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            '<rect width="960" height="600" fill="#fbfcfb"/>',
            '<rect x="0" y="0" width="960" height="10" fill="#101820"/>',
            f'<text x="54" y="58" font-family="Arial, sans-serif" font-size="30" font-weight="700" fill="#101820">{html.escape(title)}</text>',
            f'<text x="54" y="86" font-family="Arial, sans-serif" font-size="13" fill="#53606f">{html.escape(ylabel or "Values")} by {html.escape(xlabel or "Category")}</text>',
            f'<line x1="{margin_left}" y1="{margin_top + plot_h}" x2="{margin_left + plot_w}" y2="{margin_top + plot_h}" stroke="#9ca3af" stroke-width="1"/>',
            f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{margin_top + plot_h}" stroke="#9ca3af" stroke-width="1"/>',
        ]
        for tick in range(5):
            value = min_val + val_span * tick / 4
            y = sy(value)
            parts.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{margin_left + plot_w}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
            parts.append(f'<text x="{margin_left - 14}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#53606f">{value:g}</text>')

        ct = chart_type.lower()
        if ct == "bar":
            step = plot_w / max(len(vals), 1)
            bar_w = min(82, step * 0.58)
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                x = margin_left + index * step + (step - bar_w) / 2
                y = sy(value)
                h = margin_top + plot_h - y
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" fill="{accent}"/>')
                parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#101820">{value:g}</text>')
                parts.append(f'<text x="{x + bar_w / 2:.1f}" y="{margin_top + plot_h + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#53606f">{html.escape(label)}</text>')
        elif ct == "line":
            points = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(vals))
            parts.append(f'<polyline points="{points}" fill="none" stroke="{accent}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round"/>')
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                x, y = sx(index), sy(value)
                parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#fbfcfb" stroke="{accent}" stroke-width="3"/>')
                parts.append(f'<text x="{x:.1f}" y="{margin_top + plot_h + 28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#53606f">{html.escape(label)}</text>')
        elif ct == "pie":
            total = sum(abs(v) for v in vals) or 1.0
            x0, y0 = margin_left + 250, margin_top + 220
            start = -90.0
            palette = [accent, "#0891b2", "#d97706", "#64748b", "#22c55e", "#0f766e"]
            import math
            for index, (label, value) in enumerate(zip(clean_labels, vals)):
                angle = abs(value) / total * 360
                end = start + angle
                large = 1 if angle > 180 else 0
                x1 = x0 + 150 * math.cos(math.radians(start))
                y1 = y0 + 150 * math.sin(math.radians(start))
                x2 = x0 + 150 * math.cos(math.radians(end))
                y2 = y0 + 150 * math.sin(math.radians(end))
                fill = palette[index % len(palette)]
                parts.append(f'<path d="M{x0:.1f},{y0:.1f} L{x1:.1f},{y1:.1f} A150,150 0 {large},1 {x2:.1f},{y2:.1f} Z" fill="{fill}"/>')
                parts.append(f'<rect x="650" y="{150 + index * 28}" width="14" height="14" fill="{fill}"/><text x="674" y="{162 + index * 28}" font-family="Arial, sans-serif" font-size="13" fill="#101820">{html.escape(label)} ({value:g})</text>')
                start = end
        else:
            return f"[chart: Unbekannter Typ '{chart_type}'. Erlaubt: bar, line, pie]"

        parts.append('<text x="54" y="568" font-family="Arial, sans-serif" font-size="12" fill="#53606f">Generated locally by MiMi Nox - SVG fallback renderer</text>')
        parts.append("</svg>")
        out.write_text("\n".join(parts), encoding="utf-8")
        return f"CHART_FILE:{out}"
    except Exception as exc:
        return f"[chart-Fehler: {exc}]"


# ===========================================================================
# Tool: create_pdf  (reportlab → PDF-Datei)
# ===========================================================================

def _apply_pdf_template(content: str, template: str) -> str:
    text = (content or "").strip()
    lowered = text.lower()
    template = (template or "report").lower()
    sections: dict[str, list[str]] = {
        "report": ["# Executive Summary", "## Findings", "## Next Steps", "### Source Notes"],
        "brief": ["# Executive Summary", "## Key Points", "### Source Notes"],
        "analysis": ["# Executive Summary", "## Evidence", "## Risks", "## Recommendations", "### Appendix"],
        "checklist": ["# Executive Summary", "## Checklist", "## Acceptance Criteria", "### Source Notes"],
    }
    required = sections.get(template, sections["report"])
    missing = [section for section in required if section.lstrip("# ").lower() not in lowered]
    if not missing:
        return text
    inserted = [missing[0], text]
    for section in missing[1:]:
        inserted.extend(["", section, "- Not specified in the source input."])
    return "\n".join(inserted).strip()


async def create_pdf(
    title: str,
    content: str,
    filename: str = "nox_dokument.pdf",
    template: str = "report",
) -> str:
    """
    Erstellt ein formatiertes PDF-Dokument aus Text/Markdown-ähnlichem Inhalt.

    Args:
        title:    Dokumenttitel (erscheint als große Überschrift)
        content:  Textinhalt (# = H1, ## = H2, - = Bullet, normaler Text = Absatz)
        filename: Dateiname ohne Pfad (wird in ~/Downloads gespeichert)
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        import html
        import re

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_name = Path(filename).name
        safe_name = re.sub(r"\s+", "_", safe_name.strip())
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "", safe_name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("._-")
        if not safe_name:
            safe_name = "nox_dokument.pdf"
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"
        out = downloads / safe_name

        doc = SimpleDocTemplate(
            str(out), pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=24*mm, bottomMargin=24*mm,
            title=title,
            author="MiMi Nox",
            subject="MiMi Nox report",
        )

        # Print-friendly MiMi Nox palette on a white PDF page.
        GREEN   = colors.HexColor("#16a34a")
        GREEN_L = colors.HexColor("#22c55e")
        TEXT    = colors.HexColor("#111827")
        MUTED   = colors.HexColor("#6b7280")

        styles = getSampleStyleSheet()
        def S(name, **kw):
            return ParagraphStyle(name, **kw)

        s_title = S("T", fontSize=22, textColor=GREEN, spaceAfter=10, spaceBefore=0,
                    leading=28, fontName="Helvetica-Bold", alignment=TA_CENTER)
        s_h1    = S("H1", fontSize=15, textColor=GREEN_L, spaceAfter=4, spaceBefore=12,
                    fontName="Helvetica-Bold")
        s_h2    = S("H2", fontSize=12, textColor=GREEN_L, spaceAfter=3, spaceBefore=8,
                    fontName="Helvetica-Bold")
        s_h3    = S("H3", fontSize=10.5, textColor=GREEN_L, spaceAfter=3, spaceBefore=6,
                    fontName="Helvetica-Bold")
        s_body  = S("B", fontSize=10, textColor=TEXT, spaceAfter=6, leading=16,
                    fontName="Helvetica")
        s_bullet= S("BL", fontSize=10, textColor=TEXT, spaceAfter=3, leading=15,
                    leftIndent=12, fontName="Helvetica",
                    bulletText="-", bulletIndent=4)
        s_numbered = S("NL", fontSize=10, textColor=TEXT, spaceAfter=3, leading=15,
                       leftIndent=12, fontName="Helvetica")
        s_meta  = S("M", fontSize=8, textColor=MUTED, spaceAfter=12, alignment=TA_CENTER,
                    fontName="Helvetica")

        def _inline(text: str) -> str:
            escaped = html.escape(text, quote=False)
            return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)

        content = _apply_pdf_template(content, template)

        story = []
        story.append(Paragraph(title, s_title))
        story.append(Paragraph(f"Erstellt von MiMi Nox - {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_meta))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREEN, spaceAfter=10))

        for line in content.splitlines():
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
            elif line.startswith("### "):
                story.append(Paragraph(_inline(line[4:]), s_h3))
            elif line.startswith("## "):
                story.append(Paragraph(_inline(line[3:]), s_h2))
            elif line.startswith("# "):
                story.append(Paragraph(_inline(line[2:]), s_h1))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph(_inline(line[2:]), s_bullet))
            elif re.match(r"^\d+\.\s+", line):
                story.append(Paragraph(_inline(line), s_numbered))
            else:
                story.append(Paragraph(_inline(line), s_body))

        def _footer(canvas, pdf_doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(20 * mm, 12 * mm, "MiMi Nox")
            canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Seite {pdf_doc.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return f"PDF_FILE:{out}"

    except ImportError:
        return "[pdf: reportlab nicht installiert — 'pip install reportlab']"
    except Exception as e:
        return f"[pdf-Fehler: {e}]"


def _safe_download_filename(filename: str, default: str, suffix: str) -> str:
    safe_name = Path(filename or default).name
    safe_name = re.sub(r"\s+", "_", safe_name.strip())
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "", safe_name)
    safe_name = re.sub(r"_+", "_", safe_name).strip("._-")
    if not safe_name:
        safe_name = default
    if not safe_name.lower().endswith(suffix):
        safe_name += suffix
    return safe_name


def _split_lines(text: str, max_chars: int = 72, max_lines: int = 4) -> list[str]:
    words = (text or "").strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:max_lines] or [""]


def _enterprise_clean_text(text: str) -> str:
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF]", "", str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    replacements = {
        "awesome": "strong",
        "cool": "credible",
        "fun": "engaging",
        "cute": "clean",
        "wow": "notable",
        "magic": "workflow",
        "revolutionary": "material",
        "game changer": "strategic shift",
        "amazing": "strong",
        "super": "high",
        "mega": "large",
        "krass": "deutlich",
        "geil": "stark",
        "kindisch": "unreif",
        "lustig": "ansprechend",
    }
    for source, target in replacements.items():
        cleaned = re.sub(rf"\b{re.escape(source)}\b", target, cleaned, flags=re.IGNORECASE)
    return cleaned


def _normalize_enterprise_slides(slides: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, slide in enumerate(slides, 1):
        title = _enterprise_clean_text(slide.get("title") or f"Slide {index}")
        claim = _enterprise_clean_text(slide.get("claim") or title)
        body = _enterprise_clean_text(slide.get("body") or "")
        proof = _enterprise_clean_text(slide.get("proof") or "Proof object")
        visual = re.sub(r"[^a-z0-9_-]", "", str(slide.get("visual") or "custom").lower()) or "custom"
        normalized.append({"title": title, "claim": claim, "body": body, "visual": visual, "proof": proof})
    return normalized


def _default_deck_slides(topic: str, audience: str, thesis: str) -> list[dict[str, str]]:
    subject = topic.strip() or "MiMi Nox"
    audience_text = audience.strip() or "decision makers"
    thesis_text = thesis.strip() or f"{subject} turns local AI workflows into reliable, private execution."
    return [
        {"title": subject, "claim": thesis_text, "body": f"For {audience_text}: a focused investment-grade story with proof, workflow, and next step.", "visual": "hero", "proof": "Thesis card"},
        {"title": "The Shift", "claim": "Users now expect local AI to produce finished work, not rough drafts.", "body": "Privacy, latency, and tool control are becoming product requirements. The winning system makes local execution feel premium and verifiable.", "visual": "trend", "proof": "Market shift curve"},
        {"title": "Problem", "claim": "Most local assistants fail when work becomes multi-step or artifact-heavy.", "body": "They lose context, over-promise tool results, and generate files that are hard to trust without manual inspection.", "visual": "pain", "proof": "Failure stack"},
        {"title": "Solution", "claim": f"{subject} combines skills, tools, memory, and quality gates into one local workflow.", "body": "The user asks naturally; the system selects the right skill, executes real local tools, checks artifacts, and returns grounded output.", "visual": "system", "proof": "Workflow architecture"},
        {"title": "Product Experience", "claim": "The interface must show progress, evidence, and artifacts without making users manage the machinery.", "body": "Skill chips, activity status, file paths, and artifact checks keep the workflow understandable while the assistant does the work.", "visual": "interface", "proof": "Experience map"},
        {"title": "Proof Of Quality", "claim": "High-end output comes from repeatable rubrics, not from style prompts alone.", "body": "Each flagship skill needs a rubric, examples, deterministic validation, and local eval cases for regression control.", "visual": "score", "proof": "Quality ladder"},
        {"title": "Market Logic", "claim": "Local-first AI is a defensible wedge where privacy and control matter.", "body": "Developers, founders, operators, and creators need artifact-grade output while keeping files, screenshots, and workflows on the machine.", "visual": "market", "proof": "Segment matrix"},
        {"title": "Execution Roadmap", "claim": "The next milestone is premium artifact creation across PDFs, decks, charts, scans, and code.", "body": "Start with deck/PDF quality, then expand validators and evals across every user-facing skill.", "visual": "roadmap", "proof": "Milestone plan"},
        {"title": "Risks And Controls", "claim": "Trust improves when uncertainty is visible and fake success is impossible.", "body": "Missing inputs, failed tools, weak evidence, and invalid artifacts should surface as warnings instead of confident claims.", "visual": "risk", "proof": "Control gates"},
        {"title": "The Ask", "claim": "Standardize every skill around real tools, evidence, and polished artifacts.", "body": "Approve the local high-end artifact system as the default for future MiMi Nox user workflows.", "visual": "ask", "proof": "Decision frame"},
        {"title": "Appendix", "claim": "Animation plan, source notes, and scorecard are included for presenter-ready refinement.", "body": "Use the companion HTML preview for motion direction. Replace generated visual motifs with product screenshots or brand assets when available.", "visual": "appendix", "proof": "Source notes"},
    ]


def _parse_deck_slides(slides: list[dict] | str | None, topic: str, audience: str, thesis: str) -> list[dict[str, str]]:
    if isinstance(slides, str) and slides.strip():
        parsed: list[dict[str, str]] = []
        blocks = [block.strip() for block in re.split(r"\n\s*\n", slides) if block.strip()]
        for index, block in enumerate(blocks, 1):
            lines = [line.strip(" -") for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            parsed.append({
                "title": lines[0].lstrip("# ").strip() or f"Slide {index}",
                "claim": lines[1] if len(lines) > 1 else lines[0],
                "body": " ".join(lines[2:]) if len(lines) > 2 else "",
                "visual": "custom",
                "proof": "Proof object",
            })
        if parsed:
            return parsed

    if isinstance(slides, list) and slides:
        normalized = []
        for index, raw in enumerate(slides, 1):
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or raw.get("headline") or f"Slide {index}").strip()
            claim = str(raw.get("claim") or raw.get("subtitle") or title).strip()
            body = str(raw.get("body") or raw.get("notes") or raw.get("content") or "").strip()
            visual = str(raw.get("visual") or raw.get("layout") or "custom").strip()
            proof = str(raw.get("proof") or raw.get("proof_object") or raw.get("evidence") or "Proof object").strip()
            normalized.append({"title": title, "claim": claim, "body": body, "visual": visual, "proof": proof})
        if normalized:
            return normalized

    return _default_deck_slides(topic, audience, thesis)


async def create_pitch_deck(
    topic: str,
    audience: str = "investors",
    thesis: str = "",
    slides: list[dict] | str | None = None,
    filename: str = "mimi_nox_pitch_deck.pdf",
    include_animation_preview: bool = True,
    deck_profile: str = "product-platform",
    design_theme: str = "evergreen",
    source_notes: str = "",
    evidence_level: str = "assumptions",
    enterprise_grade: bool = True,
    deck_quality_profile: str = "enterprise",
    brand_kit: dict | None = None,
    source_notebook_path: str = "",
    asset_paths: list[str] | str | None = None,
) -> str:
    """Create a 16:9 pitch-deck PDF plus an optional animated HTML preview."""
    try:
        from core.deck_design import normalize_profile, normalize_theme
        from core.deck_model import build_deck_spec
        from core.deck_render import write_deck_artifacts

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_pdf = _safe_download_filename(filename, "mimi_nox_pitch_deck.pdf", ".pdf")
        out = downloads / safe_pdf
        deck_profile = normalize_profile(deck_profile or "product-platform")
        design_theme = normalize_theme(design_theme or "executive", enterprise_grade=enterprise_grade)
        normalized_assets = _normalize_deck_asset_paths(asset_paths)
        if source_notebook_path and not source_notes.strip():
            source_notes = f"Grounded in local source notebook: {source_notebook_path}"
        if source_notebook_path and evidence_level == "assumptions":
            evidence_level = "sources"
        spec = build_deck_spec(
            title=topic or "MiMi Nox Pitch Deck",
            audience=audience,
            thesis=thesis,
            slides=slides,
            deck_profile=deck_profile,
            design_theme=design_theme,
            source_notes=source_notes.strip() or "Generated from user prompt; no external company metrics or source files were provided.",
            evidence_level=evidence_level.strip() or "assumptions",
            enterprise_grade=enterprise_grade,
            brand_kit=brand_kit or {},
            wants_images=bool(asset_paths),
            source_brief_path=source_notebook_path,
            asset_paths=normalized_assets,
            deck_quality_profile=deck_quality_profile,
        )
        paths = write_deck_artifacts(spec=spec, pdf_path=out, include_preview=include_animation_preview)
        result = [
            f"PITCH_DECK_FILE:{paths['pdf']}",
            f"SCORECARD_FILE:{paths['scorecard']}",
            f"MANIFEST_FILE:{paths['manifest']}",
            f"RENDER_QA_FILE:{paths['render_qa']}",
            f"DECK_SPEC_FILE:{paths['deck_spec']}",
            f"VISUAL_QA_FILE:{paths['visual_qa']}",
            f"EVIDENCE_LEDGER_FILE:{paths['evidence_ledger']}",
        ]
        if include_animation_preview:
            result.insert(1, f"PREVIEW_FILE:{paths['preview']}")
        return "\n".join(result)
    except Exception as e:
        return f"[pitch-deck-Fehler: {e}]"


async def create_pptx_deck(
    topic: str,
    audience: str = "board and executive committee",
    thesis: str = "",
    slides: list[dict] | str | None = None,
    filename: str = "mimi_nox_pitch_deck.pptx",
    deck_profile: str = "strategy-leadership",
    design_theme: str = "executive",
    source_notes: str = "",
    evidence_level: str = "assumptions",
    enterprise_grade: bool = True,
    template_path: str = "",
    brand_name: str = "",
    brand_primary: str = "",
    brand_secondary: str = "",
    deck_quality_profile: str = "enterprise",
    source_notebook_path: str = "",
    asset_paths: list[str] | str | None = None,
) -> str:
    """Create an editable local PPTX deck with enterprise scorecard and manifest."""
    try:
        from core.deck_design import normalize_profile, normalize_theme
        from core.deck_model import build_deck_spec
        from core.deck_render import write_deck_artifacts

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_pptx = _safe_download_filename(filename, "mimi_nox_pitch_deck.pptx", ".pptx")
        out = downloads / safe_pptx
        pdf_peer = out.with_suffix(".pdf")
        deck_profile = normalize_profile(deck_profile)
        design_theme = normalize_theme(design_theme, enterprise_grade=enterprise_grade)
        template_info = _inspect_pptx_template_file(template_path) if template_path else {}
        brand_kit = _deck_v2_brand_kit(
            brand_name=brand_name,
            brand_primary=brand_primary or str(template_info.get("primary_color", "")),
            brand_secondary=brand_secondary or str(template_info.get("secondary_color", "")),
        )
        normalized_assets = _normalize_deck_asset_paths(asset_paths)
        if source_notebook_path and not source_notes.strip():
            source_notes = f"Grounded in local source notebook: {source_notebook_path}"
        if source_notebook_path and evidence_level == "assumptions":
            evidence_level = "sources"
        spec = build_deck_spec(
            title=topic or "MiMi Nox Pitch Deck",
            audience=audience,
            thesis=thesis,
            slides=slides,
            deck_profile=deck_profile,
            design_theme=design_theme,
            source_notes=source_notes.strip() or "Generated from user prompt; no external company metrics or source files were provided.",
            evidence_level=evidence_level.strip() or "assumptions",
            enterprise_grade=enterprise_grade,
            brand_kit=brand_kit,
            wants_images=bool(asset_paths),
            source_brief_path=source_notebook_path,
            asset_paths=normalized_assets,
            deck_quality_profile=deck_quality_profile,
        )
        if template_info:
            spec["template_info"] = template_info
        paths = write_deck_artifacts(spec=spec, pdf_path=pdf_peer, pptx_path=out, include_preview=True)
        return "\n".join([
            f"PPTX_DECK_FILE:{paths['pptx']}",
            f"SCORECARD_FILE:{paths['pptx_scorecard']}",
            f"MANIFEST_FILE:{paths['pptx_manifest']}",
            f"QA_FILE:{paths['pptx_qa']}",
            f"CONTACT_SHEET_FILE:{paths['contact_sheet']}",
            f"DECK_SPEC_FILE:{paths['pptx_deck_spec']}",
            f"VISUAL_QA_FILE:{paths['pptx_visual_qa']}",
            f"EVIDENCE_LEDGER_FILE:{paths['pptx_evidence_ledger']}",
        ])
    except Exception as e:
        return f"[pptx-deck-Fehler: {e}]"


async def inspect_pptx_template(path: str, filename: str = "mimi_nox_template_analysis.json") -> str:
    """Inspect a local PPTX template and write reusable style/layout metadata."""
    try:
        analysis = _inspect_pptx_template_file(path)
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / _safe_download_filename(filename, "mimi_nox_template_analysis.json", ".json")
        out.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"PPTX_TEMPLATE_ANALYSIS_FILE:{out}"
    except Exception as exc:
        return f"[pptx-template-Fehler: {exc}]"


async def edit_pptx_template(
    template_path: str,
    replacements: dict | list,
    filename: str = "mimi_nox_template_edit.pptx",
) -> str:
    """Copy a PPTX and replace editable text runs while preserving existing layout/styles."""
    try:
        src = _resolve_allowed_file(template_path)
        if src.suffix.lower() != ".pptx":
            raise ValueError("template_path must point to a .pptx file")
        mapping: dict[str, str] = {}
        if isinstance(replacements, dict):
            mapping = {str(k): str(v) for k, v in replacements.items()}
        elif isinstance(replacements, list):
            for item in replacements:
                if isinstance(item, dict) and "from" in item and "to" in item:
                    mapping[str(item["from"])] = str(item["to"])
        if not mapping:
            raise ValueError("replacements must contain at least one from/to mapping")

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / _safe_download_filename(filename, "mimi_nox_template_edit.pptx", ".pptx")
        changed_runs = 0
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
                    xml = data.decode("utf-8", errors="replace")
                    for old, new in mapping.items():
                        escaped_old = _xml_escape(old)
                        if escaped_old in xml:
                            changed_runs += xml.count(escaped_old)
                            xml = xml.replace(escaped_old, _xml_escape(_enterprise_clean_text(new)))
                    data = xml.encode("utf-8")
                zout.writestr(info, data)

        qa = _qa_pptx_deck_file(out)
        manifest = {
            "artifact_type": "pptx_template_edit",
            "source_template": str(src),
            "edited_file": str(out),
            "replacement_count": len(mapping),
            "changed_text_runs": changed_runs,
            "review_gates": ["template_package_preserved", "editable_text_replaced", "pptx_qa_generated"],
        }
        score = {
            "artifact_type": "pptx_template_edit",
            "quality_score": 100 if changed_runs else 75,
            "minimum_score": 92,
            "enterprise_grade": True,
            "status": "passed" if changed_runs else "failed",
            "checks": {
                "template_package_preserved": True,
                "editable_text_replaced": changed_runs > 0,
                "pptx_valid": not qa.get("warnings"),
                "no_amateur_language": True,
            },
            "warnings": [] if changed_runs else ["No matching text runs were replaced."],
        }
        out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".scorecard.json").write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".contact-sheet.html").write_text(_render_pptx_contact_sheet(out, qa), encoding="utf-8")
        return f"PPTX_DECK_FILE:{out}\nSCORECARD_FILE:{out.with_suffix('.scorecard.json')}\nMANIFEST_FILE:{out.with_suffix('.manifest.json')}\nQA_FILE:{out.with_suffix('.qa.json')}\nCONTACT_SHEET_FILE:{out.with_suffix('.contact-sheet.html')}"
    except Exception as exc:
        return f"[pptx-edit-Fehler: {exc}]"


async def qa_pptx_deck(pptx_path: str) -> str:
    """Create local QA JSON and an HTML contact sheet for a PPTX deck."""
    try:
        src = _resolve_allowed_file(pptx_path)
        qa = _qa_pptx_deck_file(src)
        qa_out = src.with_suffix(".qa.json")
        contact_out = src.with_suffix(".contact-sheet.html")
        qa_out.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        contact_out.write_text(_render_pptx_contact_sheet(src, qa), encoding="utf-8")
        return f"PPTX_QA_FILE:{qa_out}\nCONTACT_SHEET_FILE:{contact_out}"
    except Exception as exc:
        return f"[pptx-qa-Fehler: {exc}]"


def _pdf_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _pdf_text(text: str, x: float, y: float, size: int, font: str = "F1", color: str = "0.06 0.09 0.13") -> str:
    return f"BT {color} rg /{font} {size} Tf {x:.1f} {y:.1f} Td ({_pdf_escape(text)}) Tj ET\n"


def _xml_escape(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _resolve_allowed_file(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    if not _is_path_allowed(candidate):
        raise FileNotAllowedError(str(candidate))
    return candidate.resolve()


def _normalize_hex_color(value: str, fallback: str = "") -> str:
    text = str(value or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", text):
        return text.upper()
    return fallback


def _normalize_brand_kit(brand_name: str = "", brand_primary: str = "", brand_secondary: str = "") -> dict[str, str]:
    primary = _normalize_hex_color(brand_primary, "")
    secondary = _normalize_hex_color(brand_secondary, "")
    return {
        "brand_name": _enterprise_clean_text(brand_name)[:80],
        "primary": primary,
        "secondary": secondary,
    }


def _deck_v2_brand_kit(brand_name: str = "", brand_primary: str = "", brand_secondary: str = "") -> dict[str, str]:
    from core.deck_design import normalize_brand_kit

    return normalize_brand_kit(brand_name=brand_name, brand_primary=brand_primary, brand_secondary=brand_secondary)


def _normalize_deck_asset_paths(asset_paths: list[str] | str | None) -> list[str]:
    if not asset_paths:
        return []
    raw_paths = [asset_paths] if isinstance(asset_paths, str) else list(asset_paths)
    normalized: list[str] = []
    for raw in raw_paths:
        candidate = Path(str(raw)).expanduser()
        if candidate.exists() and _is_path_allowed(candidate):
            normalized.append(str(candidate.resolve()))
    return normalized


def _inspect_pptx_template_file(path: str | Path) -> dict:
    src = _resolve_allowed_file(str(path))
    if src.suffix.lower() != ".pptx":
        raise ValueError("Template muss eine .pptx Datei sein")
    with zipfile.ZipFile(src) as pptx:
        names = set(pptx.namelist())
        slide_names = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        text_runs = 0
        colors: dict[str, int] = {}
        samples: list[str] = []
        for slide_name in slide_names:
            xml = pptx.read(slide_name).decode("utf-8", errors="replace")
            text_runs += xml.count("<a:t>")
            for color in re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', xml):
                colors[color.upper()] = colors.get(color.upper(), 0) + 1
            for text in re.findall(r"<a:t>(.*?)</a:t>", xml):
                clean = re.sub(r"\s+", " ", html.unescape(text)).strip()
                if clean and len(samples) < 12:
                    samples.append(clean[:120])
        presentation_xml = pptx.read("ppt/presentation.xml").decode("utf-8", errors="replace") if "ppt/presentation.xml" in names else ""
    ranked_colors = sorted(colors.items(), key=lambda item: item[1], reverse=True)
    return {
        "template_path": str(src),
        "slide_count": len(slide_names),
        "editable_text_runs": text_runs,
        "primary_color": ranked_colors[0][0] if ranked_colors else "",
        "secondary_color": ranked_colors[1][0] if len(ranked_colors) > 1 else "",
        "palette": [color for color, _ in ranked_colors[:8]],
        "wide_screen": "type=\"wide\"" in presentation_xml or "12192000" in presentation_xml,
        "sample_text": samples,
        "warnings": [] if slide_names else ["No slide XML files found."],
    }


def _emu(inches: float) -> int:
    return int(inches * 914400)


def _hex_from_pdf_rgb(rgb: str) -> str:
    parts = [float(part) for part in rgb.split()[:3]]
    return "".join(f"{max(0, min(255, round(part * 255))):02X}" for part in parts)


def _pptx_textbox(
    shape_id: int,
    name: str,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    font_size: int,
    color: str,
    bold: bool = False,
) -> str:
    bold_attr = ' b="1"' if bold else ""
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{_xml_escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
  <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="{font_size * 100}"{bold_attr}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>{_xml_escape(text)}</a:t></a:r><a:endParaRPr lang="en-US" sz="{font_size * 100}"/></a:p></p:txBody>
</p:sp>"""


def _pptx_rect(shape_id: int, name: str, x: float, y: float, w: float, h: float, fill: str, line: str | None = None) -> str:
    line_xml = f'<a:ln><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{_xml_escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{line_xml}</p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>"""


def _pptx_slide_xml(
    index: int,
    total: int,
    slide: dict[str, str],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    brand_kit: dict[str, str] | None = None,
) -> str:
    palette = _deck_palette(design_theme)
    ink = _hex_from_pdf_rgb(palette["ink"])
    muted = _hex_from_pdf_rgb(palette["muted"])
    band = (brand_kit or {}).get("primary") or _hex_from_pdf_rgb(palette["band"])
    soft = _hex_from_pdf_rgb(palette["soft"])
    accent = (brand_kit or {}).get("secondary") or _hex_from_pdf_rgb(palette["accent"])
    brand_name = (brand_kit or {}).get("brand_name") or "MiMi Nox"
    shapes = [
        _pptx_rect(2, "Background", 0, 0, 13.333, 7.5, _hex_from_pdf_rgb(palette["paper"])),
        _pptx_rect(3, "Top Bar", 0, 0, 13.333, 0.16, band),
        _pptx_rect(4, "Proof Panel", 7.75, 1.45, 4.25, 4.35, soft, "D6E3DC"),
        _pptx_textbox(5, "Slide Number", f"{index:02d} / {total:02d}", 0.7, 0.42, 1.2, 0.25, font_size=8, color=muted),
        _pptx_textbox(6, "Deck Profile", f"{brand_name} Deck - {deck_profile}", 9.55, 0.42, 2.9, 0.25, font_size=8, color=muted),
        _pptx_textbox(7, "Title", " ".join(_split_lines(slide["title"], max_chars=42, max_lines=2)), 0.7, 1.05, 6.5, 0.8, font_size=25, color=ink, bold=True),
        _pptx_textbox(8, "Claim", " ".join(_split_lines(slide["claim"], max_chars=72, max_lines=3)), 0.7, 2.05, 6.65, 0.85, font_size=15, color=band, bold=True),
        _pptx_textbox(9, "Body", " ".join(_split_lines(slide["body"], max_chars=86, max_lines=5)), 0.7, 3.0, 6.45, 1.0, font_size=11, color=muted),
        _pptx_textbox(10, "Proof Object", f"Proof Object: {slide.get('proof', 'Proof object')}", 8.12, 1.84, 3.45, 0.35, font_size=10, color=ink, bold=True),
        _pptx_textbox(11, "Evidence Level", f"Evidence: {evidence_level}", 8.12, 2.18, 3.3, 0.25, font_size=8, color=muted),
        _pptx_rect(12, "Visual Object A", 8.35, 2.85, 0.7, 0.7, band),
        _pptx_rect(13, "Visual Object B", 9.35, 3.45, 0.7, 0.7, accent),
        _pptx_rect(14, "Visual Object C", 10.35, 4.05, 0.7, 0.7, band),
        _pptx_textbox(15, "Animation Plan", f"Animation Plan: reveal title, then claim, then proof object ({slide['visual']}).", 0.7, 6.85, 8.1, 0.25, font_size=8, color=ink, bold=True),
    ]
    if source_notes and index == total:
        shapes.append(_pptx_textbox(16, "Source Notes", f"Source Notes: {source_notes}", 0.7, 5.82, 10.8, 0.45, font_size=8, color=muted))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def _write_pitch_deck_pptx(
    path: Path,
    title: str,
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    brand_kit: dict[str, str] | None = None,
) -> None:
    slide_overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, len(slides) + 1)
    )
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>'
        for i in range(1, len(slides) + 1)
    )
    rels = "\n".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, len(slides) + 1)
    )
    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {slide_overrides}
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""
    presentation_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {rels}
</Relationships>"""
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_xml_escape(title)}</dc:title>
  <dc:creator>MiMi Nox</dc:creator>
  <cp:lastModifiedBy>MiMi Nox</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>"""
    app_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>MiMi Nox</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>{len(slides)}</Slides>
</Properties>"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as pptx:
        pptx.writestr("[Content_Types].xml", content_types)
        pptx.writestr("_rels/.rels", root_rels)
        pptx.writestr("docProps/core.xml", core_props)
        pptx.writestr("docProps/app.xml", app_props)
        pptx.writestr("ppt/presentation.xml", presentation)
        pptx.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
        for index, slide in enumerate(slides, 1):
            pptx.writestr(
                f"ppt/slides/slide{index}.xml",
                _pptx_slide_xml(
                    index,
                    len(slides),
                    slide,
                    deck_profile=deck_profile,
                    design_theme=design_theme,
                    source_notes=source_notes,
                    evidence_level=evidence_level,
                    brand_kit=brand_kit,
                ),
            )


def _qa_pptx_deck_file(path: Path) -> dict:
    warnings: list[str] = []
    slides: list[dict] = []
    try:
        with zipfile.ZipFile(path) as pptx:
            names = set(pptx.namelist())
            slide_names = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
            if not slide_names:
                warnings.append("No slide XML files found.")
            for index, slide_name in enumerate(slide_names, 1):
                xml = pptx.read(slide_name).decode("utf-8", errors="replace")
                texts = [html.unescape(t).strip() for t in re.findall(r"<a:t>(.*?)</a:t>", xml)]
                texts = [text for text in texts if text]
                text_chars = sum(len(text) for text in texts)
                editable_runs = xml.count("<a:t>")
                proof_present = "Proof Object:" in xml
                if editable_runs < 4:
                    warnings.append(f"Slide {index} has low editable text density.")
                if text_chars > 900:
                    warnings.append(f"Slide {index} is text-heavy.")
                if not proof_present:
                    warnings.append(f"Slide {index} is missing a proof object.")
                slides.append({
                    "slide": index,
                    "editable_text_runs": editable_runs,
                    "text_chars": text_chars,
                    "proof_object": proof_present,
                    "preview_text": texts[:5],
                })
    except Exception as exc:
        warnings.append(f"PPTX QA failed: {exc}")
    return {
        "artifact_type": "pptx_visual_qa",
        "path": str(path),
        "slide_count": len(slides),
        "status": "passed" if not warnings else "warning",
        "slides": slides,
        "warnings": warnings,
        "contact_sheet": str(path.with_suffix(".contact-sheet.html")),
    }


def _render_pptx_contact_sheet(path: Path, qa: dict) -> str:
    cards = []
    for slide in qa.get("slides", []):
        text = " ".join(slide.get("preview_text", []))
        proof = "Proof OK" if slide.get("proof_object") else "Missing proof"
        cards.append(
            "<article>"
            f"<span>Slide {slide.get('slide')}</span>"
            f"<h2>{html.escape(text[:150] or 'No extractable text')}</h2>"
            f"<p>{html.escape(proof)} - {slide.get('editable_text_runs', 0)} editable text runs - {slide.get('text_chars', 0)} chars</p>"
            "</article>"
        )
    warnings = "".join(f"<li>{html.escape(str(warning))}</li>" for warning in qa.get("warnings", []))
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MiMi Nox PPTX Contact Sheet</title>
<style>
body{{margin:0;background:#f8faf9;color:#101820;font-family:Arial,sans-serif;padding:32px}}
header{{display:flex;justify-content:space-between;gap:24px;align-items:end;border-bottom:4px solid #101820;padding-bottom:18px;margin-bottom:24px}}
h1{{margin:0;font-size:30px}} small{{color:#53606f}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}
article{{background:white;border:1px solid #d6e3dc;border-left:6px solid #16a34a;padding:16px;min-height:150px}}
span{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#53606f;font-weight:700}}
h2{{font-size:17px;line-height:1.25;margin:10px 0;color:#101820}}
p,li{{font-size:13px;color:#53606f;line-height:1.4}}
.warnings{{margin-top:26px;background:#fff7ed;border-left:6px solid #d97706;padding:14px 18px}}
</style>
<header><div><h1>PPTX Contact Sheet</h1><small>{html.escape(str(path))}</small></div><b>{html.escape(str(qa.get('status', 'unknown')))}</b></header>
<section class="grid">{''.join(cards)}</section>
<section class="warnings"><b>Warnings</b><ul>{warnings or '<li>None</li>'}</ul></section>
</html>"""


def _deck_palette(design_theme: str) -> dict[str, str]:
    themes = {
        "evergreen": {
            "paper": "0.984 0.988 0.984",
            "band": "0.086 0.639 0.290",
            "soft": "0.928 0.972 0.941",
            "ink": "0.06 0.09 0.13",
            "muted": "0.32 0.38 0.44",
            "accent": "0.035 0.569 0.698",
            "warn": "0.850 0.467 0.024",
        },
        "executive": {
            "paper": "0.980 0.980 0.965",
            "band": "0.055 0.090 0.140",
            "soft": "0.930 0.940 0.930",
            "ink": "0.055 0.090 0.140",
            "muted": "0.330 0.360 0.390",
            "accent": "0.086 0.639 0.290",
            "warn": "0.780 0.350 0.030",
        },
        "studio": {
            "paper": "0.990 0.985 0.972",
            "band": "0.035 0.569 0.698",
            "soft": "0.925 0.965 0.972",
            "ink": "0.080 0.090 0.110",
            "muted": "0.320 0.360 0.410",
            "accent": "0.086 0.639 0.290",
            "warn": "0.820 0.420 0.050",
        },
    }
    return themes.get((design_theme or "").lower(), themes["evergreen"])


def _visual_commands(kind: str, x: int, y: int, w: int, h: int, palette: dict[str, str]) -> list[str]:
    accent = palette["accent"]
    band = palette["band"]
    warn = palette["warn"]
    inner_x = x + 34
    inner_y = y + 46
    inner_w = w - 68
    inner_h = h - 108
    if kind in {"trend", "market", "score"}:
        points = [
            (inner_x, inner_y + 8),
            (inner_x + inner_w * 0.28, inner_y + inner_h * 0.35),
            (inner_x + inner_w * 0.58, inner_y + inner_h * 0.68),
            (inner_x + inner_w, inner_y + inner_h),
        ]
        line = f"{band} RG 3 w {points[0][0]:.1f} {points[0][1]:.1f} m " + " ".join(
            f"{px:.1f} {py:.1f} l" for px, py in points[1:]
        ) + " S\n"
        dots = " ".join(f"{band} rg {px - 4:.1f} {py - 4:.1f} 8 8 re f" for px, py in points)
        return [
            line,
            f"{dots}\n",
            f"{accent} RG 1.3 w {inner_x:.1f} {inner_y:.1f} m {inner_x + inner_w:.1f} {inner_y:.1f} l S\n",
        ]
    if kind in {"roadmap", "system"}:
        commands = []
        for row, label in enumerate(("Discover", "Build", "Validate", "Scale")):
            yy = y + 146 - row * 38
            commands.append(f"1 1 1 rg {x + 34} {yy} 172 24 re f {band} RG {x + 34} {yy} 172 24 re S\n")
            commands.append(_pdf_text(label, x + 49, yy + 8, 9, "F2", palette["ink"]))
        return commands
    if kind in {"pain", "risk"}:
        commands = []
        for row, label in enumerate(("Input", "Tool", "Artifact")):
            yy = y + 142 - row * 48
            commands.append(f"{warn} RG 1.6 w {x + 38} {yy} 152 30 re S\n")
            commands.append(_pdf_text(label, x + 80, yy + 10, 10, "F2", palette["ink"]))
        return commands
    if kind == "market":
        return [f"{band} RG 2 w {inner_x:.1f} {inner_y:.1f} {inner_w:.1f} {inner_h:.1f} re S\n"]
    return [
        f"{band} RG 2.2 w {inner_x + 36:.1f} {inner_y + 34:.1f} 86 86 re S\n",
        f"{accent} RG 2 w {inner_x + 14:.1f} {inner_y + 12:.1f} m {inner_x + inner_w - 12:.1f} {inner_y + inner_h - 12:.1f} l S\n",
        f"{band} rg {inner_x + 76:.1f} {inner_y + 76:.1f} 28 28 re f\n",
    ]


def _write_pitch_deck_pdf(
    path: Path,
    title: str,
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
) -> None:
    width, height = 720, 405
    palette = _deck_palette(design_theme)
    page_streams: list[str] = []
    for index, slide in enumerate(slides, 1):
        visual_x, visual_y, visual_w, visual_h = 438, 78, 210, 235
        stream = [
            f"{palette['paper']} rg 0 0 720 405 re f\n",
            f"{palette['band']} rg 0 393 720 12 re f\n",
            f"{palette['soft']} rg {visual_x} {visual_y} {visual_w} {visual_h} re f\n",
            f"0.839 0.890 0.863 RG {visual_x} {visual_y} {visual_w} {visual_h} re S\n",
            _pdf_text(f"{index:02d} / {len(slides):02d}", 46, 370, 8, "F1", palette["muted"]),
            _pdf_text(f"MiMi Nox Deck - {deck_profile}", 520, 370, 8, "F1", palette["muted"]),
            _pdf_text(f"Evidence: {evidence_level}", visual_x + 24, 268, 8, "F1", palette["muted"]),
        ]
        y = 326
        for line in _split_lines(slide["title"], max_chars=34, max_lines=2):
            stream.append(_pdf_text(line, 48, y, 25, "F2", palette["ink"]))
            y -= 29
        y -= 5
        for line in _split_lines(slide["claim"], max_chars=46, max_lines=4):
            stream.append(_pdf_text(line, 48, y, 15, "F2", palette["band"]))
            y -= 21
        y -= 8
        for line in _split_lines(slide["body"], max_chars=58, max_lines=5):
            stream.append(_pdf_text(line, 48, y, 11, "F1", palette["muted"]))
            y -= 17
        stream.append(_pdf_text(f"Proof Object: {slide.get('proof', 'Proof object')}", visual_x + 24, 286, 10, "F2", palette["ink"]))
        stream.extend(_visual_commands(slide.get("visual", "custom"), visual_x, visual_y, visual_w, visual_h, palette))
        stream.append(_pdf_text(f"Animation Plan: reveal title, then claim, then proof object ({slide['visual']}).", 48, 34, 8, "F2", palette["ink"]))
        if source_notes and index == len(slides):
            for note_index, line in enumerate(_split_lines(f"Source Notes: {source_notes}", max_chars=82, max_lines=3)):
                stream.append(_pdf_text(line, 48, 64 + note_index * 12, 8, "F1", palette["muted"]))
        page_streams.append("".join(stream))

    objects: list[bytes] = []
    kids = []
    page_obj_start = 4
    for i, stream in enumerate(page_streams):
        page_obj = page_obj_start + i * 2
        content_obj = page_obj + 1
        kids.append(f"{page_obj} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 3 0 R /F2 {3 + len(page_streams) * 2 + 1} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>".encode("latin-1", "replace")
        )
        stream_bytes = stream.encode("latin-1", "replace")
        objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1") + stream_bytes + b"endstream")

    font_bold_obj = 3 + len(page_streams) * 2 + 1
    base_objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(page_streams)} >>".encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    all_objects = base_objects + objects + [b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
    if len(all_objects) != font_bold_obj:
        raise ValueError("PDF object numbering mismatch")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(all_objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("latin-1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(all_objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.extend(
        f"trailer << /Size {len(all_objects) + 1} /Root 1 0 R /Info << /Title ({_pdf_escape(title)}) /Author (MiMi Nox) >> >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("latin-1", "replace")
    )
    path.write_bytes(output)


def _qa_pitch_deck_render_file(path: Path) -> dict:
    warnings: list[str] = []
    checks = {
        "extractable_text": False,
        "slide_count_at_least_8": False,
        "no_text_in_visual_column": True,
        "visuals_bounded": True,
        "has_real_pdf_pages": False,
    }
    overflow_words: list[dict[str, object]] = []
    allowed_visual_words = {
        "Proof", "Object:", "Evidence:", "assumptions", "user-provided", "sources", "mixed",
        "Input", "Tool", "Artifact", "Discover", "Build", "Validate", "Scale",
    }
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            checks["has_real_pdf_pages"] = len(pdf.pages) > 0
            checks["slide_count_at_least_8"] = len(pdf.pages) >= 8
            all_text = []
            for page_index, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                all_text.append(text)
                words = page.extract_words() or []
                ignored_panel_tops = {
                    round(float(word.get("top", 0)), 1)
                    for word in words
                    if str(word.get("text", "")) in {"Proof", "Object:", "Evidence:"}
                }
                for word in words:
                    word_text = str(word.get("text", ""))
                    top = float(word.get("top", 0))
                    x0 = float(word.get("x0", 0))
                    if word_text in allowed_visual_words:
                        continue
                    if any(abs(top - ignored_top) <= 2.0 for ignored_top in ignored_panel_tops):
                        continue
                    if top < 86 or top > 330:
                        continue
                    if x0 >= 418:
                        overflow_words.append({
                            "page": page_index,
                            "text": word_text,
                            "x0": round(x0, 1),
                            "top": round(top, 1),
                        })
            checks["extractable_text"] = bool(" ".join(all_text).strip())
    except Exception as exc:
        warnings.append(f"Render text-position QA failed: {exc}")

    raw = path.read_text(encoding="latin-1", errors="replace") if path.exists() else ""
    rects = re.findall(r"([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+re", raw)
    oversized_visual_rects = [
        (float(x), float(y), float(w), float(h))
        for x, y, w, h in rects
        if float(x) >= 400 and (float(w) > 240 or float(h) > 250)
    ]
    if overflow_words:
        checks["no_text_in_visual_column"] = False
        warnings.append(f"Main narrative text enters the visual column: {overflow_words[:6]}")
    if oversized_visual_rects:
        checks["visuals_bounded"] = False
        warnings.append(f"Visual commands exceed right-panel bounds: {oversized_visual_rects[:4]}")
    if not checks["extractable_text"]:
        warnings.append("Rendered deck has no extractable text.")
    if not checks["slide_count_at_least_8"]:
        warnings.append("Rendered deck has fewer than 8 slides.")
    if not checks["has_real_pdf_pages"]:
        warnings.append("Rendered deck has no readable PDF pages.")

    return {
        "artifact_type": "pitch_deck_render_qa",
        "path": str(path),
        "status": "passed" if all(checks.values()) and not warnings else "failed",
        "checks": checks,
        "warnings": warnings,
        "overflow_words": overflow_words[:20],
    }


def _deck_text(slides: list[dict[str, str]]) -> str:
    return " ".join(" ".join(str(value) for value in slide.values()) for slide in slides).lower()


def _score_pitch_deck(
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    enterprise_grade: bool,
    render_qa: dict | None = None,
) -> dict:
    deck_text = _deck_text(slides)
    amateur_terms_found = sorted(
        term
        for term in AMATEUR_DECK_TERMS
        if re.search(rf"\b{re.escape(term)}\b", deck_text)
    )
    executive_density_ok = all(
        len(slide.get("claim", "")) <= 180 and len(slide.get("body", "")) <= 360
        for slide in slides
    )
    checks = {
        "slide_count_at_least_8": len(slides) >= 8,
        "claim_on_every_slide": all(len(slide.get("claim", "").strip()) >= 14 for slide in slides),
        "proof_object_on_every_slide": all(len(slide.get("proof", "").strip()) >= 5 for slide in slides),
        "no_placeholders": not any(
            token in " ".join(str(value).lower() for value in slide.values())
            for slide in slides
            for token in ("tbd", "todo", "placeholder", "lorem")
        ),
        "visual_variety": len({slide.get("visual", "custom") for slide in slides}) >= min(5, len(slides)),
        "source_notes_or_assumptions_visible": bool(source_notes.strip()),
        "no_amateur_language": not amateur_terms_found,
        "enterprise_profile_valid": deck_profile in ENTERPRISE_DECK_PROFILES,
        "enterprise_theme_valid": design_theme in ENTERPRISE_DESIGN_THEMES,
        "executive_density": executive_density_ok,
        "evidence_level_declared": evidence_level in {"sources", "mixed", "assumptions", "user-provided"},
        "render_quality_passed": (render_qa or {}).get("status") == "passed",
    }
    passed = sum(1 for ok in checks.values() if ok)
    score = round((passed / len(checks)) * 100)
    warnings = []
    if not checks["visual_variety"]:
        warnings.append("Deck uses too few distinct visual proof objects.")
    if amateur_terms_found:
        warnings.append(f"Deck contains amateur wording: {', '.join(amateur_terms_found[:5])}.")
    if evidence_level == "assumptions":
        warnings.append("No external evidence supplied; deck is enterprise-formatted but assumption-led.")
    if render_qa and render_qa.get("status") != "passed":
        warnings.extend(str(warning) for warning in render_qa.get("warnings", [])[:4])
    minimum_score = 92 if enterprise_grade else 85
    status = "passed" if score >= minimum_score and not amateur_terms_found else "failed"
    return {
        "artifact_type": "pitch_deck",
        "quality_score": score,
        "minimum_score": minimum_score,
        "enterprise_grade": enterprise_grade,
        "status": status,
        "deck_profile": deck_profile,
        "design_theme": design_theme,
        "evidence_level": evidence_level,
        "slide_count": len(slides),
        "checks": checks,
        "warnings": warnings,
    }


def _build_pitch_deck_manifest(
    *,
    title: str,
    slides: list[dict[str, str]],
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    enterprise_grade: bool,
    template_info: dict | None = None,
    brand_kit: dict | None = None,
) -> dict:
    return {
        "title": title,
        "artifact_type": "pitch_deck",
        "enterprise_grade": enterprise_grade,
        "deck_profile": deck_profile,
        "design_theme": design_theme,
        "evidence_level": evidence_level,
        "source_notes": source_notes,
        "template": template_info or {},
        "brand_kit": brand_kit or {},
        "claim_spine": [
            {
                "slide": index,
                "title": slide.get("title", ""),
                "claim": slide.get("claim", ""),
                "proof_object": slide.get("proof", ""),
                "visual": slide.get("visual", ""),
            }
            for index, slide in enumerate(slides, 1)
        ],
        "review_gates": [
            "one_claim_per_slide",
            "proof_object_per_slide",
            "source_notes_or_assumptions",
            "anti_amateur_language",
            "executive_density",
            "visual_variety",
            "extractable_pdf_text",
        ],
    }


def _render_pitch_deck_preview(topic: str, slides: list[dict[str, str]], score: dict | None = None) -> str:
    cards = []
    for index, slide in enumerate(slides, 1):
        cards.append(
            "<section class=\"slide\">"
            f"<span>{index:02d}</span>"
            f"<h1>{html.escape(slide['title'])}</h1>"
            f"<h2>{html.escape(slide['claim'])}</h2>"
            f"<p>{html.escape(slide['body'])}</p>"
            f"<strong>{html.escape(slide.get('proof', 'Proof object'))}</strong>"
            f"<small>Animation: title -> claim -> visual proof object</small>"
            "</section>"
        )
    score_html = ""
    if score:
        score_html = (
            "<aside class=\"score\">"
            f"<b>Quality score {score.get('quality_score', 0)}/100</b>"
            f"<span>{html.escape(score.get('deck_profile', 'deck'))} - {html.escape(score.get('design_theme', 'theme'))}</span>"
            "</aside>"
        )
    return """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - MiMi Nox Deck Preview</title>
<style>
body{{margin:0;background:#101820;color:#101820;font-family:Inter,Arial,sans-serif;overflow-x:hidden}}
.slide{{min-height:100vh;display:grid;align-content:center;gap:18px;padding:8vw 12vw;background:#fbfcfb;border-bottom:10px solid #16a34a;animation:enter .72s ease both}}
.slide:nth-child(even){{background:#eef8f1}}
span{{color:#16a34a;font-weight:800;letter-spacing:.08em}}
h1{{font-size:clamp(38px,7vw,82px);line-height:.95;margin:0;max-width:980px}}
h2{{font-size:clamp(22px,3vw,38px);line-height:1.08;color:#16a34a;margin:0;max-width:920px}}
p{{font-size:clamp(17px,2vw,24px);line-height:1.35;color:#53606f;max-width:820px;margin:0}}
strong{{font-size:clamp(16px,2vw,22px);color:#101820}}
small{{font-size:14px;color:#53606f;text-transform:uppercase;letter-spacing:.08em}}
.score{{position:fixed;right:18px;top:18px;z-index:5;display:grid;gap:4px;background:#101820;color:white;padding:12px 14px;border-left:4px solid #16a34a;font-size:13px}}
.score span{{color:#b7c4bd;font-weight:600;letter-spacing:0}}
@keyframes enter{{from{{opacity:0;transform:translateY(28px) scale(.98)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
</style>
{score_html}
{cards}
</html>""".format(title=html.escape(topic or "Pitch Deck"), score_html=score_html, cards="\n".join(cards))


# ===========================================================================
# Tool: create_svg  (SVG als String → Browser-Render)
# ===========================================================================

async def create_svg(
    svg_code: str,
    filename: str = "nox_grafik.svg",
) -> str:
    """
    Speichert SVG-Code als Datei und gibt den Pfad zurück.
    Gemma4 schreibt den SVG-Code selbst; dieses Tool speichert ihn.

    Sicherheit:
      - Entfernt <script> Tags (XSS-Prävention)
      - Entfernt <foreignObject> (HTML-Injection)
      - Entfernt on*-Event-Handler (onclick, onload etc.)
      - Entfernt javascript: URLs

    Args:
        svg_code: Vollständiger SVG-XML-Code
        filename: Dateiname (in ~/Downloads gespeichert)
    """
    import re

    try:
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / filename

        # ── XSS-Sanitizer ──────────────────────────────────
        # 1) <script>...</script> entfernen
        svg_code = re.sub(
            r"<script[^>]*>.*?</script>", "", svg_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        # 2) <foreignObject>...</foreignObject> entfernen
        svg_code = re.sub(
            r"<foreignObject[^>]*>.*?</foreignObject>", "", svg_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        # 3) on*-Event-Handler entfernen (onclick, onload, onerror etc.)
        svg_code = re.sub(
            r'\s+on\w+\s*=\s*"[^"]*"', "", svg_code,
            flags=re.IGNORECASE
        )
        svg_code = re.sub(
            r"\s+on\w+\s*=\s*'[^']*'", "", svg_code,
            flags=re.IGNORECASE
        )
        # 4) javascript: URLs entfernen
        svg_code = re.sub(
            r'href\s*=\s*"javascript:[^"]*"', 'href="#"', svg_code,
            flags=re.IGNORECASE
        )

        # Sicherstellen dass es gültiges SVG ist
        if "<svg" not in svg_code:
            svg_code = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">\n{svg_code}\n</svg>'

        out.write_text(svg_code, encoding="utf-8")
        return f"SVG_FILE:{out}"

    except Exception as e:
        return f"[svg-Fehler: {e}]"

async def manage_tasks(action: str, title: str = None, task_id: str = None, status: str = None, project: str = None) -> str:
    from core.tasks import task_manager
    if action == "add":
        if not title:
            return "[Error: title required for add]"
        tid = task_manager.add_task(title=title, project=project)
        return f"Task erfolgreich hinzugefügt. ID: {tid}"
    elif action == "update":
        if not task_id:
            return "[Error: task_id required for update]"
        found = task_manager.update_task(task_id, status=status, title=title, project=project)
        return f"Task {task_id} erfolgreich aktualisiert." if found else f"[Error: Task {task_id} nicht gefunden]"
    elif action == "delete":
        if not task_id:
            return "[Error: task_id required for delete]"
        found = task_manager.delete_task(task_id)
        return f"Task {task_id} erfolgreich gelöscht." if found else f"[Error: Task {task_id} nicht gefunden]"
    elif action == "list":
        tasks = task_manager.get_tasks()
        if not tasks:
            return "Keine Aufgaben vorhanden."
        return "\n".join(f"- [{t['status']}] {t['title']} (ID: {t['id']})" for t in tasks)
    return f"[Error: unknown action '{action}']"

TOOL_MAP: dict[str, object] = {
    "manage_tasks":     manage_tasks,
    "web_search":       web_search,
    "file_search":      file_search,
    "discover_projects": discover_projects,
    "analyze_project":  analyze_project,
    "create_source_notebook": create_source_notebook,
    "query_source_notebook": query_source_notebook,
    "export_source_brief": export_source_brief,
    "read_file":        read_file,
    "list_directory":   list_directory,
    "get_datetime":     get_datetime,
    "run_shell":        run_shell,
    "load_workspace":   load_workspace,
    "analyze_image":    analyze_image,
    "vision_click":     _vision_click_wrapper,
    "vision_type":      _vision_type_wrapper,
    "take_screenshot":  take_screenshot,
    "browser_go":         browser_go,
    "browser_screenshot": browser_screenshot,
    "browser_click":      browser_click,
    "browser_type":       browser_type,
    "browser_press":      browser_press,
    "generate_chart":     generate_chart,
    "create_pdf":         create_pdf,
    "create_pitch_deck":  create_pitch_deck,
    "create_pptx_deck":   create_pptx_deck,
    "inspect_pptx_template": inspect_pptx_template,
    "edit_pptx_template": edit_pptx_template,
    "qa_pptx_deck":      qa_pptx_deck,
    "create_svg":         create_svg,
}


async def execute_tool(name: str, arguments: dict) -> str:
    """
    Führt ein Tool per Name aus und gibt das Ergebnis als String zurück.
    Fehler werden abgefangen und als String zurückgegeben — kein Crash.
    """
    func = TOOL_MAP.get(name)
    if func is None:
        return f"[Tool '{name}' nicht gefunden]"

    try:
        result = await func(**arguments)  # type: ignore[operator]
        if isinstance(result, list):
            return "\n".join(str(r) for r in result)
        return str(result)
    except ShellConfirmationRequired:
        raise  # App muss das handhaben
    except Exception as exc:
        if exc.__class__.__name__ == "SandboxConfirmationRequired":
            raise  # Bubble up to router/tui to intercept
        return f"[Tool-Fehler '{name}': {exc}]"


# ===========================================================================
# Ollama Tool Schemas
# ===========================================================================

def get_tool_schemas() -> list[dict]:
    """
    Gibt alle Tool-Definitionen als Ollama-kompatible JSON-Schemas zurück.
    Wird an ollama.chat(tools=...) übergeben.
    """
    global _TOOL_SCHEMA_CACHE
    now = time.monotonic()
    if _TOOL_SCHEMA_CACHE and now - _TOOL_SCHEMA_CACHE[0] < TOOL_SCHEMA_CACHE_TTL_SECONDS:
        return _TOOL_SCHEMA_CACHE[1]

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "manage_tasks",
                "description": (
                    "Verwaltet persönliche Aufgaben und To-Do Listen des Nutzers. "
                    "Aktionen: 'add' (neu), 'update' (ändern/abschließen), 'delete' (löschen), 'list' (alle zeigen)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add", "update", "delete", "list"]},
                        "title": {"type": "string", "description": "Titel der Aufgabe (für add/update)"},
                        "task_id": {"type": "string", "description": "ID der Aufgabe (für update/delete)"},
                        "status": {"type": "string", "enum": ["open", "done", "in_progress"], "description": "Neuer Status (für update)"},
                        "project": {"type": "string", "description": "Projektzugehörigkeit (optional)"}
                    },
                    "required": ["action"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_go",
                "description": (
                    "Öffnet einen Headless-Browser und navigiert zu einer URL. "
                    "Nutze dieses Tool nur wenn du eine Webseite visuell inspizieren, Formulare ausfüllen oder interagieren musst. "
                    "Für schnelle Internet-Recherchen nutze stattdessen web_search (DuckDuckGo). "
                    "Wenn du auf Buttons (z.B. Cookie Banner) klicken musst, nutze nachfolgend browser_click()."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL (z.B. https://wikipedia.de)"}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": (
                    "Liefert ein genaues Foto/Screenshot des aktuell aktiven Headless-Browsers zurück. "
                    "Nutze dies, wenn du dir die Webseite ansehen willst (z.B. um Cookie-Banner, Captchas oder Layouts "
                    "zu erkennen), da der KI dieses Bild im Chat angezeigt wird."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": (
                    "Sucht mittels Llama-Vision auf dem Headless-Browser nach einem beschriebenen Ziel und führt dort einen Mausklick aus. "
                    "Pflicht: Du musst vorher einmalig browser_screenshot oder browser_go aufgerufen haben. "
                    "Ideal für Cookie-Banner, Links oder Menüs."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_description": {"type": "string", "description": "Was genau geklickt werden soll (z.B. 'Der dicke grüne Akzeptieren-Button')"}
                    },
                    "required": ["target_description"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_type",
                "description": (
                    "Tippt einen Text im Headless-Browser wie eine echte Tastatur ein. "
                    "Muss normalerweise nach einem vorausgehenden browser_click in ein Suchfeld ausgeführt werden."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "Zu tippender Text"}
                    },
                    "required": ["text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_press",
                "description": "Drückt eine isolierte Taste im Headless-Browser (z.B. 'Enter', 'Escape').",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Tastenname (z.B. 'Enter')"}
                    },
                    "required": ["key"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": (
                    "Primäres Internet-Recherche-Tool. Durchsucht das Internet via DuckDuckGo und liefert echte, "
                    "aktuelle Ergebnisse mit Titel, URL und Inhaltsauszug. Nutze dieses Tool IMMER wenn du "
                    "aktuelle Informationen, Fakten, Nachrichten oder Dokumentation aus dem Internet benötigst."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Die Suchanfrage z.B. 'Python asyncio tutorial 2026'",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Anzahl der Ergebnisse (Standard: 5, max: 10)",
                            "default": 5,
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_search",
                "description": (
                    "Durchsucht den Computer nach Dateien (macOS: Spotlight, Linux: find). "
                    "Nutze dieses Tool wenn der User eine Datei auf seinem Computer sucht."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Dateiname oder Suchbegriff z.B. 'Rechnung 2026' oder 'resume.pdf'",
                        },
                        "path": {
                            "type": "string",
                            "description": "Optionaler Startpfad für die Suche z.B. '~/Desktop'",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": (
                    "Reads the contents of a file and returns its text. "
                    "Supports plain text, code, Markdown, and PDF files. "
                    "Use this tool when the user wants to read, analyze, summarize, or explain a file. "
                    "For PDF files the text is automatically extracted page by page. "
                    "Security: Only files in the home directory, Desktop, Documents, Downloads are allowed."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absolute or ~-relative path, e.g. '~/Desktop/contract.pdf'",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "discover_projects",
                "description": (
                    "Findet lokale Code-Projekte auf dem Mac in erlaubten User-Verzeichnissen "
                    "(Developer, Projects, Documents, Desktop, Downloads), bewertet sie nach Marker-Dateien "
                    "und liefert Stack, Pfad und Score. Nutze dies wenn der User sagt: finde ein Projekt, Repo, "
                    "Workspace oder Codebase auf meinem Mac."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Optionaler Suchbegriff, z.B. Projektname, Repo-Name oder Stack.",
                        },
                        "root": {
                            "type": "string",
                            "description": "Optionaler Startordner, z.B. '~/Developer' oder '~/Documents'.",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximale Anzahl Projekte, Standard 10.",
                            "default": 10,
                        },
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_project",
                "description": (
                    "Analysiert einen lokalen Projektordner top-down: Stack, Marker-Dateien, Testbefehl, "
                    "Risiken und nächste Schritte. Nutze dies für Ist-Zustand-Analysen, Codebase-Reviews "
                    "und wenn der User ein gefundenes Projekt verstehen oder verbessern will."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absoluter oder ~-relativer Pfad zum Projektordner.",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "create_source_notebook",
                "description": (
                    "Erstellt ein lokales NotebookLM-artiges Quellen-Notebook aus Dateien oder Ordnern. "
                    "Indexiert Text/PDF/Code in zitierbare Evidence-Chunks und speichert ein lokales Manifest. "
                    "Nutze dies wenn der User mit Dokumenten, Quellen, Wissen, NotebookLM, Source Grounding, "
                    "Studiennotizen oder belastbaren Zitaten arbeiten will."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "paths": {
                            "type": ["array", "string"],
                            "items": {"type": "string"},
                            "description": "Eine oder mehrere lokale Dateien/Ordner, z.B. ['~/Documents/report.pdf', '~/Documents/project'].",
                        },
                        "title": {"type": "string", "description": "Notebook-Titel."},
                        "notebook_id": {"type": "string", "description": "Optionaler stabiler Dateiname/Slug."},
                        "extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional erlaubte Endungen, z.B. ['.pdf', '.md', '.py'].",
                        },
                    },
                    "required": ["paths"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "query_source_notebook",
                "description": (
                    "Fragt ein lokales Quellen-Notebook ab und liefert eine conservative, quellengebundene Antwort "
                    "mit Evidence-Chunks im Format [S001-C001]. Nutze dies nach create_source_notebook oder wenn "
                    "ein bestehendes Notebook-Manifest angegeben wurde."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "notebook_path": {"type": "string", "description": "Pfad zur SOURCE_NOTEBOOK_FILE JSON."},
                        "question": {"type": "string", "description": "Frage, die nur aus den indexierten Quellen beantwortet werden soll."},
                        "max_chunks": {"type": "integer", "description": "Maximale Evidence-Chunks, Standard 6.", "default": 6},
                    },
                    "required": ["notebook_path", "question"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "export_source_brief",
                "description": (
                    "Exportiert ein hochwertiges Markdown-Briefing aus einem lokalen Quellen-Notebook: "
                    "Executive Summary, Evidence Register und Source Manifest. Nutze dies für belastbare "
                    "Reports, Study Guides, Projektbriefings und Quellen-Dokumentation."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "notebook_path": {"type": "string"},
                        "question": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                    "required": ["notebook_path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_directory",
                "description": (
                    "Listet den Inhalt eines Verzeichnisses auf. "
                    "Nutze dieses Tool wenn der User wissen möchte was in einem Ordner ist."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Pfad zum Verzeichnis z.B. '~/Desktop' oder '~/Documents'",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_datetime",
                "description": (
                    "Gibt das aktuelle Datum und die Uhrzeit auf Deutsch zurück. "
                    "Nutze dieses Tool wenn der User nach Datum, Uhrzeit oder Wochentag fragt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_shell",
                "description": (
                    "Schlägt einen Terminal-Befehl vor der der User ausführen kann. "
                    "WICHTIG: Der Befehl wird NICHT automatisch ausgeführt. "
                    "Der User muss explizit zustimmen. "
                    "Nutze dieses Tool für git, docker, npm, oder andere CLI-Befehle."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Der Terminal-Befehl z.B. 'git status' oder 'npm install'",
                        },
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "load_workspace",
                "description": (
                    "Liest rekursiv alle Dateien eines Verzeichnisses (Workspace). "
                    "Nutze dieses Tool wenn der User ein ganzes Projekt analysieren, "
                    "verstehen oder reviewen möchte. "
                    "Ideal für Code-Reviews, Projekt-Übersichten und Dokumentations-Aufgaben."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Pfad zum Verzeichnis z.B. '~/Desktop/mein-projekt'",
                        },
                        "extensions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Nur diese Dateiendungen laden z.B. ['.py', '.md']. Leer = alle.",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "analyze_image",
                "description": (
                    "Analysiert ein Bild mittels KI-Vision (OCR, Beschreibung, Erkennung). "
                    "Nutze dieses Tool wenn der User ein Bild, Screenshot, Foto oder Dokument "
                    "zeigen, beschreiben, auslesen oder erklären lassen möchte. "
                    "Unterstützt: PNG, JPG, WebP, GIF, BMP."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Pfad zum Bild z.B. '~/Desktop/screenshot.png'",
                        },
                        "question": {
                            "type": "string",
                            "description": "Frage zum Bild z.B. 'Was steht auf dieser Rechnung?' oder 'Beschreibe diesen Screenshot'",
                        },
                    },
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "vision_click",
                "description": (
                    "Nutzt visuelle Bildschirmanalyse um ein UI Element auf dem primären Desktop zu finden "
                    "und klickt physisch mit der Maus darauf. Nutze dieses Tool wenn du GUI Applikationen "
                    "oder den Browser des Users fernsteuern sollst. (Es dauert kurz für die Analyse)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_description": {
                            "type": "string",
                            "description": "Was soll geklickt werden? z.B. 'Der rote Speichern Button oben rechts' oder 'Das Chrome-Icon im Dock'. So präzise wie möglich.",
                        },
                    },
                    "required": ["target_description"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "vision_type",
                "description": (
                    "Tippt eine Zeichenkette in das aktuell fokussierte Eingabefeld auf dem Bildschirm des Users. "
                    "Oft gepaart mit einem vorherigen vision_click, um ein Suchfeld zu fokussieren."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Der exakte Text, der eingetippt werden soll.",
                        },
                        "press_enter": {
                            "type": "boolean",
                            "description": "Soll nach dem Tippen die Enter-Taste gedrückt werden? (Standard: false)",
                            "default": False,
                        },
                    },
                    "required": ["text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "take_screenshot",
                "description": (
                    "Erstellt einen Screenshot/Foto vom lokalen Bildschirm des Computers (dem Host Mac). "
                    "Nutze dieses Tool IMMER wenn der User dich bittet etwas vom Bildschirm zu zeigen, 'mach einen Screenshot' sagt, "
                    "oder wissen möchte 'was siehst du gerade'. Es liefert das Bild inline im Chat zurück."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "generate_chart",
                "description": (
                    "Erstellt einen Daten-Chart (bar/line/pie) als PNG-Bild im MiMiNox-Design. "
                    "Nutze dies wenn der User Daten visualisieren will. Bild erscheint automatisch im Chat."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "chart_type": {"type": "string", "enum": ["bar","line","pie"]},
                        "title":      {"type": "string"},
                        "labels":     {"type": "array", "items": {"type": "string"}},
                        "values":     {"type": "array", "items": {"type": "number"}},
                        "xlabel":     {"type": "string"},
                        "ylabel":     {"type": "string"},
                    },
                    "required": ["chart_type","title","labels","values"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_pdf",
                "description": (
                    "Erstellt ein quality-checked PDF-Dokument aus Markdown-ähnlichem Text "
                    "und speichert es in ~/Downloads. Nutze dies für Executive Summary, "
                    "strukturierte Berichte, Quellenhinweise, Anhänge und hochwertige Zusammenfassungen."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title":    {"type": "string"},
                        "content":  {"type": "string"},
                        "filename": {"type": "string"},
                        "template": {"type": "string", "enum": ["report", "brief", "analysis", "checklist"]},
                    },
                    "required": ["title","content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_pitch_deck",
                "description": (
                    "Erstellt ein high-end 16:9 Pitchdeck als quality-checked PDF-Slides "
                    "plus optionaler animierter HTML-Preview in ~/Downloads. Nutze dies fuer "
                    "Investorendecks, Sales Decks, Produkt-Pitches und praesentationstaugliche Slides."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "audience": {"type": "string"},
                        "thesis": {"type": "string"},
                        "slides": {
                            "type": ["array", "string", "null"],
                            "description": "Optional: Slide-Outline als Liste von {title, claim, body, visual} oder Markdown-Abschnitte.",
                        },
                        "filename": {"type": "string"},
                        "include_animation_preview": {"type": "boolean"},
                        "deck_profile": {
                            "type": "string",
                            "enum": ["product-platform", "engineering-platform", "strategy-leadership", "gtm-growth", "finance-ir", "consumer-retail"],
                        },
                        "design_theme": {
                            "type": "string",
                            "enum": ["evergreen", "executive", "studio"],
                        },
                        "source_notes": {
                            "type": "string",
                            "description": "What the deck is based on: user-provided facts, files, assumptions, or missing evidence.",
                        },
                        "evidence_level": {
                            "type": "string",
                            "enum": ["sources", "mixed", "assumptions", "user-provided"],
                            "description": "How strongly the deck is grounded in evidence.",
                        },
                        "enterprise_grade": {
                            "type": "boolean",
                            "description": "When true, applies Fortune-500/board-level scoring and anti-amateur constraints.",
                        },
                        "deck_quality_profile": {
                            "type": "string",
                            "enum": ["enterprise", "board", "investor", "sales"],
                            "description": "Quality profile for Deck Engine v2; enterprise is the local default.",
                        },
                        "brand_kit": {
                            "type": ["object", "null"],
                            "description": "Optional local brand kit object with brand_name, primary, and secondary fields.",
                        },
                        "source_notebook_path": {
                            "type": "string",
                            "description": "Optional local Source Notebook path used for evidence-grounded deck generation.",
                        },
                        "asset_paths": {
                            "type": ["array", "string", "null"],
                            "description": "Optional local image/logo/brand asset paths. Missing assets are surfaced as Studio warnings.",
                        },
                    },
                    "required": ["topic"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_pptx_deck",
                "description": (
                    "Erstellt ein natives, editierbares Enterprise-Pitchdeck als .pptx mit echten Textboxen, "
                    "Shapes, Scorecard und Claim-Spine-Manifest. Nutze dies, wenn der User PowerPoint, PPTX, "
                    "editierbare Slides oder Fortune-500/Board-Level Praesentationen verlangt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "audience": {"type": "string"},
                        "thesis": {"type": "string"},
                        "slides": {
                            "type": ["array", "string", "null"],
                            "description": "Optional: Slide-Outline als Liste von {title, claim, body, visual, proof} oder Markdown-Abschnitte.",
                        },
                        "filename": {"type": "string"},
                        "deck_profile": {
                            "type": "string",
                            "enum": ["product-platform", "engineering-platform", "strategy-leadership", "gtm-growth", "finance-ir", "consumer-retail"],
                        },
                        "design_theme": {
                            "type": "string",
                            "enum": ["evergreen", "executive", "studio"],
                        },
                        "source_notes": {"type": "string"},
                        "evidence_level": {
                            "type": "string",
                            "enum": ["sources", "mixed", "assumptions", "user-provided"],
                        },
                        "enterprise_grade": {"type": "boolean"},
                        "template_path": {"type": "string"},
                        "brand_name": {"type": "string"},
                        "brand_primary": {"type": "string", "description": "Hex color, e.g. #003366"},
                        "brand_secondary": {"type": "string", "description": "Hex color, e.g. #16a34a"},
                        "deck_quality_profile": {
                            "type": "string",
                            "enum": ["enterprise", "board", "investor", "sales"],
                        },
                        "source_notebook_path": {
                            "type": "string",
                            "description": "Optional local Source Notebook path used for evidence-grounded deck generation.",
                        },
                        "asset_paths": {
                            "type": ["array", "string", "null"],
                            "description": "Optional local image/logo/brand asset paths. Missing assets are surfaced as Studio warnings.",
                        },
                    },
                    "required": ["topic"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "inspect_pptx_template",
                "description": "Analysiert eine lokale PPTX-Datei als Template: Slides, editierbare Text-Runs, Palette, Beispieltexte und Warnungen.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_pptx_template",
                "description": "Kopiert eine vorhandene PPTX und ersetzt Text-Runs in-place, um Layout und Styles des Templates zu erhalten.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "template_path": {"type": "string"},
                        "replacements": {
                            "type": ["object", "array"],
                            "description": "Mapping old_text -> new_text oder Liste von {from,to}.",
                        },
                        "filename": {"type": "string"},
                    },
                    "required": ["template_path", "replacements"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "qa_pptx_deck",
                "description": "Erstellt lokalen PPTX-QA-Report und HTML-Contact-Sheet fuer visuelle Review der Slide-Struktur.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pptx_path": {"type": "string"},
                    },
                    "required": ["pptx_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_svg",
                "description": (
                    "Speichert SVG-Grafik-Code als .svg Datei in ~/Downloads. "
                    "Du schreibst den SVG-Code selbst. Für Logos, Icons, Diagramme."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "svg_code": {"type": "string"},
                        "filename": {"type": "string"},
                    },
                    "required": ["svg_code"]
                }
            }
        },
    ]
    _TOOL_SCHEMA_CACHE = (now, schemas)
    return schemas


def get_filtered_tool_schemas(whitelist: list[str]) -> list[dict]:
    """
    Gibt eine gefilterte Teilmenge der Tool-Schemas zurück.
    Wird von Swarm-Agenten genutzt, um nur erlaubte Tools anzubieten.

    Args:
        whitelist: Liste von Tool-Namen die erlaubt sind

    Returns:
        Gefilterte Tool-Schema-Liste
    """
    all_tools = get_tool_schemas()
    return [
        t for t in all_tools
        if t.get("function", {}).get("name") in whitelist
    ]

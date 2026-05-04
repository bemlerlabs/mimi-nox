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
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import ollama
from ddgs import DDGS


# Module-level shared Ollama client (reuse TCP connection)
_shared_client: ollama.AsyncClient | None = None


def _get_shared_client() -> ollama.AsyncClient:
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

        # Formatierte Ausgabe damit das Modell die URLs sieht und zitieren kann
        formatted_parts = []
        for i, r in enumerate(raw, 1):
            title = r.get("title", "")
            url   = r.get("href", "")
            body  = r.get("body", "")
            formatted_parts.append(
                f"[{i}] {title}\n"
                f"    URL: {url}\n"
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
    Liest eine Datei und gibt den Inhalt zurück.

    Sicherheit: Nur Dateien innerhalb der Whitelist erlaubt.
    Große Dateien werden auf MAX_FILE_CHARS gekürzt.

    Raises:
        FileNotAllowedError:  Pfad außerhalb Whitelist
        FileNotFoundError:    Datei existiert nicht
    """
    # Tilde expandieren
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))

    if not resolved.exists():
        raise FileNotFoundError(
            f"Datei nicht gefunden: '{resolved}'"
        )

    content = resolved.read_text(encoding="utf-8", errors="replace")

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS]
        content += f"\n\n[Datei gekürzt: Original hatte mehr als {MAX_FILE_CHARS} Zeichen]"

    return content


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
    Optimiert für Gemma4 E4B's 128K Context Window.

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
# Tool: analyze_image (Gemma4 E4B Vision / OCR)
# ===========================================================================

async def analyze_image(
    path: str,
    question: str = "Beschreibe dieses Bild detailliert.",
) -> str:
    """
    Analysiert ein Bild via Gemma4 E4B's native multimodale Fähigkeit.

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
            model=os.environ.get("MIMI_NOX_MODEL", "gemma4:e4b"),
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

from core.browser import browser_manager

async def browser_go(url: str) -> str:
    return await browser_manager.go(url)

async def browser_screenshot() -> str:
    import time, base64
    b64 = await browser_manager.screenshot()
    image_dir = Path(os.environ.get("MIMI_NOX_IMAGE_DIR", str(Path.home() / ".mimi-nox" / "sessions" / "images")))
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = f"browser_{int(time.time())}.jpeg"
    with open(image_dir / filename, "wb") as f:
        f.write(base64.b64decode(b64))
    return f"Browser Screenshot aufgenommen:\n\n![Browser](/images/{filename})"

async def browser_click(target_description: str) -> str:
    return await browser_manager.click(target_description)

async def browser_type(text: str) -> str:
    return await browser_manager.type_text(text)

async def browser_press(key: str) -> str:
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
    try:
        import matplotlib
        matplotlib.use("Agg")  # kein Display nötig
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import tempfile, os

        fig, ax = plt.subplots(figsize=(8, 5))
        fig.patch.set_facecolor("#020504")
        ax.set_facecolor("#040a04")
        ax.tick_params(colors="#6b7280")
        ax.spines["bottom"].set_color("#166534")
        ax.spines["left"].set_color("#166534")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.title.set_color("#f0fdf4")
        ax.xaxis.label.set_color("#6b7280")
        ax.yaxis.label.set_color("#6b7280")

        vals = [float(v) for v in values]
        ct = chart_type.lower()

        if ct == "bar":
            bars = ax.bar(labels, vals, color=color, alpha=0.85, edgecolor="#166534", linewidth=0.5)
            for bar, v in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(vals)*0.01,
                        f"{v:g}", ha="center", va="bottom", color="#86efac", fontsize=9)
        elif ct == "line":
            ax.plot(labels, vals, color=color, linewidth=2.5, marker="o",
                    markersize=6, markerfacecolor="#020504", markeredgecolor=color)
            ax.fill_between(range(len(labels)), vals, alpha=0.12, color=color)
            ax.set_xticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=15 if len(labels) > 6 else 0)
        elif ct == "pie":
            greens = ["#22c55e","#16a34a","#15803d","#166534","#4ade80","#86efac","#bbf7d0"]
            colors = [greens[i % len(greens)] for i in range(len(labels))]
            wedges, texts, autotexts = ax.pie(
                vals, labels=labels, autopct="%1.1f%%",
                colors=colors, startangle=140,
                textprops={"color": "#f0fdf4", "fontsize": 10},
                wedgeprops={"edgecolor": "#020504", "linewidth": 2}
            )
            for at in autotexts:
                at.set_color("#020504")
                at.set_fontweight("bold")
        else:
            return f"[chart: Unbekannter Typ '{chart_type}'. Erlaubt: bar, line, pie]"

        ax.set_title(title, fontsize=14, fontweight="bold", pad=16)
        if xlabel: ax.set_xlabel(xlabel)
        if ylabel: ax.set_ylabel(ylabel)
        plt.tight_layout(pad=1.5)

        # In /tmp speichern
        out = Path(tempfile.gettempdir()) / f"nox_chart_{int(datetime.now().timestamp())}.png"
        plt.savefig(str(out), dpi=130, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)

        return f"CHART_FILE:{out}"

    except ImportError:
        return "[chart: matplotlib nicht installiert — 'pip install matplotlib']"
    except Exception as e:
        return f"[chart-Fehler: {e}]"


# ===========================================================================
# Tool: create_pdf  (reportlab → PDF-Datei)
# ===========================================================================

async def create_pdf(
    title: str,
    content: str,
    filename: str = "nox_dokument.pdf",
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
        import re

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / filename

        doc = SimpleDocTemplate(
            str(out), pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=24*mm, bottomMargin=20*mm
        )

        # Farben
        BG      = colors.HexColor("#020504")
        GREEN   = colors.HexColor("#22c55e")
        GREEN_L = colors.HexColor("#4ade80")
        TEXT    = colors.HexColor("#f0fdf4")
        MUTED   = colors.HexColor("#6b7280")

        styles = getSampleStyleSheet()
        def S(name, **kw):
            return ParagraphStyle(name, **kw)

        s_title = S("T", fontSize=22, textColor=GREEN, spaceAfter=4, spaceBefore=0,
                    fontName="Helvetica-Bold", alignment=TA_CENTER)
        s_h1    = S("H1", fontSize=15, textColor=GREEN_L, spaceAfter=4, spaceBefore=12,
                    fontName="Helvetica-Bold")
        s_h2    = S("H2", fontSize=12, textColor=GREEN_L, spaceAfter=3, spaceBefore=8,
                    fontName="Helvetica-Bold")
        s_body  = S("B", fontSize=10, textColor=TEXT, spaceAfter=6, leading=16,
                    fontName="Helvetica")
        s_bullet= S("BL", fontSize=10, textColor=TEXT, spaceAfter=3, leading=15,
                    leftIndent=12, fontName="Helvetica",
                    bulletText="•", bulletIndent=4)
        s_meta  = S("M", fontSize=8, textColor=MUTED, spaceAfter=8, alignment=TA_CENTER,
                    fontName="Helvetica")

        story = []
        story.append(Paragraph(title, s_title))
        story.append(Paragraph(f"Erstellt von ◑ MiMi Nox · {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_meta))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREEN, spaceAfter=10))

        for line in content.splitlines():
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], s_h2))
            elif line.startswith("# "):
                story.append(Paragraph(line[2:], s_h1))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph(line[2:], s_bullet))
            else:
                # Inline Bold: **text** → <b>text</b>
                line = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", line)
                story.append(Paragraph(line, s_body))

        doc.build(story)
        return f"PDF_FILE:{out}"

    except ImportError:
        return "[pdf: reportlab nicht installiert — 'pip install reportlab']"
    except Exception as e:
        return f"[pdf-Fehler: {e}]"


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


TOOL_MAP: dict[str, object] = {
    "web_search":       web_search,
    "file_search":      file_search,
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
    return [
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
                    "Liest den Inhalt einer Datei. "
                    "Nutze dieses Tool wenn der User eine Datei lesen, analysieren oder erklären möchte. "
                    "Sicherheit: Nur Dateien im Home-Verzeichnis, Desktop, Documents, Downloads erlaubt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Absoluter oder ~-relativer Pfad z.B. '~/Desktop/vertrag.txt'",
                        },
                    },
                    "required": ["path"],
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
                    "Erstellt ein formatiertes PDF-Dokument aus Markdown-ähnlichem Text "
                    "und speichert es in ~/Downloads. Nutze dies für Berichte, Zusammenfassungen."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title":    {"type": "string"},
                        "content":  {"type": "string"},
                        "filename": {"type": "string"},
                    },
                    "required": ["title","content"]
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

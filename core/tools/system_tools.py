"""MiMi Nox – System/Core tools: datetime, projects, workspace, image, screenshot, SVG."""

from __future__ import annotations

import asyncio
import base64
import os
import subprocess
import sys
import time as time_module
from datetime import datetime
from pathlib import Path

from core.tools.base import (
    DirectoryNotFoundError,
    FileNotAllowedError,
    MAX_WORKSPACE_CHARS,
    MAX_WORKSPACE_DEPTH,
    SUPPORTED_IMAGE_EXTENSIONS,
    _get_shared_client,
    _is_path_allowed,
)


GERMAN_WEEKDAYS = [
    "Montag", "Dienstag", "Mittwoch", "Donnerstag",
    "Freitag", "Samstag", "Sonntag",
]

GERMAN_MONTHS = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


async def get_datetime() -> str:
    now = datetime.now()
    weekday = GERMAN_WEEKDAYS[now.weekday()]
    month = GERMAN_MONTHS[now.month - 1]
    return f"{weekday}, {now.day:02d}. {month} {now.year}, {now.hour:02d}:{now.minute:02d} Uhr"


async def discover_projects(query: str = "", root: str | None = None, max_results: int = 10) -> str:
    from core.project_discovery import discover_project_records, format_project_listing

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
    from core.project_discovery import analyze_project_path

    return await asyncio.to_thread(analyze_project_path, path)


async def load_workspace(
    path: str,
    extensions: list[str] | None = None,
    max_depth: int = MAX_WORKSPACE_DEPTH,
) -> str:
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


async def analyze_image(
    path: str,
    question: str = "Beschreibe dieses Bild detailliert.",
) -> str:
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


async def take_screenshot() -> str:
    image_dir = Path(os.environ.get("MIMI_NOX_IMAGE_DIR", str(Path.home() / ".mimi-nox" / "sessions" / "images")))
    image_dir.mkdir(parents=True, exist_ok=True)

    filename = f"screenshot_{int(time_module.time())}.png"
    filepath = image_dir / filename

    try:
        if sys.platform == "darwin":
            await asyncio.to_thread(
                subprocess.run, ["screencapture", "-x", str(filepath)], check=True
            )
        else:
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


async def create_svg(
    svg_code: str,
    filename: str = "nox_grafik.svg",
) -> str:
    import re

    try:
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / filename

        svg_code = re.sub(
            r"<script[^>]*>.*?</script>", "", svg_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        svg_code = re.sub(
            r"<foreignObject[^>]*>.*?</foreignObject>", "", svg_code,
            flags=re.DOTALL | re.IGNORECASE
        )
        svg_code = re.sub(
            r'\s+on\w+\s*=\s*"[^"]*"', "", svg_code,
            flags=re.IGNORECASE
        )
        svg_code = re.sub(
            r"\s+on\w+\s*=\s*'[^']*'", "", svg_code,
            flags=re.IGNORECASE
        )
        svg_code = re.sub(
            r'href\s*=\s*"javascript:[^"]*"', 'href="#"', svg_code,
            flags=re.IGNORECASE
        )

        if "<svg" not in svg_code:
            svg_code = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">\n{svg_code}\n</svg>'

        out.write_text(svg_code, encoding="utf-8")
        return f"SVG_FILE:{out}"

    except Exception as e:
        return f"[svg-Fehler: {e}]"

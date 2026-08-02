"""MiMi Nox – file_search, read_file, list_directory tools."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from core.tools.base import (
    FileNotAllowedError,
    MAX_FILE_CHARS,
    _is_path_allowed,
)


# Lazy-import pdfplumber
try:
    import pdfplumber as _pdfplumber
    _PDF_AVAILABLE = True
except ImportError:
    _pdfplumber = None
    _PDF_AVAILABLE = False


async def file_search(query: str, path: str | None = None) -> str:
    query = query.strip()
    if not query:
        raise ValueError("Query darf nicht leer sein")

    search_path = path or str(Path.home() / "Desktop")

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
        return f"Dateisuche nicht verfügbar auf diesem System ({sys.platform})."


async def read_file(path: str) -> str:
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))

    if not resolved.exists():
        raise FileNotFoundError(f"File not found: '{resolved}'")

    if resolved.suffix.lower() == ".pdf":
        return _extract_pdf_text(resolved)

    content = resolved.read_text(encoding="utf-8", errors="replace")

    if len(content) > MAX_FILE_CHARS:
        content = content[:MAX_FILE_CHARS]
        content += f"\n\n[File truncated: original had more than {MAX_FILE_CHARS} chars]"

    return content


def _extract_pdf_text(path: Path) -> str:
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

    except Exception as exc:
        return f"[Could not read PDF '{path.name}': {exc}]"


async def list_directory(path: str) -> list[str]:
    resolved = Path(path).expanduser()

    if not _is_path_allowed(resolved):
        raise FileNotAllowedError(str(resolved))

    from core.tools.base import DirectoryNotFoundError

    if not resolved.exists():
        raise DirectoryNotFoundError(str(resolved))

    entries = [entry.name for entry in sorted(resolved.iterdir())]
    if len(entries) > 500:
        return entries[:500] + ["... [Liste auf 500 Einträge gekürzt]"]
    return entries

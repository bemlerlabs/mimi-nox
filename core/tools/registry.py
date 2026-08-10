"""MiMi Nox – Tool registry: TOOL_MAP, execute_tool, get_tool_schemas."""

from __future__ import annotations

import time

from core.tools.base import (
    TOOL_SCHEMA_CACHE_TTL_SECONDS,
    _TOOL_SCHEMA_CACHE,
    ShellConfirmationRequired,
)
from core.tools.task_tools import manage_tasks
from core.tools.web_search import web_search
from core.tools.file_ops import file_search, read_file, list_directory
from core.tools.source_tools import (
    create_source_notebook,
    query_source_notebook,
    export_source_brief,
)
from core.tools.system_tools import (
    discover_projects,
    analyze_project,
    get_datetime,
    load_workspace,
    analyze_image,
    take_screenshot,
    create_svg,
)
from core.tools.browser_tools import (
    _vision_click_wrapper,
    _vision_type_wrapper,
    browser_go,
    browser_screenshot,
    browser_click,
    browser_type,
    browser_press,
)
from core.tools.chart_tools import generate_chart
from core.tools.pdf_tools import create_pdf
from core.tools.deck_tools import (
    create_pitch_deck,
    create_pptx_deck,
    inspect_pptx_template,
    edit_pptx_template,
    qa_pptx_deck,
)
from core.tools.shell_tools import run_shell
from core.tools.mcp_client import get_mcp_tools, call_registered_mcp_tool


TOOL_MAP: dict[str, object] = {
    "manage_tasks": manage_tasks,
    "web_search": web_search,
    "file_search": file_search,
    "discover_projects": discover_projects,
    "analyze_project": analyze_project,
    "create_source_notebook": create_source_notebook,
    "query_source_notebook": query_source_notebook,
    "export_source_brief": export_source_brief,
    "read_file": read_file,
    "list_directory": list_directory,
    "get_datetime": get_datetime,
    "run_shell": run_shell,
    "load_workspace": load_workspace,
    "analyze_image": analyze_image,
    "vision_click": _vision_click_wrapper,
    "vision_type": _vision_type_wrapper,
    "take_screenshot": take_screenshot,
    "browser_go": browser_go,
    "browser_screenshot": browser_screenshot,
    "browser_click": browser_click,
    "browser_type": browser_type,
    "browser_press": browser_press,
    "generate_chart": generate_chart,
    "create_pdf": create_pdf,
    "create_pitch_deck": create_pitch_deck,
    "create_pptx_deck": create_pptx_deck,
    "inspect_pptx_template": inspect_pptx_template,
    "edit_pptx_template": edit_pptx_template,
    "qa_pptx_deck": qa_pptx_deck,
    "create_svg": create_svg,
}


async def execute_tool(name: str, arguments: dict) -> str:
    # MCP-Remote-Tools (Namespace 'mcp_') werden separat dispatched.
    mcp_tools = get_mcp_tools()
    if name in mcp_tools:
        try:
            text, is_error = await call_registered_mcp_tool(name, arguments)
            prefix = "[MCP-Tool-Fehler] " if is_error else ""
            return f"{prefix}{text}"
        except Exception as exc:
            return f"[MCP-Tool-Fehler '{name}': {exc}]"

    func = TOOL_MAP.get(name)
    if func is None:
        return f"[Tool '{name}' nicht gefunden]"

    try:
        result = await func(**arguments)
        if isinstance(result, list):
            return "\n".join(str(r) for r in result)
        return str(result)
    except ShellConfirmationRequired:
        raise
    except Exception as exc:
        if exc.__class__.__name__ == "SandboxConfirmationRequired":
            raise
        return f"[Tool-Fehler '{name}': {exc}]"


def invalidate_tool_schema_cache() -> None:
    """Löscht den get_tool_schemas-Cache (z.B. wenn MCP-Tools registriert werden)."""
    global _TOOL_SCHEMA_CACHE
    _TOOL_SCHEMA_CACHE = None


def get_tool_schemas() -> list[dict]:
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
                        "chart_type": {"type": "string", "enum": ["bar", "line", "pie"]},
                        "title": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}},
                        "values": {"type": "array", "items": {"type": "number"}},
                        "xlabel": {"type": "string"},
                        "ylabel": {"type": "string"},
                    },
                    "required": ["chart_type", "title", "labels", "values"]
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
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "filename": {"type": "string"},
                        "template": {"type": "string", "enum": ["report", "brief", "analysis", "checklist"]},
                    },
                    "required": ["title", "content"]
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
    # MCP-Remote-Tools dynamisch anhängen (Namespace 'mcp_')
    for mcp_name, mcp_entry in get_mcp_tools().items():
        schemas.append({
            "type": "function",
            "function": mcp_entry.get("schema", {"name": mcp_name, "description": "", "inputSchema": {"type": "object"}}),
        })

    _TOOL_SCHEMA_CACHE = (now, schemas)
    return schemas


def get_filtered_tool_schemas(whitelist: list[str]) -> list[dict]:
    all_tools = get_tool_schemas()
    return [
        t for t in all_tools
        if t.get("function", {}).get("name") in whitelist
    ]

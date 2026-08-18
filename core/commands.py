"""
◑ MiMi Nox – Slash Commands

Extensible command registry. Add your own commands in 30 seconds:

    COMMANDS["/mycmd"] = "Do something awesome with: {input}"

Commands are resolved before sending to Ollama.
The {input} placeholder is replaced with the user's text after the command.

Example:
    User types:  /post AI productivity
    Resolves to: "Write a professional LinkedIn post about... AI productivity"

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# Format: "/command": "Prompt template with optional {input} placeholder"

COMMANDS: dict[str, str] = {
    "/post": (
        "Write a professional, authentic LinkedIn post about the following topic. "
        "Keep it concise (max 150 words), engaging, and avoid corporate buzzwords. "
        "Topic: {input}"
    ),
    "/debug": (
        "You are a senior software engineer with 15 years of experience. "
        "Carefully analyze the following code for bugs, edge cases, performance issues, "
        "and improvements. Be specific and explain your reasoning. "
        "Code:\n{input}"
    ),
    "/idea": (
        "Generate exactly 5 creative, actionable startup ideas related to: {input}\n\n"
        "For each idea use this format:\n"
        "**Name** | Problem | Solution | Why now\n\n"
        "Be concrete, not generic."
    ),
    "/explain": (
        "Explain the following concept clearly and simply, "
        "as if explaining to a smart developer who has never encountered it before. "
        "Use analogies if helpful. Concept: {input}"
    ),
    "/commit": (
        "Write a conventional Git commit message for the following changes. "
        "Use the format: <type>(<scope>): <short description>\n\n"
        "Then add a brief body if needed. Changes:\n{input}"
    ),
    # /swarm is handled specially by the App (triggers multi-agent pipeline)
    # The template here is only used as a fallback usage hint.
    "/swarm": "__swarm__:{input}",
    # /learn triggers the Skill-Builder (KI erstellt sich selbst neue Skills)
    "/learn": "__learn__:{input}",
    # Phase 2 Item 8 — Prompt-Commands (wie /post: {input} = User-Text):
    "/plan": (
        "Erstelle einen detaillierten, schrittweisen Implementierungsplan für:\n"
        "{input}\n\n"
        "Format pro Schritt: Ziel, konkretes Vorgehen, veränderte Dateien, "
        "Risiko. Schließe mit einer Verifikations-Strategie ab (Tests/Checks). "
        "Kein Code-Spam — Plan zuerst."
    ),
    "/review": (
        "Du bist ein kritischer Senior-Reviewer. Analysiere den folgenden "
        "Code auf Bugs, Sicherheitslücken, Performance- und Stilprobleme. "
        "Sei konkret (Zeilen/Verhalten), priorisiere nach Schweregrad. "
        "Falls kein Code angehängt ist: bitte um Code.\n{input}"
    ),
    # Phase 2 Item 8 — Info-Commands (lokal gerendert, KEIN LLM).
    # Die Templates sind nur Fallback-Dokumentation; die TUI rendert sie
    # via render_info_command() (Info-Commands werden dort abgefangen,
    # bevor resolve_command sie hier auflösen würde).
    "/help": "MiMi Nox Command-Übersicht (siehe /help in der TUI)",
    "/model": "Aktives Modell/Provider anzeigen (siehe /model in der TUI)",
    "/engine": "Engine-Config anzeigen (siehe /engine in der TUI)",
    "/configure": "Engine-Auswahl (siehe /configure in der TUI)",
}

# ---------------------------------------------------------------------------
# Info-Commands (Phase 2 Item 8)
# ---------------------------------------------------------------------------
# Diese Commands werden LOCALL gerendert (kein LLM-Pass): sie zeigen Zustand
# an. In der TUI wird is_info_command() vor resolve_command() ausgewertet;
# die Registry-Einträge oben sind Fallback + Dokumentation.
INFO_COMMANDS: frozenset[str] = frozenset({"/help", "/model", "/engine", "/configure"})


def is_info_command(text: str) -> bool:
    """True wenn text ein Info-Command ist (/help, /model, /engine, /configure),
    unabhängig von zusätzlichen Argumenten."""
    parts = text.strip().split(maxsplit=1)
    return bool(parts) and parts[0].lower() in INFO_COMMANDS


def render_info_command(text: str) -> str:
    """Rendert einen Info-Command lokal (kein LLM).

    Returns:
        Der Render-Text, oder "" wenn text kein Info-Command ist.

    Lazy-Imports: model_provider / engine_config werden erst bei Bedarf geladen,
    damit core.commands auch ohne das volle Provider-Ökosystem importierbar
    bleibt (z. B. in leichten Test-Runs).
    """
    cmd = text.strip().split(maxsplit=1)[0].lower()
    if cmd not in INFO_COMMANDS:
        return ""

    if cmd == "/help":
        lines = ["MiMi Nox — Commands"]
        lines.append("─" * 40)
        for name, desc in get_command_help():
            tag = " [Info]" if name in INFO_COMMANDS else ""
            lines.append(f"  {name:<12} {desc}{tag}")
        lines.append("")
        lines.append("Info-Commands rendern lokal (kein LLM): /help /model /engine /configure")
        return "\n".join(lines)

    if cmd == "/model":
        try:
            from core.model_provider import get_active_provider

            cfg = get_active_provider()
            return (
                "Aktives Modell/Provider:\n"
                f"  Provider : {cfg.provider}\n"
                f"  Label    : {cfg.label}\n"
                f"  Modell   : {cfg.model}\n"
                f"  Base URL : {cfg.base_url}"
            )
        except Exception as exc:  # noqa: BLE001
            return f"Modell-Info nicht verfügbar: {exc}"

    if cmd == "/engine":
        try:
            from core.engine_config import default_config_path, load_engine_config

            choice = load_engine_config()
            if choice is None:
                return (
                    "Keine Engine-Auswahl persistiert (~/.mimi-nox/engine.json).\n"
                    "Wähle eine Engine: `miminox tui --configure`\n"
                    "(alternativ: `miminox serve` für die OpenAI-kompatible Engine)"
                )
            lines = [
                f"Engine-Config ({default_config_path()}):",
                f"  Provider : {choice.provider}",
                f"  Modell   : {choice.model}",
            ]
            if choice.api_url:
                lines.append(f"  API URL  : {choice.api_url}")
            lines.append("Wechseln: `miminox tui --configure`")
            return "\n".join(lines)
        except Exception as exc:  # noqa: BLE001
            return f"Engine-Info nicht verfügbar: {exc}"

    if cmd == "/configure":
        try:
            from core.engine_config import load_engine_config

            choice = load_engine_config()
            if choice is not None:
                state = f"Aktuell: {choice.provider} / {choice.model}"
            else:
                state = "Noch keine Engine gewählt."
            return (
                f"{state}\n"
                "Neue Engine wählen (interaktiv, wird nach ~/.mimi-nox/engine.json\n"
                "persistiert): `miminox tui --configure`"
            )
        except Exception as exc:  # noqa: BLE001
            return f"Configure-Info nicht verfügbar: {exc}"

    # Unreachable (cmd wurde oben gegen INFO_COMMANDS geprüft) — defensive.
    return ""

# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

_COMMAND_DESCRIPTIONS: dict[str, str] = {
    "/post":    "Write a LinkedIn post",
    "/debug":   "Debug code as a senior engineer",
    "/idea":    "Generate 5 startup ideas",
    "/explain": "Explain a concept simply",
    "/commit":  "Write a Git commit message",
    "/swarm":   "Multi-agent parallel pipeline",
    "/learn":   "Lerne ein Muster und erstelle einen neuen Skill",
    "/plan":    "Schrittweiser Implementierungsplan (Prompt)",
    "/review":  "Kritische Code-Review (Prompt)",
    "/help":    "Command-Übersicht (lokal, kein LLM)",
    "/model":   "Aktives Modell/Provider (lokal, kein LLM)",
    "/engine":  "Engine-Config (lokal, kein LLM)",
    "/configure": "Engine-Auswahl (lokal, kein LLM)",
}

# Commands that trigger special app-level behaviour (not resolved to a prompt)
SWARM_COMMANDS: frozenset[str] = frozenset({"/swarm"})
LEARN_COMMANDS: frozenset[str] = frozenset({"/learn"})


def resolve_command(raw_input: str) -> str:
    """
    Resolve a slash command to its full prompt.

    Examples:
        resolve_command("/post AI trends")
        → "Write a professional LinkedIn post about... AI trends"

        resolve_command("/post")
        → "[/post] Usage: /post <topic>  —  Write a LinkedIn post"

        resolve_command("/unknown foo")
        → "/unknown foo"   (passthrough, no match)

        resolve_command("hello")
        → "hello"          (passthrough, no slash)

    Returns:
        The resolved prompt string, or the original input if no match.
    """
    raw_input = raw_input.strip()

    if not raw_input.startswith("/"):
        return raw_input

    parts = raw_input.split(maxsplit=1)
    command = parts[0].lower()
    argument = parts[1].strip() if len(parts) > 1 else ""

    if command not in COMMANDS:
        return raw_input  # unknown command → passthrough

    template = COMMANDS[command]

    if "{input}" in template:
        if not argument:
            desc = _COMMAND_DESCRIPTIONS.get(command, "")
            return (
                f"[{command}] Usage: {command} <text>  "
                f"{'— ' + desc if desc else ''}"
            )
        return template.replace("{input}", argument)

    # Template has no {input} placeholder → append argument if present
    return template + (" " + argument if argument else "")


def get_completions(prefix: str) -> list[str]:
    """
    Return all commands that start with the given prefix.
    Used for Tab-completion in HistoryInput.

    Example:
        get_completions("/po") → ["/post"]
        get_completions("/")   → ["/post", "/debug", "/idea", "/explain", "/commit"]
    """
    return [cmd for cmd in COMMANDS if cmd.startswith(prefix)]


def get_command_help() -> list[tuple[str, str]]:
    """Return list of (command, description) for the help overlay."""
    return [
        (cmd, _COMMAND_DESCRIPTIONS.get(cmd, ""))
        for cmd in COMMANDS
    ]


def is_command(text: str) -> bool:
    """Return True if text starts with a known slash command."""
    parts = text.strip().split(maxsplit=1)
    return bool(parts) and parts[0].lower() in COMMANDS


def is_swarm_command(text: str) -> bool:
    """Return True if text is a /swarm command (handled by swarm pipeline)."""
    parts = text.strip().split(maxsplit=1)
    return bool(parts) and parts[0].lower() in SWARM_COMMANDS


def extract_swarm_task(text: str) -> str:
    """
    Extract the task from a /swarm command.
    "/swarm Plan a REST API" → "Plan a REST API"
    "/swarm" → ""  (caller should show usage hint)
    """
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def is_learn_command(text: str) -> bool:
    """Return True if text is a /learn command (handled by skill-builder)."""
    parts = text.strip().split(maxsplit=1)
    return bool(parts) and parts[0].lower() in LEARN_COMMANDS


def extract_learn_topic(text: str) -> str:
    """
    Extract the topic from a /learn command.
    "/learn FastAPI-Routen Stil" → "FastAPI-Routen Stil"
    "/learn" → ""  (caller should show usage hint)
    """
    parts = text.strip().split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""

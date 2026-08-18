"""P0-1 / Threat-Model E1: Approval-Gates, Diff-Vorschau und ``--dry-run``.

Konservative Default-Defaults (Release-Bar aus AGENTS.md):

- Destructive / mutating-Tools brauchen **vor** der Ausführung eine
  explizite Freigabe.
- Ohne Policy und ohne Interaktivität wird eine MUTATING-Ausführung
  abgelehnt (``--yes`` erforderlich) statt still ausgeführt.
- ``--dry-run`` zeigt den Diff, schreibt aber **nichts**.

Die Layer ist bewusst in ``core.tools.approval`` isoliert, damit die
Registry (``core.tools.registry.execute_tool``) und der CLI-Subcommand
(``miminox tool <name>``) denselben Gate-Code nutzen.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional


# ── Klassifikation ─────────────────────────────────────────────────────────

#: Read-only / non-mutating Tools. Diese brauchen nie ein Approval-Gate.
#: (Bewusst konservativ: alles andere gilt als mutating.)
SAFE_TOOLS: frozenset[str] = frozenset({
    "read_file",
    "list_directory",
    "file_search",
    "get_datetime",
    "query_source_notebook",
    "browser_screenshot",
})


@dataclass(frozen=True)
class ToolClassification:
    """Statische Risk-Einstufung eines Tools (E1)."""

    name: str
    is_mutating: bool
    auto_approve_by_default: bool


def classify_tool(name: str) -> ToolClassification:
    """Klassifiziert ein Tool nach Mutations-Potenzial.

    Defaults konservativ: unbekannt / nicht in ``SAFE_TOOLS`` gilt als
    mutating und darf nicht auto-approved werden.
    """
    safe = name in SAFE_TOOLS
    return ToolClassification(
        name=name,
        is_mutating=not safe,
        auto_approve_by_default=safe,
    )


# ── Policy / Decision ──────────────────────────────────────────────────────

#: Callback-Signatur: ``async def on_confirm(tool_name, arguments) -> bool``
OnConfirm = Callable[[str, dict], Awaitable[bool]]


@dataclass
class ApprovalPolicy:
    """Runtime-Approval-Konfiguration pro Ausführungskontext.

    Defaults sind konservative (E1): keine Auto-Approval, kein Dry-Run.
    """

    auto_approve: bool = False
    dry_run: bool = False
    #: ``True`` → explizite Ablehnung (``--no``): mutating-Tools werden nicht ausgeführt.
    declined: bool = False
    #: ``None`` → kein expliziter Callback → auf TTY-Prompt zurückgreifen.
    on_confirm: Optional[OnConfirm] = None
    #: Ist der Aufrufer interaktiv (TTY)? ``False`` → kein Prompt möglich.
    interactive: bool = True


@dataclass
class ApprovalDecision:
    """Ergebnis des Approval-Gates.

    ``report`` ist menschenlesbar und wird von der CLI / der Registry als
    Ergebnis-String an den User weitergereicht.
    """

    approved: bool
    dry_run: bool
    report: str
    diff: str = ""
    extra: dict = field(default_factory=dict)


# ── Diff-Vorschau ───────────────────────────────────────────────────────────

def _truncate(text: str, limit: int = 400) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f" … (+{len(text) - limit} Zeichen)"


def format_diff(tool_name: str, arguments: dict) -> str:
    """Menschenlesbare Vorschau, was ausgeführt werden würde.

    Wird dem User im Approval-Prompt angezeigt; bei ``--dry-run`` ist es
    die einzige sichtbare Wirkung.
    """
    args = dict(arguments or {})

    if tool_name == "create_svg":
        svg = str(args.get("svg_code", ""))
        filename = str(args.get("filename", ""))
        lines = [
            f"SVG erstellen → {filename or '(Default-Name)'}",
            "Vorschau:",
            _truncate(svg, 600),
        ]
        return "\n".join(lines)

    if tool_name == "run_shell":
        cmd = str(args.get("command", ""))
        return f"Shell-Befehl:\n    {cmd}"

    if tool_name == "manage_tasks":
        action = str(args.get("action", ""))
        title = str(args.get("title", ""))
        return f"Tasks: action={action!r} title={title!r}"

    # Fallback: alle Arguments als key/value
    parts = [f"{k} = {_truncate(str(v), 200)}" for k, v in sorted(args.items())]
    body = "\n".join(f"    {p}" for p in parts) or "    (keine Argumente)"
    return f"Tool: {tool_name}\n{body}"


# ── Approval-Request ───────────────────────────────────────────────────────

async def request_approval(
    tool_name: str,
    arguments: dict,
    policy: ApprovalPolicy,
) -> ApprovalDecision:
    """Führt das Approval-Gate aus.

    Reihenfolge (konservativ):

    1. SAFE-Tool → auto-approved (ohne Prompt, ohne Dry-Run-Effekt).
    2. ``policy.auto_approve`` (z.B. ``--yes``) → auto-approved.
    3. ``policy.dry_run`` → **nicht ausgeführt**, Dry-Run-Report.
    4. Callback vorhanden → Callback entscheidet.
    5. Interaktiv → TTY-Prompt (``input()``).
    6. Sonst (non-interactive, kein Flag) → **deny** mit Hinweis auf
       ``--yes`` (Exit 1 in der CLI).
    """
    cls = classify_tool(tool_name)
    diff = format_diff(tool_name, arguments)

    if cls.auto_approve_by_default:
        return ApprovalDecision(
            approved=True, dry_run=False,
            report=f"[auto] {tool_name} ist read-only — keine Approval nötig.",
            diff=diff,
        )

    # Explizite Ablehnung (--no): mutating-Tools werden nicht ausgeführt.
    if policy.declined:
        return ApprovalDecision(
            approved=False, dry_run=False,
            report=f"[Abgelehnt] {tool_name} explizit abgelehnt (--no). Ausführung gestoppt.",
            diff=diff,
        )

    if policy.auto_approve:
        return ApprovalDecision(
            approved=True, dry_run=False,
            report=f"[--yes] {tool_name} explizit freigegeben.",
            diff=diff,
        )

    if policy.dry_run:
        return ApprovalDecision(
            approved=False, dry_run=True,
            report=(
                f"[DRY-RUN] {tool_name} wurde NICHT ausgeführt.\n"
                f"Vorschau:\n{diff}"
            ),
            diff=diff,
        )

    if policy.on_confirm is not None:
        granted = await policy.on_confirm(tool_name, arguments)
        if granted:
            return ApprovalDecision(
                approved=True, dry_run=False,
                report=f"[approved] {tool_name} per Callback freigegeben.",
                diff=diff,
            )
        return ApprovalDecision(
            approved=False, dry_run=False,
            report=f"[Abgelehnt] {tool_name} durch Callback abgelehnt. Ausführung gestoppt.",
            diff=diff,
        )

    if policy.interactive:
        try:
            answer = input(
                f"\n[Approval] {tool_name}\n{diff}\n\n"
                f"Ausführen? [y/N] "
            )
        except EOFError:
            answer = "n"
        if answer.strip().lower() in ("y", "yes"):
            return ApprovalDecision(
                approved=True, dry_run=False,
                report=f"[approved] {tool_name} interaktiv bestätigt.",
                diff=diff,
            )
        return ApprovalDecision(
            approved=False, dry_run=False,
            report=f"[Abgelehnt] {tool_name} interaktiv abgelehnt. Ausführung gestoppt.",
            diff=diff,
        )

    # Non-interactive, kein Flag, kein Callback → konservativ: deny.
    return ApprovalDecision(
        approved=False, dry_run=False,
        report=(
            f"[Abgelehnt] {tool_name} ist mutating und dieser Aufruf ist "
            f"non-interactive. Verwende --yes (explizite Freigabe) oder "
            f"--dry-run (Vorschau ohne Ausführung)."
        ),
        diff=diff,
    )


__all__ = [
    "SAFE_TOOLS",
    "ToolClassification",
    "classify_tool",
    "ApprovalPolicy",
    "ApprovalDecision",
    "OnConfirm",
    "format_diff",
    "request_approval",
]

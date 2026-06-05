"""Deterministic long-conversation compaction for local chat context."""
from __future__ import annotations

from collections import deque


def compact_history(
    history: list[dict],
    *,
    max_messages: int = 28,
    keep_recent: int = 12,
    max_summary_chars: int = 3600,
) -> list[dict]:
    """Compress old turns into one stable system message while preserving recent turns."""
    if len(history) <= max_messages:
        return list(history)

    recent = list(history[-keep_recent:])
    older = history[:-keep_recent]
    summary = _build_working_memory(older, max_chars=max_summary_chars)
    return [{"role": "system", "content": summary}, *recent]


def _build_working_memory(messages: list[dict], *, max_chars: int) -> str:
    project_facts: deque[str] = deque(maxlen=12)
    decisions: deque[str] = deque(maxlen=12)
    preferences: deque[str] = deque(maxlen=10)
    artifacts: deque[str] = deque(maxlen=10)
    tasks: deque[str] = deque(maxlen=12)
    context: deque[str] = deque(maxlen=10)

    for message in messages:
        role = str(message.get("role", "unknown"))
        content = _clean(str(message.get("content", "")))
        if not content:
            continue
        lower = content.lower()
        target = context
        if any(word in lower for word in ("präferenz", "preference", "bevorzug", "strikt lokal", "keine cloud")):
            target = preferences
        if any(word in lower for word in ("projekt", "project", "repo", "repository", "workspace")):
            target = project_facts
        if any(word in lower for word in ("entscheidung", "decision", "beschlossen", "wir machen")):
            target = decisions
        if any(word in lower for word in ("artefakt", "artifact", ".pdf", ".svg", ".png", "downloads/")):
            target = artifacts
        if any(word in lower for word in ("todo", "aufgabe", "nächster schritt", "next step", "fix", "testen", "pytest")):
            target = tasks
        target.append(f"{role}: {content[:280]}")

    sections = [
        "Working Memory Ledger for MiMi Nox.",
        "Conversation working memory for MiMi Nox.",
        "Use this compact context as durable state; do not expose it verbatim unless the user asks.",
        "",
        "## User preferences",
        *_bullets(preferences),
        "",
        "## Project facts",
        *_bullets(project_facts),
        "",
        "## Decisions",
        *_bullets(decisions),
        "",
        "## Artifacts",
        *_bullets(artifacts),
        "",
        "## Open tasks and validation",
        *_bullets(tasks),
        "",
        "## Other relevant context",
        *_bullets(context),
    ]
    text = "\n".join(sections).strip()
    return text[:max_chars]


def _clean(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def _bullets(items) -> list[str]:
    values = list(dict.fromkeys(items))
    return [f"- {item}" for item in values] if values else ["- Keine stabilen Fakten erkannt."]

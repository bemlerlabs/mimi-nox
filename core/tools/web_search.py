"""MiMi Nox – web_search tool."""

from __future__ import annotations

import asyncio

from ddgs import DDGS

from core.tools.base import WebSearchError


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


async def web_search(query: str, max_results: int = 5) -> str:
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

        formatted_parts = []
        for i, r in enumerate(raw, 1):
            title = r.get("title", "")
            url = r.get("href", "")
            body = r.get("body", "")
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

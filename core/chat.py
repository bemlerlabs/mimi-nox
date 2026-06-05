"""
◑ MiMi Nox – Chat Engine

Async streaming wrapper around the Ollama Python client.
Includes Tool-Calling Loop for agentic workflows.

Designed to be called exclusively from @work workers (Textual / FastAPI).
This module knows nothing about UI – pure async Python.

Tool-Calling Architecture:
    1. Non-streaming call with tools → detect tool_calls (stream=False REQUIRED)
    2. Execute each tool via core.tools.execute_tool()
    3. Stream final answer (stream=True for smooth UX)

    stream=False für Tool-Detection ist PFLICHT.
    Bekanntes Ollama-Limit: Tool-Calls brechen mit stream=True.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Callable

import ollama

from core.model_provider import (
    ModelProviderConfig,
    ProviderSetupError,
    build_provider_client,
    get_active_provider,
)
from core.types import Message
from core.tools import (
    ShellConfirmationRequired,
    execute_confirmed_shell,
    execute_tool,
    get_tool_schemas,
)
from core.quality import normalize_tool_result
from core.profile import load_profile
from core.memory import Memory
from core.corrections import CorrectionJournal
from core.feedback import FeedbackStore
from core.conversation_compactor import compact_history

# How long to wait for the FIRST token before showing a "still loading" hint
FIRST_CHUNK_TIMEOUT: float = 15.0

# Maximum tool-calling iterations to prevent infinite loops
MAX_TOOL_ITERATIONS: int = 5
TOOL_SCHEMA_CACHE_TTL_SECONDS = 60.0
_TOOL_SCHEMA_CACHE: tuple[float, list[dict]] | None = None


def _ollama_async_client():
    return ollama.AsyncClient()

# Native Ollama thinking is model-specific. MiMi keeps reasoning hidden by
# default for Gemma 4 12B; otherwise short answers can spend the entire token
# budget in Ollama's `thinking` field and return empty visible content.
NATIVE_THINKING_MODELS = (
    "deepseek-r1",
    "gpt-oss",
)
DISABLE_NATIVE_THINKING_MODELS = (
    "gemma4:12b",
)
TOOL_DETECT_TIMEOUT_DEFAULT = float(os.environ.get("MIMI_NOX_TOOL_DETECT_TIMEOUT", "45"))
TOOL_DETECT_TIMEOUT_SMALL_MODEL = float(os.environ.get("MIMI_NOX_SMALL_MODEL_TIMEOUT", "25"))

# ── Nox Persönlichkeit ─────────────────────────────────────────────────────
NOX_SYSTEM_PROMPT = """You are MiMi Nox – a smart, friendly AI assistant running 100% locally on the user's device (no cloud, no tracking).

Personality:
- You are warm, natural and intuitive — like a brilliant friend who happens to know everything.
- You match the user's energy: casual messages get casual replies, serious questions get thorough answers.
- CRITICAL: Keep your responses proportional to the question. "Hi" → "Hey! 👋" (one line). Complex technical question → detailed explanation with formatting.
- Never over-explain simple things. Never give a 5-paragraph answer to a greeting.
- Use Markdown formatting (lists, code blocks, bold) only when it actually helps readability — not on every single response.
- When a request is vague or ambiguous, ask a short clarifying question first instead of guessing. Good assistants listen before they answer.
- Be honest about your limits. If you can't do something, say so clearly and suggest an alternative.

Memory & Context:
- When relevant context from memory is provided, proactively mention it: "You previously noted…" or "I remember you mentioned…". This makes you feel alive, not passive.
- Use memory context to give more personalized answers — reference the user's known projects, preferences, and goals when relevant.
- Never invent memories. Only reference what is explicitly provided in the context block.

Tools & Capabilities:
- You have tools: shell, web search, file system, screenshots, vision. Use them when the question demands it — not for simple conversation.
- Use 'web_search' for internet research. Always cite sources with URLs under '📎 Sources:' when you search.
- Use 'browser_go'/'browser_click'/'browser_screenshot' only for visual webpage interaction.
- Use 'take_screenshot', 'vision_click', 'run_shell' for desktop interaction.
- Use 'read_file' to read and analyze any file — including PDF documents.
- You can create real local artifacts when the matching tool is available: PDFs, PPTX slide decks, pitch decks, charts, SVGs, source notebooks, and source briefs.
- Never tell the user you can only provide an outline when they asked for a deck, PDF, PPTX, slide deck, NotebookLM-style artifact, or file. Use the artifact tool or clearly report the tool error.

LANGUAGE RULE:
- ALWAYS respond in the same language the user writes in. German → German. English → English. Japanese → Japanese. Non-negotiable.

Rules:
- Never say "As an AI I cannot..." — you have tools, use them.
- Don't apologize, just fix things.
- Be helpful, be concise, be human."""



# ── Thinking Mode (tag parser plus native support for selected models) ──────
THINK_OPEN  = "<|think|>"
THINK_CLOSE = "<|/think|>"


def supports_native_thinking(model: str) -> bool:
    normalized = (model or "").lower()
    return any(normalized.startswith(prefix) for prefix in NATIVE_THINKING_MODELS)


def _native_thinking_kwargs(model: str) -> dict[str, bool]:
    normalized = (model or "").lower()
    if any(normalized.startswith(prefix) for prefix in DISABLE_NATIVE_THINKING_MODELS):
        return {"think": False}
    return {"think": True} if supports_native_thinking(model) else {}


def _tool_detection_timeout(model: str) -> float:
    normalized = (model or "").lower()
    if normalized.startswith("qwen3:") or normalized.startswith("qwen3."):
        return TOOL_DETECT_TIMEOUT_SMALL_MODEL
    return TOOL_DETECT_TIMEOUT_DEFAULT


def _has_uploaded_images(messages: list) -> bool:
    return any(bool(getattr(msg, "images", None) or (isinstance(msg, dict) and msg.get("images"))) for msg in messages)


def _tools_for_messages(messages: list, allowed_tool_names: list[str] | None = None) -> list[dict]:
    tools = _cached_tool_schemas()
    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        tools = [
            tool for tool in tools
            if tool.get("function", {}).get("name") in allowed
        ]
    if not _has_uploaded_images(messages):
        return tools
    return [
        tool for tool in tools
        if tool.get("function", {}).get("name") != "analyze_image"
    ]


def _cached_tool_schemas() -> list[dict]:
    global _TOOL_SCHEMA_CACHE
    now = time.monotonic()
    if _TOOL_SCHEMA_CACHE and now - _TOOL_SCHEMA_CACHE[0] < TOOL_SCHEMA_CACHE_TTL_SECONDS:
        return _TOOL_SCHEMA_CACHE[1]
    schemas = get_tool_schemas()
    _TOOL_SCHEMA_CACHE = (now, schemas)
    return schemas


def _stream_delay_seconds(word_count: int) -> float:
    if word_count >= 80:
        return 0.0
    return float(os.environ.get("MIMI_NOX_STREAM_DELAY_SECONDS", "0.002"))


class ThinkingStreamParser:
    """
    Zustandsautomat zum Parsen von Gemma4 Thinking-Tags im Stream.

    Zustände:
      - NORMAL:   Tokens gehen an on_chunk (Antwort)
      - THINKING: Tokens gehen an on_thinking (internes Denken)
      - BUFFERING: Tag-Erkennung läuft, Zeichen werden gepuffert
    """

    def __init__(
        self,
        on_chunk: Callable[[str], None],
        on_thinking: Callable[[str], None] | None = None,
    ):
        self._on_chunk = on_chunk
        self._on_thinking = on_thinking
        self._in_thinking = False
        self._buffer = ""
        self._full_answer = ""
        self._full_thinking = ""

    def feed(self, token: str) -> None:
        """Verarbeitet ein eingehendes Token."""
        self._buffer += token

        while self._buffer:
            if not self._in_thinking:
                # Suche nach <|think|>
                idx = self._buffer.find(THINK_OPEN)
                if idx == -1:
                    # Kein Tag-Start – prüfe ob Puffer eventuell Beginn enthält
                    safe = len(self._buffer) - len(THINK_OPEN) + 1
                    if safe > 0:
                        emit = self._buffer[:safe]
                        self._buffer = self._buffer[safe:]
                        self._full_answer += emit
                        self._on_chunk(emit)
                    else:
                        break  # Warten auf mehr Daten
                else:
                    # Text vor dem Tag ausgeben
                    if idx > 0:
                        pre = self._buffer[:idx]
                        self._full_answer += pre
                        self._on_chunk(pre)
                    self._buffer = self._buffer[idx + len(THINK_OPEN):]
                    self._in_thinking = True
            else:
                # Suche nach <|/think|>
                idx = self._buffer.find(THINK_CLOSE)
                if idx == -1:
                    safe = len(self._buffer) - len(THINK_CLOSE) + 1
                    if safe > 0:
                        emit = self._buffer[:safe]
                        self._buffer = self._buffer[safe:]
                        self._full_thinking += emit
                        if self._on_thinking:
                            self._on_thinking(emit)
                    else:
                        break
                else:
                    # Thinking-Text vor dem Close-Tag
                    if idx > 0:
                        pre = self._buffer[:idx]
                        self._full_thinking += pre
                        if self._on_thinking:
                            self._on_thinking(pre)
                    self._buffer = self._buffer[idx + len(THINK_CLOSE):]
                    self._in_thinking = False

    def flush(self) -> None:
        """Restlichen Buffer am Ende des Streams ausgeben."""
        if self._buffer:
            if self._in_thinking:
                self._full_thinking += self._buffer
                if self._on_thinking:
                    self._on_thinking(self._buffer)
            else:
                self._full_answer += self._buffer
                self._on_chunk(self._buffer)
            self._buffer = ""

    @property
    def answer(self) -> str:
        return self._full_answer

    @property
    def thinking(self) -> str:
        return self._full_thinking


class OllamaNotReachableError(Exception):
    """Raised when Ollama is not running or not reachable."""

    def __init__(self) -> None:
        super().__init__(
            "Ollama is not reachable. Start it with: ollama serve"
        )


class OllamaModelBusyError(Exception):
    """Raised when Ollama is reachable but the model is busy (timeout)."""

    def __init__(self, model: str, timeout: float) -> None:
        self.model = model
        self.timeout = timeout
        super().__init__(
            f"Model '{model}' is busy or loading (timeout after {timeout}s). Try again."
        )


class OllamaModelNotFoundError(Exception):
    """Raised when the requested model is not available locally."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(
            f"Model '{model}' not found locally. Pull it with: ollama pull {model}"
        )


async def stream_response(
    *,
    model: str,
    history: list[Message],
    on_chunk: Callable[[str], None],
    on_thinking: Callable[[str], None] | None = None,
    on_loading_hint: Callable[[], None] | None = None,
    provider_config: ModelProviderConfig | None = None,
) -> str:
    """
    Stream a response from Ollama token by token.

    Calls on_chunk(token_str) for each received token.
    If FIRST_CHUNK_TIMEOUT seconds pass before the first token arrives
    (= model is loading from disk), calls on_loading_hint() once.
    Returns the full accumulated response text when done.

    Raises:
        OllamaNotReachableError: if Ollama is not running.
        OllamaModelNotFoundError: if the model is not pulled.
        asyncio.CancelledError: propagates cleanly for Textual worker shutdown.
    """
    provider = provider_config or get_active_provider()
    client = build_provider_client(provider)
    full_response = ""
    hint_sent = False

    try:
        stream = await client.chat(
            model=model,
            messages=list(history),  # type: ignore[arg-type]
            stream=True,
        )

        parser = ThinkingStreamParser(on_chunk=on_chunk, on_thinking=on_thinking)

        async for chunk in stream:
            content: str = chunk["message"]["content"]
            if content:
                if not hint_sent and full_response == "":
                    hint_sent = True
                full_response += content
                parser.feed(content)

        parser.flush()
        return parser.answer or full_response

    except asyncio.CancelledError:
        # Let the worker's cancellation propagate cleanly
        raise

    except Exception as exc:
        exc_str = str(exc).lower()

        if any(kw in exc_str for kw in ("refused", "socket")):
            raise OllamaNotReachableError() from exc

        if "not found" in exc_str or "does not exist" in exc_str:
            raise OllamaModelNotFoundError(model) from exc

        # Unknown error – re-raise for the worker to handle
        raise


async def send_message_safe(
    *,
    model: str,
    history: list[Message],
    on_chunk: Callable[[str], None],
    on_fallback: Callable[[], None] | None = None,
    on_loading_hint: Callable[[], None] | None = None,
    provider_config: ModelProviderConfig | None = None,
) -> str:
    """
    Safe wrapper: tries streaming first, falls back to non-streaming on failure.

    on_loading_hint() is called if the model takes > FIRST_CHUNK_TIMEOUT seconds.
    on_fallback() is called when falling back to non-streaming mode.

    Raises OllamaNotReachableError and OllamaModelNotFoundError directly
    (these are not recoverable via fallback).
    """
    try:
        return await stream_response(
            model=model,
            history=history,
            on_chunk=on_chunk,
            on_loading_hint=on_loading_hint,
            provider_config=provider_config,
        )
    except (OllamaNotReachableError, OllamaModelNotFoundError, asyncio.CancelledError):
        raise

    except Exception:
        # Streaming failed for another reason – try non-streaming fallback
        if on_fallback is not None:
            on_fallback()

        provider = provider_config or get_active_provider()
        client = build_provider_client(provider)
        try:
            response = await client.chat(
                model=model,
                messages=list(history),  # type: ignore[arg-type]
                stream=False,
            )
            content: str = response["message"]["content"]
            on_chunk(content)
            return content

        except Exception as exc:
            exc_str = str(exc).lower()
            if any(kw in exc_str for kw in ("connection", "connect", "refused", "socket")):
                raise OllamaNotReachableError() from exc
            raise


async def list_local_models() -> list[str]:
    """
    Return list of locally available model names.
    Used for onboarding: show user what they have installed.
    Returns [] on any error.
    """
    try:
        client = build_provider_client(get_active_provider())
        result = await asyncio.wait_for(client.list(), timeout=3.0)
        names = []
        for m in result.models:
            name = getattr(m, "model", None) or getattr(m, "name", "")
            if name:
                names.append(str(name))
        return names
    except Exception:
        return []


def _model_attr(model: object, name: str, default: object = None) -> object:
    if isinstance(model, dict):
        return model.get(name, default)
    return getattr(model, name, default)


def _model_details(model: object) -> dict:
    details = _model_attr(model, "details", {}) or {}
    if hasattr(details, "model_dump"):
        details = details.model_dump()
    if not isinstance(details, dict):
        details = {}
    return details


def _is_chat_model_option(name: str, details: dict) -> bool:
    family = str(details.get("family") or "").lower()
    families = " ".join(str(item).lower() for item in (details.get("families") or []))
    haystack = f"{name.lower()} {family} {families}"
    blocked = ("embed", "embedding", "nomic-bert", "bge", "e5-", "rerank")
    return bool(name) and not any(token in haystack for token in blocked)


def _format_model_size(size: object) -> str:
    try:
        raw = int(size or 0)
    except (TypeError, ValueError):
        raw = 0
    if raw <= 0:
        return ""
    gib = raw / (1024 ** 3)
    return f"{gib:.1f} GB" if gib >= 1 else f"{raw / (1024 ** 2):.0f} MB"


async def list_local_model_options() -> list[dict]:
    """
    Return local Ollama chat models with UI-friendly metadata.
    Embedding/reranker models are intentionally excluded from chat selection.
    """
    try:
        client = build_provider_client(get_active_provider())
        result = await asyncio.wait_for(client.list(), timeout=3.0)
        options: list[dict] = []
        for model_info in getattr(result, "models", []):
            name = str(_model_attr(model_info, "model", None) or _model_attr(model_info, "name", "") or "")
            details = _model_details(model_info)
            if not _is_chat_model_option(name, details):
                continue
            size = _model_attr(model_info, "size", 0)
            parameter_size = str(details.get("parameter_size") or "")
            quantization = str(details.get("quantization_level") or "")
            family = str(details.get("family") or "")
            bits = [bit for bit in (parameter_size, quantization, _format_model_size(size)) if bit]
            options.append(
                {
                    "name": name,
                    "model": name,
                    "label": f"{name} · {' · '.join(bits)}" if bits else name,
                    "family": family,
                    "parameter_size": parameter_size,
                    "quantization": quantization,
                    "size_bytes": int(size or 0),
                    "size_label": _format_model_size(size),
                    "chat_capable": True,
                }
            )
        return sorted(options, key=lambda item: item["name"].lower())
    except Exception:
        return []


async def check_ollama_connection(model: str) -> tuple[bool, str, list[str]]:
    """
    Quick connectivity check. Returns (is_connected, status_message, available_models).
    Safe to call on startup without raising.

    Note: ollama 0.4+ returns pydantic models, not dicts.
    """
    try:
        client = build_provider_client(get_active_provider())
        result = await asyncio.wait_for(client.list(), timeout=3.0)

        available_names: list[str] = []
        for m in result.models:
            name = getattr(m, "model", None) or getattr(m, "name", "")
            available_names.append(str(name))

        model_pulled = any(model in name for name in available_names)
        if model_pulled:
            return True, f"connected · {model}", available_names
        return True, f"connected · {model} (not pulled)", available_names

    except asyncio.TimeoutError:
        return False, "timeout", []
    except Exception:
        return False, "offline", []


async def chat_with_tools(
    *,
    model: str,
    history: list[Message],
    on_chunk: Callable[[str], None],
    on_thinking: Callable[[str], None] | None = None,
    on_tool_start: Callable[[str, dict], None] | None = None,
    on_tool_done: Callable[[str, str], None] | None = None,
    on_phase: Callable[[str], None] | None = None,
    on_loading_hint: Callable[[], None] | None = None,
    provider_config: ModelProviderConfig | None = None,
    allowed_tool_names: list[str] | None = None,
    extra_system_prompt: str | None = None,
    on_shell_confirm: Callable[[str], object] | None = None,
) -> str:
    """
    Tool-enabled chat mit automatischer Tool-Ausführung.

    Ablauf:
        1. Non-streaming Aufruf mit Tool-Schemas → Tool-Calls detektieren
        2. Tools ausführen (max MAX_TOOL_ITERATIONS Iterationen)
        3. Finale Antwort als Text via on_chunk ausgeben

    WICHTIG: stream=False für Tool-Detection ist PFLICHT.
    Bekanntes Ollama-Limit: Tool-Calls brechen mit stream=True.

    Args:
        model:          Ollama Modell-Name
        history:        Konversations-History (role/content dicts)
        on_chunk:       Callback für jeden Text-Token der finalen Antwort
        on_tool_start:  Callback wenn Tool gestartet wird (name, args)
        on_tool_done:   Callback wenn Tool fertig ist (name, result)
        on_loading_hint: Callback wenn Modell zu lange lädt

    Raises:
        OllamaNotReachableError:    Ollama nicht erreichbar
        OllamaModelNotFoundError:   Modell nicht lokal vorhanden
        ShellConfirmationRequired:  Shell-Tool braucht User-Bestätigung
    """
    provider = provider_config or get_active_provider()
    client = build_provider_client(provider)
    messages: list = compact_history(list(history))
    tools = _tools_for_messages(messages, allowed_tool_names=allowed_tool_names)

    # ── System-Prompt mit Personalisierung injizieren ────────────────────
    context_parts = [NOX_SYSTEM_PROMPT]
    if messages and messages[0].get("role") == "system":
        context_parts.append(str(messages.pop(0).get("content", "")))
    if extra_system_prompt:
        context_parts.append(extra_system_prompt)

    try:
        profile_ctx = load_profile().to_context_string()
        if profile_ctx:
            context_parts.append(profile_ctx)
    except Exception:
        pass

    try:
        # User-Frage für semantische Suche extrahieren
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                break
        if user_query:
            memory_ctx = Memory().get_context_injection(user_query)
            if memory_ctx:
                context_parts.append(memory_ctx)
    except Exception:
        pass

    try:
        corrections_ctx = CorrectionJournal().to_context_string()
        if corrections_ctx:
            context_parts.append(corrections_ctx)
    except Exception:
        pass

    try:
        feedback_ctx = FeedbackStore().to_few_shot_string()
        if feedback_ctx:
            context_parts.append(feedback_ctx)
    except Exception:
        pass

    full_system_prompt = "\n\n".join(part for part in context_parts if part)
    messages.insert(0, {"role": "system", "content": full_system_prompt})

    # ── Schritt 1: Tool-Detection (stream=False – Pflicht!) ──────────────────
    TOOL_DETECT_TIMEOUT = _tool_detection_timeout(model)
    MAX_RETRIES = 0 if TOOL_DETECT_TIMEOUT <= TOOL_DETECT_TIMEOUT_SMALL_MODEL else 1

    if on_phase:
        on_phase("Analyzing request…")

    response = None
    fallback_used = False
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=model,
                    messages=messages,
                    tools=tools,
                    stream=False,
                    **_native_thinking_kwargs(model),
                ),
                timeout=TOOL_DETECT_TIMEOUT,
            )
            break  # Erfolg → Loop verlassen
        except asyncio.TimeoutError:
            if attempt < MAX_RETRIES:
                if on_phase:
                    on_phase("Loading model… (Retry)")
                continue  # Nochmal versuchen
            # Letzter Versuch auch Timeout -> prüfen ob Ollama eindeutig offline ist.
            # Wenn der Probe selbst hängt, ist Ollama oft nur mit Modell-Laden/GPU-Speicher
            # blockiert. Das darf im Frontend nicht als "Ollama nicht erreichbar" erscheinen.
            try:
                test_client = _ollama_async_client()
                await asyncio.wait_for(test_client.list(), timeout=3.0)
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(kw in exc_str for kw in ("connection", "connect", "refused", "socket")):
                    raise OllamaNotReachableError() from exc
            # Ollama lebt, aber Modell antwortet nicht → busy/loading
            raise OllamaModelBusyError(model, TOOL_DETECT_TIMEOUT)
        except Exception as exc:
            exc_str = str(exc).lower()
            fallback_model = os.environ.get("MIMI_NOX_FALLBACK_MODEL", "qwen3:4b")
            if (
                not fallback_used
                and fallback_model
                and fallback_model != model
                and not _has_uploaded_images(messages)
                and "requires more system memory" in exc_str
            ):
                fallback_used = True
                model = fallback_model
                if on_phase:
                    on_phase(f"Primary model needs more memory; retrying with {fallback_model}…")
                continue
            if any(kw in exc_str for kw in ("refused", "socket")):
                raise OllamaNotReachableError() from exc
            if "not found" in exc_str or "does not exist" in exc_str:
                raise OllamaModelNotFoundError(model) from exc
            raise

    if response is None:
        raise OllamaNotReachableError()

    # ── Schritt 2: Tool-Calling Loop ─────────────────────────────────────────
    iteration = 0

    while (
        hasattr(response, "message")
        and hasattr(response.message, "tool_calls")
        and response.message.tool_calls
        and iteration < MAX_TOOL_ITERATIONS
    ):
        iteration += 1
        if on_phase:
            on_phase(f"Tool round {iteration}…")

        # Assistenten-Nachricht mit tool_calls zur History hinzufügen
        messages.append(response.message)

        for tool_call in response.message.tool_calls:
            if isinstance(tool_call, dict):
                function = tool_call.get("function") or tool_call
                name = str(function.get("name", ""))
                args = function.get("arguments") or {}
            else:
                function = tool_call.function
                name = str(function.name)
                args = function.arguments or {}

            # Callback: Tool startet
            if on_tool_start is not None:
                on_tool_start(name, args)

            if name == "run_shell":
                command = args.get("command", "")
                if on_shell_confirm is None:
                    raise ShellConfirmationRequired(command)
                maybe_approved = on_shell_confirm(command)
                approved = await maybe_approved if hasattr(maybe_approved, "__await__") else bool(maybe_approved)
                result = await execute_confirmed_shell(command, confirmed=bool(approved))
            else:
                # Tool ausführen (Fehler werden in execute_tool abgefangen)
                result = await execute_tool(name, args)


            # Callback: Tool fertig
            if on_tool_done is not None:
                on_tool_done(name, result)

            # Tool-Ergebnis zur History hinzufügen
            normalized_result = normalize_tool_result(name, result)
            messages.append({
                "role": "tool",
                "content": result,
            })
            messages.append({
                "role": "system",
                "content": (
                    "Tool evidence summary:\n"
                    f"- tool: {normalized_result.tool}\n"
                    f"- status: {normalized_result.status}\n"
                    f"- summary: {normalized_result.summary}\n"
                    f"- artifacts: {normalized_result.artifacts}\n"
                    f"- warnings: {normalized_result.warnings}"
                ),
            })

        # Nächste Iteration: prüfen ob weitere Tool-Calls folgen
        if on_phase:
            on_phase("Processing results…")
        try:
            response = await client.chat(
                model=model,
                messages=messages,
                tools=tools,
                stream=False,
                **_native_thinking_kwargs(model),
            )
        except Exception as exc:
            exc_str = str(exc).lower()
            if any(kw in exc_str for kw in ("connection", "connect", "refused")):
                raise OllamaNotReachableError() from exc
            raise

    # Max Iterationen aufgebraucht?
    if iteration >= MAX_TOOL_ITERATIONS:
        warning = f"[⚠ Max tool iterations ({MAX_TOOL_ITERATIONS}) reached]"
        on_chunk(warning)
        return warning

    # ── Schritt 3: Finale Antwort ausgeben (Thinking-Tags parsen) ──────────
    if on_phase:
        on_phase("Generating response…")
    final_content: str = ""

    if hasattr(response, "message"):
        msg = response.message

        # ── Thinking aus Ollama's nativem Feld extrahieren ──────────────
        # Only models with native Ollama thinking enabled populate msg.thinking.
        if on_thinking and hasattr(msg, "thinking") and msg.thinking:
            thinking_text = str(msg.thinking)
            # Wort-für-Wort emittieren für smooth streaming feel
            words = thinking_text.split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                on_thinking(chunk)
                await asyncio.sleep(0.005)

        # ── Antwort-Content ausgeben ────────────────────────────────────
        if msg.content:
            raw_content = str(msg.content)
            parser = ThinkingStreamParser(on_chunk=on_chunk, on_thinking=on_thinking)
            # Wort-für-Wort ausgeben für smooth streaming Effekt
            words = raw_content.split(" ")
            delay = _stream_delay_seconds(len(words))
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                parser.feed(chunk)
                if delay > 0:
                    await asyncio.sleep(delay)
            parser.flush()
            final_content = parser.answer

    return final_content

"""server/routes/chat.py – POST /api/chat + POST /api/chat/stream (SSE)"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.chat import OllamaNotReachableError, OllamaModelNotFoundError, OllamaModelBusyError, chat_with_tools
from core.react import reflect, react_loop
from core.commands import is_learn_command, extract_learn_topic, is_swarm_command, extract_swarm_task
from core.skills import SkillLoader, SkillLoadError
from core.skill_fastpath import run_skill_fast_path
from core.artifact_detector import ArtifactDetector
from core.quality import evaluate_quality, normalize_tool_result, validate_artifact
from core.model_provider import (
    DEFAULT_OLLAMA_BASE_URL,
    ModelProviderConfig,
    ProviderSetupError,
    get_active_provider,
)

router = APIRouter(tags=["Chat"])

DEFAULT_MODEL = os.environ.get("MIMI_NOX_MODEL", "gemma4:12b")
FILE_MARKER_MAP = {
    "PDF_FILE:": ("pdf", "📄 PDF"),
    "DECK_STUDIO_FILE:": ("deck_studio", "🎛 Slide Studio"),
    "PITCH_DECK_FILE:": ("pdf", "📄 PDF Slides"),
    "PPTX_DECK_FILE:": ("pptx", "📊 Editable PPTX"),
    "PREVIEW_FILE:": ("html", "🌐 Animated Preview"),
    "CONTACT_SHEET_FILE:": ("html", "🧾 Contact Sheet"),
    "SCORECARD_FILE:": ("json", "📋 Quality Scorecard"),
    "QA_FILE:": ("json", "🧪 Deck QA"),
    "MANIFEST_FILE:": ("json", "🗂 Claim Manifest"),
    "RENDER_QA_FILE:": ("json", "🧪 Render QA"),
    "DECK_SPEC_FILE:": ("json", "🧭 Deck Spec"),
    "VISUAL_QA_FILE:": ("json", "🎨 Visual QA"),
    "EVIDENCE_LEDGER_FILE:": ("json", "📚 Evidence Ledger"),
    "SOURCE_BRIEF_FILE:": ("markdown", "📚 Source Brief"),
}


def _resolve_skill_invocation(message: str):
    """Return (skill, stripped_message) for explicit slash or high-confidence natural skill requests."""
    stripped = (message or "").strip()
    if not stripped.startswith("/"):
        lowered = stripped.lower()
        if "notebooklm" in lowered or "notebook lm" in lowered or "quellen-notebook" in lowered:
            notebook_skill = SkillLoader().resolve_trigger("/notebook")
            if notebook_skill:
                return notebook_skill, stripped
        skill = SkillLoader().resolve_for_message(stripped)
        return skill, stripped
    parts = stripped.split(maxsplit=1)
    trigger = parts[0]
    skill = SkillLoader().resolve_trigger(trigger)
    if not skill:
        return None, message
    user_content = parts[1].strip() if len(parts) > 1 else stripped
    return skill, user_content


def _emit_file_markers(text: str, emit) -> None:
    emitted: set[tuple[str, str]] = set()
    for marker, (file_type, label) in FILE_MARKER_MAP.items():
        if marker not in text:
            continue
        path = text.split(marker, 1)[1].splitlines()[0].strip()
        key = (file_type, path)
        if path and key not in emitted:
            emitted.add(key)
            emit({"type": "file_result", "file_type": file_type, "path": path, "label": label})
    summary_markers = (
        (r"Studio PPTX:\s*`([^`]+\.pptx)`", "PPTX_DECK_FILE:"),
        (r"PDF Slides:\s*`([^`]+\.pdf)`", "PITCH_DECK_FILE:"),
        (r"Animated Preview:\s*`([^`]+\.preview\.html)`", "PREVIEW_FILE:"),
        (r"Render QA:\s*`([^`]+\.render-qa\.json)`", "RENDER_QA_FILE:"),
        (r"Quality Scorecard:\s*`([^`]+\.scorecard\.json)`", "SCORECARD_FILE:"),
        (r"Contact Sheet:\s*`([^`]+\.contact-sheet\.html)`", "CONTACT_SHEET_FILE:"),
        (r"Deck Spec:\s*`([^`]+\.deck-spec\.json)`", "DECK_SPEC_FILE:"),
        (r"Visual QA:\s*`([^`]+\.visual-qa\.json)`", "VISUAL_QA_FILE:"),
        (r"Evidence Ledger:\s*`([^`]+\.evidence-ledger\.json)`", "EVIDENCE_LEDGER_FILE:"),
        (r"Source Brief:\s*`([^`]+\.md)`", "SOURCE_BRIEF_FILE:"),
    )
    for pattern, marker in summary_markers:
        file_type, label = FILE_MARKER_MAP[marker]
        for match in re.findall(pattern, text or ""):
            path = match.strip()
            key = (file_type, path)
            if path and key not in emitted:
                emitted.add(key)
                emit({"type": "file_result", "file_type": file_type, "path": path, "label": label})


def _normalize_fast_path_tool_results(text: str):
    results = []
    for marker in FILE_MARKER_MAP:
        if marker not in text:
            continue
        path = text.split(marker, 1)[1].splitlines()[0].strip()
        if path:
            results.append(normalize_tool_result("fast_path", f"{marker}{path}"))
    summary_markers = (
        (r"Studio PPTX:\s*`([^`]+\.pptx)`", "PPTX_DECK_FILE:"),
        (r"PDF Slides:\s*`([^`]+\.pdf)`", "PITCH_DECK_FILE:"),
        (r"Animated Preview:\s*`([^`]+\.preview\.html)`", "PREVIEW_FILE:"),
        (r"Render QA:\s*`([^`]+\.render-qa\.json)`", "RENDER_QA_FILE:"),
        (r"Quality Scorecard:\s*`([^`]+\.scorecard\.json)`", "SCORECARD_FILE:"),
        (r"Contact Sheet:\s*`([^`]+\.contact-sheet\.html)`", "CONTACT_SHEET_FILE:"),
        (r"Deck Spec:\s*`([^`]+\.deck-spec\.json)`", "DECK_SPEC_FILE:"),
        (r"Visual QA:\s*`([^`]+\.visual-qa\.json)`", "VISUAL_QA_FILE:"),
        (r"Evidence Ledger:\s*`([^`]+\.evidence-ledger\.json)`", "EVIDENCE_LEDGER_FILE:"),
        (r"Source Brief:\s*`([^`]+\.md)`", "SOURCE_BRIEF_FILE:"),
    )
    for pattern, marker in summary_markers:
        for match in re.findall(pattern, text or ""):
            results.append(normalize_tool_result("fast_path", f"{marker}{match.strip()}"))
    return results


def _contextualize_fast_path_content(user_content: str, history: list[dict]) -> str:
    """Attach the last substantive user intent for vague follow-up commands."""
    content = (user_content or "").strip()
    if not _is_vague_followup(content):
        return content

    previous = _last_substantive_user_message(history)
    if not previous:
        return content
    return "\n\n".join([
        content,
        f"Kontext aus vorheriger Anfrage: {previous}",
    ])


def _is_vague_followup(content: str) -> bool:
    stripped = re.sub(r"^/\w+\s*", " ", content or "", flags=re.IGNORECASE).strip().lower()
    if not stripped:
        return True
    substantive = re.sub(
        r"\b(mach(e|en)?|erstell(e|en)?|erstelle|das|die|der|den|mir|jetzt|etzt|richtig|nochmal|noch|file|datei|bitte|ok|ja)\b",
        " ",
        stripped,
        flags=re.IGNORECASE,
    )
    substantive = " ".join(substantive.split())
    return len(substantive) < 12


def _last_substantive_user_message(history: list[dict]) -> str:
    for item in reversed(history or []):
        if item.get("role") != "user":
            continue
        content = str(item.get("content") or "").strip()
        if not content or _is_vague_followup(content):
            continue
        return content[:1200]
    return ""


# ── Pydantic Models ────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    model: str = DEFAULT_MODEL
    history: list[dict] = []


class ChatResponse(BaseModel):
    response: str
    model: str


class StreamRequest(BaseModel):
    message: str
    model: str = DEFAULT_MODEL
    history: list[dict] = []
    autonomous: bool = False
    images: list[str] = []       # Base64-kodierte Bilder für 12B Multimodal
    force_tier: str | None = None  # Optional: "offline" | "fast" | "power"


class ApproveRequest(BaseModel):
    token: str
    approved: bool

# ── Request-scoped Sandbox State (T-02 Fix) ──────────────────────────────────
# ContextVar: Jeder asyncio-Request bekommt seinen eigenen Sandbox-Dict.
# Kein Leak zwischen simultanen Requests, auch mit uvicorn --workers N.
from contextvars import ContextVar as _ContextVar

_sandbox_store: _ContextVar[dict | None] = _ContextVar('nox_sandbox_store', default=None)


def get_sandbox() -> dict:
    """Gibt den request-scoped Sandbox-State-Dict zurück (erstellt ihn bei Bedarf)."""
    store = _sandbox_store.get()
    if store is None:
        store = {}
        _sandbox_store.set(store)
    return store


# Legacy-Alias — bleibt importierbar für Kompatibilität, wird nicht mehr befüllt
pending_sandbox: dict[str, dict] = {}  # DEPRECATED: nutze get_sandbox()

# App-weites Token-Registry für Cross-Request Sandbox-Approval
# (approve_sandbox läuft in eigenem Request-Context, daher kein ContextVar)
_active_sandbox_events: dict[str, dict] = {}


def _friendly_model_error(exc: Exception, provider: ModelProviderConfig | None = None) -> str:
    """Return a user-facing model error that matches the offline-first setup story."""
    raw = str(exc)
    lower = raw.lower()
    active = provider or get_active_provider()

    if active.provider == "local_ollama" and any(
        marker in lower
        for marker in (
            "failed to connect",
            "connection",
            "connecterror",
            "refused",
            "socket",
            "not running",
        )
    ):
        return (
            "Lokales Ollama ist gerade nicht erreichbar. "
            "Starte MiMi Nox mit `miminox start` oder prüfe mit `miminox doctor`."
        )

    if active.provider == "local_ollama" and any(
        marker in lower
        for marker in ("not found", "does not exist", "nicht installiert", "missing")
    ):
        return (
            f"Lokales Modell '{active.model}' fehlt oder ist nicht ladbar. "
            "Starte die Reparatur mit `miminox doctor` und danach `miminox start`."
        )

    return raw


def sandbox_auto_approval_allowed(*, autonomous: bool) -> bool:
    """Risky tools must always require explicit user approval."""
    return False


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Synchroner Chat-Endpunkt (wartet auf vollständige Antwort)."""
    provider = get_active_provider()
    model = provider.model if request.model == DEFAULT_MODEL else request.model
    try:
        response_text = await react_loop(
            question=request.message,
            model=model,
            context=request.history,
            provider_config=provider,
        )
        return ChatResponse(response=response_text or "", model=model)
    except ProviderSetupError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except OllamaNotReachableError:
        raise HTTPException(status_code=503, detail="Ollama nicht erreichbar. Starte mit: ollama serve")
    except OllamaModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Modell '{exc.model}' nicht installiert.")


@router.post("/chat/stream")
async def chat_stream(request: StreamRequest) -> StreamingResponse:
    """
    Transparentes Streaming via SSE.

    Event-Typen (jede Zeile: data: <JSON>\n\n):
      {"type": "chunk",    "data": "..."}          → Token sofort an AI-Bubble
      {"type": "thinking_start"}                   → Progress UI without raw reasoning
      {"type": "activity", "cmd": "...", "status": "running|done"} → Terminal-Feed
      {"type": "reflect",  "status": "running|done", "needs_revision": bool}
      {"type": "revision", "reason": "..."}         → Bubble resetten, neue Antwort
      {"type": "error",    "msg": "..."}            → Fehleranzeige
      {"type": "done"}                              → Cursor entfernen

    Ablauf:
      1. Erste Antwort SOFORT streamen (kein Buffering → Cursor sichtbar)
      2. Reflexion → Activity-Event im Terminal
      3. Wenn needs_revision: revision-event + überarbeitete Antwort streamen
      4. done
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def emit(event: dict) -> None:
            queue.put_nowait(event)

        async def run() -> None:
            messages = list(request.history)
            # ── Bilder in User-Message einbauen (12B Multimodal) ──────────
            active_skill, user_content = _resolve_skill_invocation(request.message)
            user_msg: dict = {"role": "user", "content": user_content}
            if request.images:
                user_msg["images"] = request.images
            messages.append(user_msg)

            # ── Modell via Hybrid-Router ermitteln ────────────────────────
            # Wenn force_tier gesetzt → Router gibt den erzwungenen Tier zurück
            # Wenn model == DEFAULT_MODEL → Router entscheidet automatisch
            # Wenn model explizit gesetzt → bleibt unverändert (Override)
            active_provider = get_active_provider()
            if request.force_tier:
                from core.model_router import get_router
                active_config = await get_router().resolve(
                    force_tier=request.force_tier
                )
                model = active_config.name
                active_provider = ModelProviderConfig(
                    provider="local_ollama",
                    model=model,
                    base_url=DEFAULT_OLLAMA_BASE_URL,
                    label="Local Ollama",
                    offline_capable=True,
                    requires_internet=False,
                )
                # Tier-Info an Frontend senden
                emit({"type": "model_info",
                      "tier": active_config.tier.value,
                      "model": model,
                      "provider": "local_ollama"})
            elif request.model == DEFAULT_MODEL:
                model = active_provider.model
                emit({"type": "model_info",
                      "tier": "provider",
                      "model": model,
                      "provider": active_provider.provider,
                      "offline_capable": active_provider.offline_capable,
                      "requires_internet": active_provider.requires_internet})
            else:
                model = request.model

            _done_sent = False
            try:
                # ── /swarm: Swarm V2 Pipeline ─────────────────────────────
                if is_swarm_command(request.message):
                    swarm_task = extract_swarm_task(request.message)
                    if not swarm_task:
                        emit({"type": "chunk", "data": "🐝 Nutzung: `/swarm <Aufgabe>` – z.B. `/swarm Analysiere 3 KI-Trends und fasse sie zusammen`"})
                        emit({"type": "done"})
                        _done_sent = True
                        return

                    emit({"type": "thinking_start"})
                    emit({"type": "swarm_status", "phase": "planning", "message": "🐝 Swarm V2 gestartet — Manager analysiert Aufgabe…"})

                    try:
                        from core.swarm_v2 import run_swarm_v2

                        result = await run_swarm_v2(
                            task=swarm_task,
                            model=model,
                            on_event=emit,
                        )
                        # Finale Synthese als Chunks streamen
                        if result.final:
                            words = result.final.split(" ")
                            for i, word in enumerate(words):
                                chunk = word + (" " if i < len(words) - 1 else "")
                                emit({"type": "chunk", "data": chunk})
                    except (OllamaNotReachableError, OllamaModelNotFoundError) as exc:
                        emit({"type": "error", "msg": str(exc)})
                    except Exception as exc:
                        emit({"type": "error", "msg": f"Swarm-Fehler: {exc}"})

                    emit({"type": "done"})
                    _done_sent = True
                    return

                # ── /learn: Skill-Builder-Pipeline ─────────────────────────
                if is_learn_command(request.message):
                    topic = extract_learn_topic(request.message)
                    if not topic:
                        emit({"type": "chunk", "data": "💡 Nutzung: `/learn <Thema>` – z.B. `/learn Wie wir FastAPI-Routen strukturieren`"})
                        emit({"type": "done"})
                        _done_sent = True
                        return

                    emit({"type": "thinking_start"})

                    def on_learn_chunk(chunk: str) -> None:
                        emit({"type": "chunk", "data": chunk})

                    def on_learn_phase(phase: str) -> None:
                        emit({"type": "activity", "cmd": phase, "status": "running"})

                    def on_learn_tool_start(name: str, args: dict) -> None:
                        emit({"type": "activity", "cmd": f"{name}({json.dumps(args, ensure_ascii=False)[:60]})", "status": "running"})

                    def on_learn_tool_done(name: str, result: str) -> None:
                        emit({"type": "activity", "cmd": f"{name} → {result[:40]}", "status": "done"})

                    try:
                        from core.skill_builder import build_skill

                        skill = await build_skill(
                            topic=topic,
                            model=model,
                            on_phase=on_learn_phase,
                            on_chunk=on_learn_chunk,
                            on_tool_start=on_learn_tool_start,
                            on_tool_done=on_learn_tool_done,
                        )
                        # Bestätigungs-Nachricht
                        emit({"type": "chunk", "data": f"\n\n✅ **Neuer Skill erstellt:** `{skill.name}` ({skill.trigger})\n"})
                        emit({"type": "chunk", "data": f"\n_{skill.description}_"})
                        # Skill-Created Event → Frontend lädt Chips neu
                        emit({"type": "skill_created", "skill": {
                            "name": skill.name,
                            "trigger": skill.trigger,
                            "description": skill.description,
                        }})
                    except (SkillLoadError, ValueError) as exc:
                        emit({"type": "chunk", "data": f"\n\n⚠️ Skill-Erstellung fehlgeschlagen: {exc}"})

                    emit({"type": "done"})
                    _done_sent = True
                    return

                # ── Sandbox Handler ─────────────────────────────────────────
                async def _sandbox_cb(name: str, args: dict) -> bool:
                    if sandbox_auto_approval_allowed(autonomous=request.autonomous):
                        return True
                    token = str(uuid.uuid4())
                    event = asyncio.Event()
                    # T-02: _active_sandbox_events ist app-weit (cross-request)
                    # damit approve_sandbox() den Token findet.
                    # get_sandbox() ist für request-internen State (nicht hier nötig).
                    _active_sandbox_events[token] = {"event": event, "approved": False}
                    emit({"type": "sandbox_confirm", "token": token, "tool": name, "args": args})
                    await event.wait()
                    res = _active_sandbox_events.pop(token, {"approved": False})
                    return res["approved"]

                # T-03: ContextVar-Setter statt Monkey-Patching
                from core.vision import (
                    set_sandbox_confirm_cb,
                    set_vision_learning_cb,
                    set_vision_learned_success_cb,
                )

                set_sandbox_confirm_cb(_sandbox_cb)

                async def _vision_learning_cb(target: str) -> None:
                    emit({"type": "vision_learning", "target": target})
                set_vision_learning_cb(_vision_learning_cb)

                async def _vision_learned_success_cb(target: str) -> None:
                    emit({"type": "vision_learned_success", "target": target})
                set_vision_learned_success_cb(_vision_learned_success_cb)

                async def _shell_confirm_cb(command: str) -> bool:
                    return await _sandbox_cb("run_shell", {"command": command})

                if active_skill and not request.images:
                    fast_user_content = _contextualize_fast_path_content(user_content, request.history)
                    fast_answer = await run_skill_fast_path(active_skill.name, fast_user_content)
                    if fast_answer is not None:
                        emit({"type": "activity", "cmd": f"{active_skill.trigger} fast path", "status": "done"})
                        _emit_file_markers(fast_answer, emit)
                        fast_tool_results = _normalize_fast_path_tool_results(fast_answer)
                        emit({"type": "quality_check", "status": "running", "skill": active_skill.name})
                        for tool_result in fast_tool_results:
                            for artifact in tool_result.artifacts:
                                validation = validate_artifact(artifact)
                                emit({
                                    "type": "artifact_check",
                                    "artifact_type": validation.artifact_type,
                                    "status": validation.status,
                                    "path": validation.path,
                                    "warnings": validation.warnings,
                                })
                        quality_report = evaluate_quality(
                            answer=fast_answer,
                            skill=active_skill,
                            tool_results=fast_tool_results,
                        )
                        emit({
                            "type": "quality_check",
                            "status": quality_report.status,
                            "skill": active_skill.name,
                            "issues": quality_report.issues,
                            "warnings": quality_report.warnings,
                        })
                        emit({"type": "chunk", "data": fast_answer})
                        emit({"type": "done"})
                        _done_sent = True
                        return

                # ── Phase 1: Erste Antwort sofort streamen ─────────────────
                first_chunks: list[str] = []
                captured_tool_results = []

                def on_chunk(chunk: str) -> None:
                    first_chunks.append(chunk)
                    emit({"type": "chunk", "data": chunk})

                def on_thinking(chunk: str) -> None:
                    # Internal model reasoning must not cross the API boundary.
                    _ = chunk

                def on_tool_start(name: str, args: dict) -> None:
                    emit({"type": "activity", "cmd": f"{name}({json.dumps(args, ensure_ascii=False)[:60]})", "status": "running"})

                def on_tool_done(name: str, result: str) -> None:
                    tool_result = normalize_tool_result(name, result)
                    captured_tool_results.append(tool_result)
                    # Datei-Outputs speziell behandeln → file_result Event
                    if result.startswith("CHART_FILE:"):
                        path = result[len("CHART_FILE:"):]
                        emit({"type": "file_result", "file_type": "chart", "path": path,
                              "label": f"📊 Chart erstellt"})
                        emit({"type": "activity", "cmd": f"{name} → Chart gespeichert ✅", "status": "done"})
                    elif result.startswith("PDF_FILE:"):
                        path = result[len("PDF_FILE:"):]
                        emit({"type": "file_result", "file_type": "pdf", "path": path,
                              "label": f"📄 PDF: {path.split('/')[-1]}"})
                        emit({"type": "activity", "cmd": f"{name} → PDF gespeichert ✅", "status": "done"})
                    elif result.startswith("SVG_FILE:"):
                        path = result[len("SVG_FILE:"):]
                        emit({"type": "file_result", "file_type": "svg", "path": path,
                              "label": f"🎨 SVG: {path.split('/')[-1]}"})
                        emit({"type": "activity", "cmd": f"{name} → SVG gespeichert ✅", "status": "done"})
                    else:
                        emit({"type": "activity", "cmd": f"{name} → {result[:40]}", "status": "done"})

                    for artifact in tool_result.artifacts:
                        validation = validate_artifact(artifact)
                        emit({
                            "type": "artifact_check",
                            "artifact_type": validation.artifact_type,
                            "status": validation.status,
                            "path": validation.path,
                            "warnings": validation.warnings,
                        })

                def on_phase(phase: str) -> None:
                    emit({"type": "activity", "cmd": phase, "status": "running"})

                # SOFORT Thinking-Event senden → User sieht was passiert
                emit({"type": "thinking_start"})

                await chat_with_tools(
                    model=model,
                    history=messages,
                    on_chunk=on_chunk,
                    on_thinking=on_thinking,
                    on_tool_start=on_tool_start,
                    on_tool_done=on_tool_done,
                    on_phase=on_phase,
                    provider_config=active_provider,
                    allowed_tool_names=active_skill.tools if active_skill else None,
                    extra_system_prompt=active_skill.system_prompt if active_skill else None,
                    on_shell_confirm=_shell_confirm_cb,
                )

                first_answer = "".join(first_chunks)

                # ── Deterministische lokale Qualitätsprüfung ────────────────
                skill_quality_passed = False
                if active_skill:
                    emit({"type": "quality_check", "status": "running", "skill": active_skill.name})
                    quality_report = evaluate_quality(
                        answer=first_answer,
                        skill=active_skill,
                        tool_results=captured_tool_results,
                    )
                    emit({
                        "type": "quality_check",
                        "status": quality_report.status,
                        "skill": active_skill.name,
                        "issues": quality_report.issues,
                        "warnings": quality_report.warnings,
                    })
                    skill_quality_passed = quality_report.status == "passed"

                # ── Artifact-Erkennung ─────────────────────────────────────────────
                _detector    = ArtifactDetector()
                _artifacts   = _detector.detect(first_answer)
                if _artifacts:
                    # Bubble-Text ohne Code (Placeholder stattdessen)
                    clean_text = _detector.extract_text(first_answer)
                    emit({"type": "replace_text", "text": clean_text})
                    for art in _artifacts:
                        emit({"type": "artifact", "artifact": art.to_dict()})

                if active_skill and skill_quality_passed:
                    emit({"type": "done"})
                    _done_sent = True
                    return

                # ── Phase 2: Reflexion ─────────────────────────────────────
                emit({"type": "reflect", "status": "running"})
                reflexion = await reflect(
                    response=first_answer,
                    question=request.message,
                    model=model,
                    provider_config=active_provider,
                )
                emit({"type": "reflect", "status": "done", "needs_revision": reflexion.needs_revision})

                if not reflexion.needs_revision:
                    emit({"type": "done"})
                    _done_sent = True
                    return

                # ── Phase 3: Revision ──────────────────────────────────────
                emit({"type": "revision", "reason": reflexion.reason[:200]})

                messages.append({"role": "assistant", "content": first_answer})
                messages.append({
                    "role": "user",
                    "content": (
                        f"Deine Antwort war unvollständig.\n"
                        f"Kritik: {reflexion.reason}\n\n"
                        f"Bitte gib eine verbesserte, vollständige Antwort."
                    ),
                })

                def on_chunk_rev(chunk: str) -> None:
                    emit({"type": "chunk", "data": chunk})

                await chat_with_tools(
                    model=model,
                    history=messages,
                    on_chunk=on_chunk_rev,
                    on_thinking=on_thinking,
                    on_tool_start=on_tool_start,
                    on_tool_done=on_tool_done,
                    on_phase=on_phase,
                    provider_config=active_provider,
                    allowed_tool_names=active_skill.tools if active_skill else None,
                    extra_system_prompt=active_skill.system_prompt if active_skill else None,
                    on_shell_confirm=_shell_confirm_cb,
                )

            except ProviderSetupError as exc:
                emit({"type": "error", "msg": str(exc)})
            except OllamaNotReachableError:
                emit({"type": "error", "msg": "Ollama nicht erreichbar — starte: ollama serve"})
            except OllamaModelBusyError as exc:
                emit({"type": "error", "msg": f"⏳ Modell beschäftigt – bitte nochmal versuchen (Timeout nach {exc.timeout:.0f}s)"})
            except OllamaModelNotFoundError as exc:
                emit({"type": "error", "msg": f"Modell '{exc.model}' nicht installiert"})
            except Exception as exc:
                emit({"type": "error", "msg": _friendly_model_error(exc, active_provider)})
            finally:
                if not _done_sent:
                    emit({"type": "done"})
                queue.put_nowait(None)  # Sentinel

        task = asyncio.create_task(run())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            # Client hat die Verbindung abgebrochen (Senden-Button "Stopp")
            task.cancel()
            raise
        finally:
            try:
                await task
            except asyncio.CancelledError:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/sandbox/approve")
async def approve_sandbox(req: ApproveRequest):
    """Nimmt Sandbox-Bestätigungen (y/n) aus dem UI entgegen.

    NOTE: Dieses Endpoint arbeitet mit dem app-weiten _active_sandbox_events-
    Registry, nicht mit dem request-scoped get_sandbox(). Tokens werden von
    _sandbox_cb() registriert und hier aufgelöst.
    """
    if req.token in _active_sandbox_events:
        _active_sandbox_events[req.token]["approved"] = req.approved
        _active_sandbox_events[req.token]["event"].set()
        return {"status": "ok"}
    raise HTTPException(404, "Sandbox Token nicht gefunden oder abgelaufen")

class AutonomousRequest(BaseModel):
    enabled: bool

@router.post("/settings/autonomous")
async def set_autonomous(req: AutonomousRequest):
    """Schaltet den Autonomen Modus für GUI Fernsteuerung ein/aus."""
    os.environ["MIMI_NOX_AUTONOMOUS_MODE"] = "1" if req.enabled else "0"
    return {"status": "ok", "autonomous": req.enabled}

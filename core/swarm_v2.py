"""
◑ MiMi Nox – Swarm Engine V2
core/swarm_v2.py

Autonomes Swarm-System mit:
  - Manager-Agent (Gemma4 12B) entscheidet via Function Calling über Spawning
  - SwarmAgent: autonomer Worker mit eigenem Ollama-Client + Tool-Zugriff
  - SwarmOrchestrator: steuert Lifecycle, SSE-Events, Synthese

Architektur:

    ┌──────────────┐
    │  MANAGER     │  Gemma4 12B + spawn_swarm Tool
    └──────┬───────┘
           │ spawn_swarm({count, role, subtasks})
    ┌──────▼─────────────────────────────────┐
    │     asyncio.create_task() × N          │  ← PARALLEL
    │  SwarmAgent1  SwarmAgent2  Agent3 ...  │
    │  (eigener Client, eigener Prompt)      │
    │  → terminate_self() wenn fertig        │
    └──────┬─────────────────────────────────┘
           │ N Ergebnisse via SharedState
    ┌──────▼───────┐
    │  SYNTHESIZER │  fasst alles zusammen
    └──────────────┘

Design:
  - Pure async Python, kein threading
  - on_event Callback für SSE-Bridge (Server-Integration)
  - SwarmAgent hat Tool-Calling via chat_with_tools (konfigurierbare Whitelist)
  - Self-Termination: Agent ruft terminate_self → Task beendet sich
  - Fail-safe: Agent-Exceptions werden gefangen, andere laufen weiter

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import asyncio
import json
import re
import logging
from collections.abc import Callable
from dataclasses import dataclass

import ollama

from core.chat import OllamaModelNotFoundError, OllamaNotReachableError
from core.swarm_state import (
    AgentStatus,
    SwarmPhase,
    SwarmStateStore,
    swarm_state_store,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_SWARM_AGENTS = 8
DEFAULT_TOOL_WHITELIST = [
    "web_search", "browser_go", "browser_screenshot", "browser_click",
    "browser_type", "browser_press", "read_file", "list_directory",
    "file_search", "load_workspace", "get_datetime", "analyze_image",
]
AGENT_TIMEOUT = 120.0  # Max seconds per agent

# ── Prompts ────────────────────────────────────────────────────────────────────

MANAGER_SYSTEM = """\
Du bist der Manager-Agent von MiMi Nox. Deine Aufgabe ist, komplexe Aufgaben zu analysieren
und bei Bedarf einen Schwarm spezialisierter Agenten zu spawnen.

ANALYSE-STRATEGIE:
1. Lies die Aufgabe sorgfältig
2. Entscheide: Kann ich das alleine lösen, oder brauche ich parallele Helfer?
3. Wenn parallele Helfer nötig: nutze das spawn_swarm Tool

REGELN FÜR SPAWN-ENTSCHEIDUNGEN:
- Spawne NUR wenn die Aufgabe klar in unabhängige Teilaufgaben zerlegbar ist
- Spawne 2-6 Agenten (nicht mehr, nicht weniger)
- Jeder Agent braucht eine KLARE, ABGESCHLOSSENE Teilaufgabe
- Rollen: researcher, writer, analyzer, summarizer, coder, reviewer

Wenn du spawn_swarm NICHT brauchst, löse die Aufgabe direkt selbst.\
"""

SPECIALIST_SYSTEM_TEMPLATE = """\
Du bist ein spezialisierter Swarm-Agent mit der Rolle: {role}

Deine EINZIGE Aufgabe: {subtask}

Kontext der Gesamtaufgabe: {main_task}

REGELN:
- Fokussiere dich NUR auf deine Teilaufgabe
- Sei präzise und gründlich
- Nutze verfügbare Tools wenn nötig (web_search, browser_go, read_file, etc.)
- Wenn du fertig bist, rufe terminate_self() auf
- Dein Ergebnis wird von einem Synthesizer mit den Ergebnissen anderer Agenten zusammengeführt\
"""

SYNTHESIZER_SYSTEM = """\
Du bist der Synthese-Agent. Kombiniere die Ergebnisse mehrerer Spezialisten-Agenten
zu einer kohärenten, gut strukturierten Gesamtantwort.

REGELN:
- Vermeide Duplikate
- Strukturiere mit Markdown (Überschriften, Listen, Code-Blöcke)
- Sei klar und handlungsorientiert
- Erwähne NICHT dass die Antwort von verschiedenen Agenten stammt
- Formuliere als wäre es eine einzige, durchdachte Antwort\
"""


# ── Swarm Tool Schemas ─────────────────────────────────────────────────────────

def get_spawn_swarm_schema() -> dict:
    """Tool-Schema für spawn_swarm (nur für Manager-Agent)."""
    return {
        "type": "function",
        "function": {
            "name": "spawn_swarm",
            "description": (
                "Spawne einen Schwarm spezialisierter Agenten für parallele Aufgabenverarbeitung. "
                "Nutze dieses Tool wenn eine Aufgabe in unabhängige Teilaufgaben zerlegbar ist."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Anzahl der zu spawnenden Agenten (2-8)",
                    },
                    "role": {
                        "type": "string",
                        "description": (
                            "Rolle aller Agenten. Eine von: researcher, writer, analyzer, "
                            "summarizer, coder, reviewer"
                        ),
                    },
                    "subtasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste der Teilaufgaben – eine pro Agent",
                    },
                },
                "required": ["count", "role", "subtasks"],
            },
        },
    }


def get_terminate_self_schema() -> dict:
    """Tool-Schema für terminate_self (für Swarm-Agenten)."""
    return {
        "type": "function",
        "function": {
            "name": "terminate_self",
            "description": (
                "Beende diesen Swarm-Agenten. Rufe dies auf, wenn deine Teilaufgabe "
                "vollständig erledigt ist. Dein Ergebnis wird gespeichert."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    }


# ── Exceptions ─────────────────────────────────────────────────────────────────

class SwarmAgentTerminated(Exception):
    """Signalisiert dass ein Agent sich via terminate_self beendet hat."""
    pass


# ── SwarmAgent ─────────────────────────────────────────────────────────────────

class SwarmAgent:
    """
    Ein autonomer Swarm-Worker mit eigenem LLM-Kontext und Tool-Zugriff.

    Lifecycle:
        1. __init__: Agent wird konfiguriert (role, subtask, tools)
        2. run(): Agent arbeitet autonom mit chat + tool-calling
        3. terminate_self oder natürliches Ende → Ergebnis im SharedState
    """

    def __init__(
        self,
        *,
        agent_id: str,
        role: str,
        subtask: str,
        main_task: str,
        model: str,
        state_store: SwarmStateStore,
        swarm_id: str,
        tool_whitelist: list[str] | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.subtask = subtask
        self.main_task = main_task
        self.model = model
        self.state = state_store
        self.swarm_id = swarm_id
        self.tool_whitelist = tool_whitelist or DEFAULT_TOOL_WHITELIST
        self._terminated = False

    async def run(self) -> str:
        """
        Hauptloop: LLM-Aufruf mit Tool-Calling.
        Gibt das Ergebnis als String zurück.
        """
        await self.state.update_agent_status(
            self.agent_id, AgentStatus.RUNNING, f"Starte: {self.subtask[:60]}…"
        )

        system_prompt = SPECIALIST_SYSTEM_TEMPLATE.format(
            role=self.role,
            subtask=self.subtask,
            main_task=self.main_task,
        )

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": self.subtask},
        ]

        # Tools: gefilterte Schemas + terminate_self
        tools = self._get_tools()

        client = ollama.AsyncClient()
        result_text = ""
        max_iterations = 5

        try:
            for iteration in range(max_iterations):
                if self._terminated:
                    break

                response = await asyncio.wait_for(
                    client.chat(
                        model=self.model,
                        messages=messages,
                        tools=tools,
                        stream=False,
                    ),
                    timeout=AGENT_TIMEOUT,
                )

                # Tool-Calls verarbeiten
                if (
                    hasattr(response, "message")
                    and hasattr(response.message, "tool_calls")
                    and response.message.tool_calls
                ):
                    messages.append(response.message)

                    for tool_call in response.message.tool_calls:
                        name = tool_call.function.name
                        args = tool_call.function.arguments or {}

                        # terminate_self → Agent beendet sich
                        if name == "terminate_self":
                            self._terminated = True
                            await self.state.add_tool_used(self.agent_id, name)
                            messages.append({
                                "role": "tool",
                                "content": "Agent erfolgreich terminiert.",
                            })
                            break

                        # run_shell blockieren (Sicherheit)
                        if name == "run_shell":
                            messages.append({
                                "role": "tool",
                                "content": "[Swarm-Agenten dürfen keine Shell-Befehle ausführen.]",
                            })
                            continue

                        # Tool whitelist prüfen
                        if name not in self.tool_whitelist:
                            messages.append({
                                "role": "tool",
                                "content": f"[Tool '{name}' nicht in der Whitelist dieses Agenten.]",
                            })
                            continue

                        # Tool ausführen
                        await self.state.update_agent_status(
                            self.agent_id,
                            AgentStatus.RUNNING,
                            f"{name}({json.dumps(args, ensure_ascii=False)[:50]})",
                        )
                        await self.state.add_tool_used(self.agent_id, name)

                        from core.tools import execute_tool, ShellConfirmationRequired
                        try:
                            tool_result = await execute_tool(name, args)
                        except ShellConfirmationRequired:
                            tool_result = "[Shell-Bestätigung in Swarm nicht verfügbar.]"
                        except Exception as exc:
                            tool_result = f"[Tool-Fehler: {exc}]"

                        messages.append({
                            "role": "tool",
                            "content": tool_result,
                        })

                    if self._terminated:
                        # Ergebnis aus den bisherigen Messages extrahieren
                        result_text = self._extract_result(messages)
                        break

                    continue  # Nächste Iteration nach Tool-Calls

                # Keine Tool-Calls → finale Antwort
                if hasattr(response, "message") and response.message.content:
                    result_text = str(response.message.content).strip()
                break  # Fertig

        except asyncio.TimeoutError:
            result_text = f"[Agent {self.agent_id} Timeout nach {AGENT_TIMEOUT}s]"
            await self.state.set_agent_error(self.agent_id, "Timeout")
            return result_text
        except Exception as exc:
            result_text = f"[Agent {self.agent_id} Fehler: {exc}]"
            await self.state.set_agent_error(self.agent_id, str(exc))
            return result_text

        # Ergebnis speichern
        await self.state.set_agent_result(self.agent_id, result_text)
        if not self._terminated:
            await self.state.update_agent_status(
                self.agent_id, AgentStatus.DONE, "Aufgabe erledigt"
            )
        else:
            await self.state.terminate_agent(self.agent_id)

        return result_text

    def _get_tools(self) -> list[dict]:
        """Erstellt die Tool-Schemas für diesen Agenten (gefiltert + terminate_self)."""
        from core.tools import get_tool_schemas

        all_tools = get_tool_schemas()
        filtered = [
            t for t in all_tools
            if t.get("function", {}).get("name") in self.tool_whitelist
        ]
        filtered.append(get_terminate_self_schema())
        return filtered

    def _extract_result(self, messages: list[dict]) -> str:
        """Extrahiert das letzte sinnvolle Ergebnis aus der Message-History."""
        # Suche die letzte Assistant-Nachricht mit Content
        for msg in reversed(messages):
            role = msg.get("role", "") if isinstance(msg, dict) else getattr(msg, "role", "")
            content = ""
            if isinstance(msg, dict):
                content = msg.get("content", "")
            elif hasattr(msg, "content"):
                content = str(msg.content or "")
            if role == "assistant" and content and "terminate" not in content.lower():
                return content
        return f"[Agent {self.agent_id}: Aufgabe über terminate_self abgeschlossen]"


# ── SwarmOrchestrator ──────────────────────────────────────────────────────────

class SwarmOrchestrator:
    """
    Steuert den gesamten Swarm-Lifecycle.

    1. Manager-Agent analysiert die Aufgabe
    2. Manager spawnt via spawn_swarm Tool
    3. N SwarmAgents laufen parallel
    4. Synthesizer fasst Ergebnisse zusammen

    Usage:
        orchestrator = SwarmOrchestrator(
            task="Analysiere 3 KI-Trends",
            model="gemma4:12b",
            on_event=emit,
        )
        result = await orchestrator.run()
    """

    def __init__(
        self,
        *,
        task: str,
        model: str,
        on_event: Callable[[dict], None] | None = None,
        state_store: SwarmStateStore | None = None,
        tool_whitelist: list[str] | None = None,
    ) -> None:
        self.task = task
        self.model = model
        self.on_event = on_event or (lambda e: None)
        self.state = state_store or swarm_state_store
        self.tool_whitelist = tool_whitelist or DEFAULT_TOOL_WHITELIST
        self.swarm_id = ""
        self._spawn_result: dict | None = None

    async def run(self) -> SwarmV2Result:
        """
        Führt den gesamten Swarm-Pipeline aus.

        Returns:
            SwarmV2Result mit allen Agenten-Ergebnissen und der finalen Synthese.
        """
        # Session erstellen
        self.swarm_id = self.state.create_session(self.task)
        self.state.subscribe(self.on_event)

        try:
            return await self._execute_pipeline()
        finally:
            self.state.unsubscribe(self.on_event)

    async def _execute_pipeline(self) -> SwarmV2Result:
        """Interne Pipeline: Manager → Spawn → Execute → Synthesize."""

        # ── Phase 1: Manager analysiert und spawnt ─────────────────────────
        await self.state.update_session_phase(self.swarm_id, SwarmPhase.PLANNING)

        spawn_params = await self._run_manager()

        if not spawn_params:
            # Manager hat direkt geantwortet (kein Spawn nötig)
            await self.state.update_session_phase(self.swarm_id, SwarmPhase.DONE)
            return SwarmV2Result(
                swarm_id=self.swarm_id,
                task=self.task,
                subtasks=[],
                agent_results=[],
                final=self._spawn_result.get("direct_answer", "") if self._spawn_result else "",
            )

        # ── Phase 2: Agenten spawnen ───────────────────────────────────────
        await self.state.update_session_phase(self.swarm_id, SwarmPhase.SPAWNING)

        count = min(spawn_params.get("count", 2), MAX_SWARM_AGENTS)
        role = spawn_params.get("role", "researcher")
        subtasks = spawn_params.get("subtasks", [self.task])

        # Subtasks auf count angleichen
        while len(subtasks) < count:
            subtasks.append(self.task)
        subtasks = subtasks[:count]

        agents: list[SwarmAgent] = []
        for i, subtask in enumerate(subtasks):
            agent_id = self.state.register_agent(self.swarm_id, role, subtask)
            agent = SwarmAgent(
                agent_id=agent_id,
                role=role,
                subtask=subtask,
                main_task=self.task,
                model=self.model,
                state_store=self.state,
                swarm_id=self.swarm_id,
                tool_whitelist=self.tool_whitelist,
            )
            agents.append(agent)

        # ── Phase 3: Parallele Ausführung ──────────────────────────────────
        await self.state.update_session_phase(self.swarm_id, SwarmPhase.EXECUTING)

        agent_tasks = [asyncio.create_task(agent.run()) for agent in agents]
        results: list[str] = []

        # Warte auf alle mit individueller Fehlerbehandlung
        done_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        for i, result in enumerate(done_results):
            if isinstance(result, Exception):
                logger.error(f"Agent {agents[i].agent_id} crashed: {result}")
                results.append(f"[Agent-Fehler: {result}]")
            else:
                results.append(result or "")

        # ── Phase 4: Synthese ──────────────────────────────────────────────
        await self.state.update_session_phase(self.swarm_id, SwarmPhase.SYNTHESIZING)

        final = await self._synthesize(subtasks, results)

        await self.state.set_session_result(self.swarm_id, final)
        await self.state.update_session_phase(self.swarm_id, SwarmPhase.DONE)

        # swarm_done Event
        self.on_event({
            "type": "swarm_done",
            "swarm_id": self.swarm_id,
            "agent_count": len(agents),
            "final": final,
        })

        return SwarmV2Result(
            swarm_id=self.swarm_id,
            task=self.task,
            subtasks=subtasks,
            agent_results=results,
            final=final,
        )

    async def _run_manager(self) -> dict | None:
        """
        Manager-Agent: analysiert Task und entscheidet über Spawning.

        Returns:
            dict mit spawn_params wenn Spawning nötig, None wenn Manager direkt antwortet.
        """
        client = ollama.AsyncClient()
        tools = [get_spawn_swarm_schema()]

        messages = [
            {"role": "system", "content": MANAGER_SYSTEM},
            {"role": "user", "content": self.task},
        ]

        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    stream=False,
                ),
                timeout=60.0,
            )
        except Exception as exc:
            msg = str(exc).lower()
            if any(k in msg for k in ("connection", "refused", "socket")):
                raise OllamaNotReachableError() from exc
            if "not found" in msg:
                raise OllamaModelNotFoundError(self.model) from exc
            raise

        # Tool-Call prüfen
        if (
            hasattr(response, "message")
            and hasattr(response.message, "tool_calls")
            and response.message.tool_calls
        ):
            for tool_call in response.message.tool_calls:
                if tool_call.function.name == "spawn_swarm":
                    params = tool_call.function.arguments or {}
                    logger.info(f"◑ Manager spawnt Swarm: {params}")
                    return params

        # Kein Tool-Call → Manager hat direkt geantwortet
        direct = ""
        if hasattr(response, "message") and response.message.content:
            direct = str(response.message.content).strip()

        self._spawn_result = {"direct_answer": direct}
        return None

    async def _synthesize(self, subtasks: list[str], results: list[str]) -> str:
        """Synthese-Agent: kombiniert Agenten-Ergebnisse zu einer Antwort."""
        parts = [f"Originalaufgabe: {self.task}\n"]
        for i, (subtask, result) in enumerate(zip(subtasks, results), 1):
            parts.append(f"Teilaufgabe {i}: {subtask}\nErgebnis:\n{result}")

        combined = "\n\n---\n\n".join(parts)

        client = ollama.AsyncClient()
        try:
            response = await asyncio.wait_for(
                client.chat(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYNTHESIZER_SYSTEM},
                        {"role": "user", "content": combined},
                    ],
                    stream=False,
                ),
                timeout=90.0,
            )
            # Robuster Zugriff: Pydantic-Objekt (Ollama ≥ 0.4) ODER Dict
            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = getattr(getattr(response, "message", None), "content", "") or ""
            return str(content).strip()
        except Exception as exc:
            logger.error(f"◑ Synthesizer-Fehler: {exc}")
            # Fallback: Ergebnisse einfach zusammenfügen
            return "\n\n---\n\n".join(
                f"## Teilaufgabe {i+1}\n{r}" for i, r in enumerate(results)
            )


# ── Result ─────────────────────────────────────────────────────────────────────

@dataclass
class SwarmV2Result:
    """Ergebnis eines Swarm V2 Runs."""
    swarm_id: str
    task: str
    subtasks: list[str]
    agent_results: list[str]
    final: str

    def __repr__(self) -> str:
        return (
            f"SwarmV2Result(swarm_id={self.swarm_id!r}, "
            f"agents={len(self.subtasks)}, "
            f"final_len={len(self.final)})"
        )


# ── Public API ─────────────────────────────────────────────────────────────────

async def run_swarm_v2(
    *,
    task: str,
    model: str,
    on_event: Callable[[dict], None] | None = None,
    state_store: SwarmStateStore | None = None,
    tool_whitelist: list[str] | None = None,
) -> SwarmV2Result:
    """
    Convenience-Funktion: Erstellt und führt einen SwarmOrchestrator aus.

    Args:
        task:           Die Aufgabe
        model:          Ollama Modell
        on_event:       SSE-Bridge Callback
        state_store:    Optional: eigener State-Store (für Tests)
        tool_whitelist: Optional: Tools für Agenten (Default: alle read-safe Tools)

    Returns:
        SwarmV2Result
    """
    orchestrator = SwarmOrchestrator(
        task=task,
        model=model,
        on_event=on_event,
        state_store=state_store,
        tool_whitelist=tool_whitelist,
    )
    return await orchestrator.run()

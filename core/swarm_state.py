"""
◑ MiMi Nox – Swarm Shared State Store
core/swarm_state.py

Thread-safe Shared State für alle Swarm-Agenten.
Ermöglicht Status-Tracking, Pub/Sub-Events für SSE, und Agent-Lifecycle-Management.

Design:
  - Alle Mutations via async Lock (kein threading.Lock – wir sind in asyncio)
  - subscribe() registriert Callbacks für SSE-Bridge
  - In-Memory Store als Default (T-09: Optional SQLite-Backend)
  - Agent-Lifecycle: SPAWNED → RUNNING → DONE | ERROR | TERMINATED
  - T-10: Budget-Tracker pro Swarm-Session

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import asyncio
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ── Enums ──────────────────────────────────────────────────────────────────────

class AgentStatus(str, Enum):
    """Lifecycle-Status eines einzelnen Swarm-Agenten."""
    SPAWNED    = "spawned"
    RUNNING    = "running"
    DONE       = "done"
    ERROR      = "error"
    TERMINATED = "terminated"


class SwarmPhase(str, Enum):
    """Phase des gesamten Swarm-Runs."""
    PLANNING     = "planning"
    SPAWNING     = "spawning"
    EXECUTING    = "executing"
    SYNTHESIZING = "synthesizing"
    DONE         = "done"
    ERROR        = "error"


# ── Exceptions (T-10) ──────────────────────────────────────────────────────────

class BudgetExceededError(Exception):
    """Wird geworfen wenn das Token-Budget einer Session überschritten wurde."""
    def __init__(self, swarm_id: str, used: int, limit: int):
        super().__init__(
            f"Swarm '{swarm_id}' hat das Token-Budget überschritten: {used}/{limit} Tokens"
        )
        self.swarm_id = swarm_id
        self.used     = used
        self.limit    = limit


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    """Zustand eines einzelnen Swarm-Agenten."""
    agent_id:        str
    role:            str
    subtask:         str
    status:          AgentStatus = AgentStatus.SPAWNED
    result:          str         = ""
    error:           str         = ""
    progress_detail: str         = ""
    tools_used:      list[str]   = field(default_factory=list)
    created_at:      float       = field(default_factory=time.time)
    finished_at:     float | None = None


@dataclass
class SwarmSession:
    """Metadaten eines gesamten Swarm-Runs."""
    swarm_id:     str
    task:         str
    phase:        SwarmPhase  = SwarmPhase.PLANNING
    agent_ids:    list[str]   = field(default_factory=list)
    final_result: str         = ""
    created_at:   float       = field(default_factory=time.time)
    finished_at:  float | None = None


# ── Shared State Store ─────────────────────────────────────────────────────────

class SwarmStateStore:
    """
    Shared State für Swarm-Agenten.

    Thread-safe via asyncio.Lock.
    Pub/Sub via Callbacks für SSE-Bridge.

    T-09: Optional SQLite-Backend für Persistenz über Neustarts hinweg.
    T-10: Budget-Tracker: token_budget=N blockiert Agent-Spawns bei Überschreitung.
    T-12: add_tool_used() ist dedupliziert via Lock.

    Usage:
        store = SwarmStateStore()                          # In-Memory (default)
        store = SwarmStateStore(db_path="/data/swarm.db") # SQLite-Persistenz
        store = SwarmStateStore(token_budget=50_000)       # Mit Budget
    """

    def __init__(
        self,
        db_path:      str | None = None,
        token_budget: int | None = None,
    ) -> None:
        self._lock         = asyncio.Lock()
        self._db_path      = db_path
        self._token_budget = token_budget

        # T-10: Token-Tracking
        self._session_tokens: dict[str, int] = {}   # swarm_id → gesamt tokens
        self._agent_tokens:   dict[str, int] = {}   # agent_id → tokens

        if db_path:
            # T-09: SQLite-Backend
            self._db: sqlite3.Connection | None = sqlite3.connect(
                db_path, check_same_thread=False
            )
            self._db.row_factory = sqlite3.Row
            self._init_sqlite_schema()
            self._agents:   dict[str, AgentState]   = self._load_agents_from_db()
            self._sessions: dict[str, SwarmSession] = self._load_sessions_from_db()
        else:
            self._db      = None
            self._agents   = {}
            self._sessions = {}

        self._subscribers: list[Callable[[dict], None]] = []

    # ── T-09: SQLite Schema & Persistenz ────────────────────────────────────

    def _init_sqlite_schema(self) -> None:
        assert self._db is not None
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                swarm_id     TEXT PRIMARY KEY,
                task         TEXT NOT NULL,
                phase        TEXT NOT NULL DEFAULT 'planning',
                agent_ids    TEXT NOT NULL DEFAULT '',
                final_result TEXT NOT NULL DEFAULT '',
                created_at   REAL NOT NULL,
                finished_at  REAL
            );
            CREATE TABLE IF NOT EXISTS agents (
                agent_id        TEXT PRIMARY KEY,
                swarm_id        TEXT NOT NULL,
                role            TEXT NOT NULL,
                subtask         TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'spawned',
                result          TEXT NOT NULL DEFAULT '',
                error           TEXT NOT NULL DEFAULT '',
                progress_detail TEXT NOT NULL DEFAULT '',
                tools_used      TEXT NOT NULL DEFAULT '',
                created_at      REAL NOT NULL,
                finished_at     REAL
            );
        """)
        self._db.commit()

    def _load_sessions_from_db(self) -> dict[str, SwarmSession]:
        assert self._db is not None
        result = {}
        for row in self._db.execute("SELECT * FROM sessions").fetchall():
            agent_ids = [a for a in row["agent_ids"].split(",") if a]
            session = SwarmSession(
                swarm_id=row["swarm_id"],
                task=row["task"],
                phase=SwarmPhase(row["phase"]),
                agent_ids=agent_ids,
                final_result=row["final_result"],
                created_at=row["created_at"],
                finished_at=row["finished_at"],
            )
            result[session.swarm_id] = session
        return result

    def _load_agents_from_db(self) -> dict[str, AgentState]:
        assert self._db is not None
        result = {}
        for row in self._db.execute("SELECT * FROM agents").fetchall():
            tools_used = [t for t in row["tools_used"].split(",") if t]
            agent = AgentState(
                agent_id=row["agent_id"],
                role=row["role"],
                subtask=row["subtask"],
                status=AgentStatus(row["status"]),
                result=row["result"],
                error=row["error"],
                progress_detail=row["progress_detail"],
                tools_used=tools_used,
                created_at=row["created_at"],
                finished_at=row["finished_at"],
            )
            result[agent.agent_id] = agent
        return result

    def _persist_session(self, session: SwarmSession) -> None:
        if self._db is None:
            return
        self._db.execute("""
            INSERT OR REPLACE INTO sessions
            (swarm_id, task, phase, agent_ids, final_result, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session.swarm_id, session.task, session.phase.value,
            ",".join(session.agent_ids), session.final_result,
            session.created_at, session.finished_at,
        ))
        self._db.commit()

    def _persist_agent(self, agent: AgentState, swarm_id: str) -> None:
        if self._db is None:
            return
        self._db.execute("""
            INSERT OR REPLACE INTO agents
            (agent_id, swarm_id, role, subtask, status, result, error,
             progress_detail, tools_used, created_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent.agent_id, swarm_id, agent.role, agent.subtask,
            agent.status.value, agent.result, agent.error,
            agent.progress_detail, ",".join(agent.tools_used),
            agent.created_at, agent.finished_at,
        ))
        self._db.commit()

    def _get_swarm_for_agent(self, agent_id: str) -> str | None:
        for swarm_id, session in self._sessions.items():
            if agent_id in session.agent_ids:
                return swarm_id
        return None

    # ── Pub/Sub ───────────────────────────────────────────────────────────

    def subscribe(self, callback: Callable[[dict], None]) -> None:
        """Registriert einen Callback für State-Updates (SSE-Bridge)."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[dict], None]) -> None:
        """Entfernt einen Callback."""
        self._subscribers = [cb for cb in self._subscribers if cb is not callback]

    def _notify(self, event: dict) -> None:
        """Benachrichtige alle Subscriber über ein State-Update."""
        for cb in self._subscribers:
            try:
                cb(event)
            except Exception:
                pass

    # ── Session Management ────────────────────────────────────────────────

    def create_session(self, task: str) -> str:
        """Erstellt eine neue Swarm-Session. Returns swarm_id."""
        swarm_id = f"swarm-{uuid.uuid4().hex[:8]}"
        session  = SwarmSession(swarm_id=swarm_id, task=task)
        self._sessions[swarm_id]      = session
        self._session_tokens[swarm_id] = 0  # T-10
        self._persist_session(session)
        self._notify({
            "type": "swarm_status", "swarm_id": swarm_id,
            "phase": session.phase.value,
            "message": f"Swarm erstellt: {task[:80]}",
        })
        return swarm_id

    async def update_session_phase(self, swarm_id: str, phase: SwarmPhase) -> None:
        """Aktualisiert die Phase einer Swarm-Session."""
        async with self._lock:
            session = self._sessions.get(swarm_id)
            if not session:
                return
            session.phase = phase
            if phase in (SwarmPhase.DONE, SwarmPhase.ERROR):
                session.finished_at = time.time()
            self._persist_session(session)
        self._notify({
            "type": "swarm_status", "swarm_id": swarm_id,
            "phase": phase.value, "message": _phase_message(phase),
        })

    async def set_session_result(self, swarm_id: str, result: str) -> None:
        """Setzt das finale Ergebnis einer Swarm-Session."""
        async with self._lock:
            session = self._sessions.get(swarm_id)
            if session:
                session.final_result = result
                self._persist_session(session)

    def get_session(self, swarm_id: str) -> SwarmSession | None:
        """Gibt die Session-Daten zurück."""
        return self._sessions.get(swarm_id)

    # ── Agent Management ──────────────────────────────────────────────────

    def register_agent(self, swarm_id: str, role: str, subtask: str) -> str:
        """
        Registriert einen neuen Swarm-Agenten.
        T-10: Wirft BudgetExceededError wenn Budget überschritten.
        Returns agent_id.
        """
        # T-10: Budget-Check VOR dem Spawn
        if self._token_budget is not None:
            used = self._session_tokens.get(swarm_id, 0)
            if used > self._token_budget:
                raise BudgetExceededError(swarm_id, used, self._token_budget)

        agent_id = f"sw-{uuid.uuid4().hex[:6]}"
        agent    = AgentState(agent_id=agent_id, role=role, subtask=subtask)
        self._agents[agent_id]      = agent
        self._agent_tokens[agent_id] = 0  # T-10

        session = self._sessions.get(swarm_id)
        if session:
            session.agent_ids.append(agent_id)
            self._persist_session(session)

        self._persist_agent(agent, swarm_id)
        self._notify({
            "type": "agent_spawned", "swarm_id": swarm_id,
            "agent_id": agent_id, "role": role,
            "subtask": subtask[:120],
        })
        return agent_id

    async def update_agent_status(
        self, agent_id: str, status: AgentStatus, detail: str = ""
    ) -> None:
        """Aktualisiert den Status eines Agenten."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            agent.status = status
            if detail:
                agent.progress_detail = detail
            if status in (AgentStatus.DONE, AgentStatus.ERROR, AgentStatus.TERMINATED):
                agent.finished_at = time.time()
            swarm_id = self._get_swarm_for_agent(agent_id)
            self._persist_agent(agent, swarm_id or "")
        self._notify({
            "type": "agent_progress", "agent_id": agent_id,
            "status": status.value, "detail": detail[:200] if detail else "",
        })

    async def set_agent_result(self, agent_id: str, result: str) -> None:
        """Setzt das Ergebnis eines Agenten."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.result = result
                self._persist_agent(agent, self._get_swarm_for_agent(agent_id) or "")

    async def set_agent_error(self, agent_id: str, error: str) -> None:
        """Setzt den Fehler eines Agenten."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.error       = error
                agent.status      = AgentStatus.ERROR
                agent.finished_at = time.time()
                self._persist_agent(agent, self._get_swarm_for_agent(agent_id) or "")
        self._notify({
            "type": "agent_progress", "agent_id": agent_id,
            "status": AgentStatus.ERROR.value, "detail": error[:200],
        })

    async def terminate_agent(self, agent_id: str) -> None:
        """Markiert einen Agenten als TERMINATED (Self-Termination)."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if not agent:
                return
            agent.status      = AgentStatus.TERMINATED
            agent.finished_at = time.time()
            self._persist_agent(agent, self._get_swarm_for_agent(agent_id) or "")
        self._notify({
            "type": "agent_terminated", "agent_id": agent_id,
            "result_preview": (self._agents.get(agent_id, AgentState("","","")).result or "")[:200],
        })

    def get_agent(self, agent_id: str) -> AgentState | None:
        """Gibt den Zustand eines Agenten zurück."""
        return self._agents.get(agent_id)

    def get_all_agents(self, swarm_id: str) -> list[AgentState]:
        """Gibt alle Agenten einer Session zurück."""
        session = self._sessions.get(swarm_id)
        if not session:
            return []
        return [self._agents[aid] for aid in session.agent_ids if aid in self._agents]

    def all_agents_finished(self, swarm_id: str) -> bool:
        """Prüft ob alle Agenten einer Session fertig sind."""
        agents = self.get_all_agents(swarm_id)
        if not agents:
            return False
        return all(
            a.status in (AgentStatus.DONE, AgentStatus.ERROR, AgentStatus.TERMINATED)
            for a in agents
        )

    async def add_tool_used(self, agent_id: str, tool_name: str) -> None:
        """T-12: Trackt Tools dedupliziert via Lock."""
        async with self._lock:
            agent = self._agents.get(agent_id)
            if agent and tool_name not in agent.tools_used:
                agent.tools_used.append(tool_name)
                self._persist_agent(agent, self._get_swarm_for_agent(agent_id) or "")

    # ── T-10: Budget-Tracker ───────────────────────────────────────────────

    def record_tokens(
        self,
        swarm_id: str,
        count:    int,
        agent_id: str | None = None,
    ) -> None:
        """
        T-10 + T-14: Erfasst verbrauchte Tokens.
        Emittiert ein 'budget_exceeded'-Event EINMALIG wenn das Limit erstmals überschritten wird.

        Args:
            swarm_id: Session-ID
            count:    Anzahl Tokens
            agent_id: Optional — wenn gesetzt, per-Agent gezählt
        """
        before = self._session_tokens.get(swarm_id, 0)
        self._session_tokens[swarm_id] = before + count
        after  = self._session_tokens[swarm_id]

        if agent_id is not None:
            self._agent_tokens[agent_id] = self._agent_tokens.get(agent_id, 0) + count

        # T-14: budget_exceeded Event — nur einmalig wenn Schwelle gekreuzt
        if (
            self._token_budget is not None
            and before <= self._token_budget   # vorher OK
            and after  >  self._token_budget   # jetzt überschritten
        ):
            self._notify({
                "type":        "budget_exceeded",
                "swarm_id":    swarm_id,
                "tokens_used": after,
                "budget":      self._token_budget,
            })

    def get_budget_report(self, swarm_id: str) -> dict:
        """
        T-10: Budget-Report für eine Session.

        Returns:
            total_tokens, budget_limit, budget_remaining, budget_exceeded, per_agent
        """
        session   = self._sessions.get(swarm_id)
        total     = self._session_tokens.get(swarm_id, 0)
        per_agent = {
            aid: self._agent_tokens.get(aid, 0)
            for aid in (session.agent_ids if session else [])
        }
        remaining = (
            self._token_budget - total if self._token_budget is not None else None
        )
        return {
            "total_tokens":     total,
            "budget_limit":     self._token_budget,
            "budget_remaining": remaining,
            "budget_exceeded":  (
                self._token_budget is not None and total > self._token_budget
            ),
            "per_agent": per_agent,
        }

    # ── Cleanup ───────────────────────────────────────────────────────────

    async def cleanup_session(self, swarm_id: str) -> None:
        """Räumt alle Daten einer Session auf (Memory-Freigabe)."""
        async with self._lock:
            session = self._sessions.pop(swarm_id, None)
            if session:
                for aid in session.agent_ids:
                    self._agents.pop(aid, None)
                    self._agent_tokens.pop(aid, None)
            self._session_tokens.pop(swarm_id, None)

    def get_stats(self) -> dict:
        """Debug-Info: aktuelle Store-Statistiken."""
        return {
            "sessions":    len(self._sessions),
            "agents":      len(self._agents),
            "subscribers": len(self._subscribers),
        }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _phase_message(phase: SwarmPhase) -> str:
    """Menschenlesbare Phase-Beschreibung."""
    return {
        SwarmPhase.PLANNING:     "🧠 Manager analysiert Aufgabe…",
        SwarmPhase.SPAWNING:     "⚡ Swarm-Agenten werden erstellt…",
        SwarmPhase.EXECUTING:    "🐝 Agenten arbeiten parallel…",
        SwarmPhase.SYNTHESIZING: "🔗 Ergebnisse werden zusammengeführt…",
        SwarmPhase.DONE:         "✅ Swarm abgeschlossen.",
        SwarmPhase.ERROR:        "❌ Swarm fehlgeschlagen.",
    }.get(phase, str(phase))


# ── Singleton ──────────────────────────────────────────────────────────────────

swarm_state_store = SwarmStateStore()

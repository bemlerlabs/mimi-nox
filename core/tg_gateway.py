"""
◑ MiMi Nox – Telegram-Gateway-Orchestrierung (Sprint 3 G1).

Routet erlaubte Telegram-Nachrichten auf die EXISTIERENDE chat_with_tools-
Pipeline (Qwen auf DGX als Engine) — derselbe Pfad wie die PWA. Jede Channel-
Session nutzt die ApprovalPolicy-DEFAULT (P0-1-Gate, KEIN Auto-Approve):
mutating-Tools werden per Telegram-Freigabe (ja/nein) bestätigt.

Concurrency (on-device, kein Relay): die Poll-Loop spawn pro erlaubter
Nachricht einen Task. Braucht ein Tool Approval, postet der Task den Diff und
wartet auf die ja/nein-Antwort; die (weiterlaufende) Poll-Loop liest die
Antwort und löst die Freigabe. So blockiert die Approval-Runde die Loop nie.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from core.tg_client import TgMessage
from core.tools.approval import ApprovalPolicy, format_diff
from core.chat import chat_with_tools
from core.channels.injection_guard import (
    INJECTION_POLICY_PROMPT,
    guard_channel_message,
)

_APPROVAL_YES = {"ja", "yes", "y", "yep", "ok", "approve", "/ja", "/yes", "👍"}
_APPROVAL_NO = {"nein", "no", "n", "nope", "deny", "ablehnen", "/nein", "/no", "👎"}


def is_approval_yes(text: str) -> bool:
    """True, wenn der Text ein explizites Approval-Freigabe-Signal ist."""
    return (text or "").strip().lower() in _APPROVAL_YES


def is_approval_no(text: str) -> bool:
    """True, wenn der Text ein explizites Ablehnungs-Signal ist."""
    return (text or "").strip().lower() in _APPROVAL_NO


@dataclass
class _PendingApproval:
    tool_name: str
    diff: str
    future: asyncio.Future
    created_at: float


class TGGateway:
    """On-Device-Telegram-Gateway: Long-Poll → chat_with_tools (Qwen/DGX)."""

    def __init__(
        self,
        *,
        client,
        model: str,
        api_url: str | None = None,
        approval_timeout: float = 300.0,
    ) -> None:
        self._client = client
        self._model = model
        self._api_url = api_url
        self._approval_timeout = approval_timeout
        self._pending: dict[int, _PendingApproval] = {}
        self._tasks: set[asyncio.Task] = set()
        # Audit-Trail (Evidenz für Review/E2E): jedes Approval-Event.
        self.approval_history: list[dict] = []

    # ── Poll-Loop (eine Iteration) ───────────────────────────────────────────
    async def run_poll(self) -> list[asyncio.Task]:
        """Eine Poll-Iteration: erlaubte Updates abarbeiten."""
        started: list[asyncio.Task] = []
        for m in self._client.get_updates():
            if not self._client.is_allowed(m.user_id):
                continue  # Defensive: Allowlist gilt hart.
            pending = self._pending.get(m.chat_id)
            if pending is not None:
                if is_approval_yes(m.text):
                    self._resolve(m.chat_id, True)
                elif is_approval_no(m.text):
                    self._resolve(m.chat_id, False)
                # Sonst: Antwort auf offene Approval ignorieren (nicht neu starten).
                continue
            task = asyncio.create_task(self._run_chat(m))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            started.append(task)
        return started

    async def quiesce(self) -> None:
        """Wartet auf alle in-Flight-Chat-Tasks (deterministisch für Tests/E2E)."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    def _resolve(self, chat_id: int, approved: bool) -> None:
        p = self._pending.pop(chat_id, None)
        if p is None:
            return
        if not p.future.done():
            p.future.set_result(approved)
        self._log_approval(p.tool_name, approved, "reply")

    # ── Ein Chat (eine erlaubte Nachricht) ───────────────────────────────────
    async def _run_chat(self, m: TgMessage) -> None:
        try:
            await self._send(m.chat_id, "⏳ Verarbeite deine Anfrage …")
            # E2 (Sprint3-G2, core/channels/injection_guard): Channel-Inhalt ist
            # NIE Instruktion. Der Text wird in eine UNTRUSTED-Quarantäne gewrappt
            # und das Model via extra_system_prompt angewiesen, ihn nur als Daten
            # zu behandeln. Blockiert die harte Schicht 3 = ApprovalPolicy (kein
            # Auto-Approve). Approval-Antworten (ja/nein) laufen NICHT durch hier.
            guarded = guard_channel_message(m.text or "")
            policy = ApprovalPolicy(
                auto_approve=False,
                dry_run=False,
                declined=False,
                on_confirm=lambda name, args: self._request_approval(m.chat_id, name, args),
                interactive=False,
            )
            final = await chat_with_tools(
                model=self._model,
                history=[{"role": "user", "content": guarded.wrapped}],
                on_chunk=lambda _c: None,
                api_url=self._api_url,
                approval_policy=policy,
                extra_system_prompt=INJECTION_POLICY_PROMPT,
            )
            answer = (final or "").strip()
            if answer:
                await self._send(m.chat_id, answer)
        except Exception as exc:  # noqa: BLE001 — Token redigieren, nie rohen Fehler
            from core.tg_tokens import redact_token
            try:
                await self._send(m.chat_id, f"⚠️ Fehler: {redact_token(str(exc))}")
            except Exception:
                pass

    async def _request_approval(self, chat_id: int, tool_name: str, args: dict) -> bool:
        """P0-1-Gate via Telegram: Diff posten, auf ja/nein warten (kein Auto)."""
        diff = format_diff(tool_name, args)
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending[chat_id] = _PendingApproval(tool_name, diff, fut, time.time())
        try:
            await self._send(
                chat_id,
                f"🔐 Tool-Freigabe nötig:\n{diff}\n\nAntworte mit **ja** oder **nein**.",
            )
            approved = await asyncio.wait_for(fut, timeout=self._approval_timeout)
            self._log_approval(tool_name, bool(approved), "reply")
            return bool(approved)
        except asyncio.TimeoutError:
            self._pending.pop(chat_id, None)
            self._log_approval(tool_name, False, "timeout")
            await self._send(chat_id, "⏱ Approval-Timeout → abgelehnt (kein Auto-Approve).")
            return False

    async def _send(self, chat_id: int, text: str) -> None:
        """Synchroner Telegram-Call ins Thread, damit die Loop frei bleibt."""
        await asyncio.to_thread(self._client.send_message, chat_id, text)

    def _log_approval(self, tool: str, approved: bool, how: str) -> None:
        self.approval_history.append(
            {"tool": tool, "approved": bool(approved), "how": how, "ts": time.time()}
        )


__all__ = ["TGGateway", "is_approval_yes", "is_approval_no"]

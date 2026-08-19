"""
tests/test_tg_approval.py – Sprint 3 G1: strict ApprovalPolicy (P0-1-Gate) in der
Channel-Pipeline.

SPECK-DoD (Ziffer 4, 5):
  (4) Channel-Sessions nutzen die ApprovalPolicy DEFAULT (Wiederverwendung des
      P0-1-Gates), KEIN Auto-Approve. Mutating-Tools werden NIE still ausgeführt.
  (5) Der Kanal routet auf die EXISTIERENDE chat_with_tools-Pipeline (Qwen/DGX).

Diese Tests verifizieren, dass `chat_with_tools` ein `ApprovalPolicy`-Objekt
durch den Tool-Loop durchreicht und das P0-1-Gate (request_approval) greift:

  - Strict-Default (auto_approve=False, interactive=False, kein Callback)
    → ein MUTATING-Tool (run_shell) wird ABGELEHNT, nicht ausgeführt.
  - on_confirm-Callback True → Tool wird ausgeführt (Shell-Whitelist als
    zweite Schranke via execute_confirmed_shell).
  - SAFE-Tools (read-only) → auto-approved, selbst unter Strict-Policy.

VOLLSTÄNDIG OFFLINE: der Provider-Client wird durch einen Fake ersetzt, der
Tool-Calls emittiert. Kein echtes DGX, kein echtes Shell (außer echo im
Freigabe-Fall, der in ALLOWED_COMMANDS steht).
"""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from core.chat import chat_with_tools
from core.tools.approval import ApprovalPolicy


# ── Fake-Provider-Client (emittiert Tool-Calls) ────────────────────────────────

class _Fn:
    def __init__(self, name: str, arguments: dict) -> None:
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name: str, arguments: dict) -> None:
        self.function = _Fn(name, arguments)


class _Msg:
    def __init__(self, content: str | None = None, tool_calls=None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class _Resp:
    def __init__(self, message: _Msg) -> None:
        self.message = message


class _FakeClient:
    """Async-Fake: liefert nacheinander die Responses aus dem Script."""

    def __init__(self, script: list[_Resp]) -> None:
        self._script = list(script)
        self._i = 0
        self.chat_calls: list = []

    async def chat(self, model=None, messages=None, tools=None, stream=False, **kw):
        self.chat_calls.append(messages)
        if self._i < len(self._script):
            resp = self._script[self._i]
            self._i += 1
            return resp
        return _Resp(_Msg(content="fertig", tool_calls=None))


def _tool_call_resp(name: str, arguments: dict) -> _Resp:
    return _Resp(_Msg(content=None, tool_calls=[_ToolCall(name, arguments)]))


def _final_resp(text: str = "fertig") -> _Resp:
    return _Resp(_Msg(content=text, tool_calls=None))


async def _run_chat_with_tools(script, policy, on_tool_done, history=None):
    """chat_with_tools mit gefaktem Provider-Client aufrufen."""
    if history is None:
        history = [{"role": "user", "content": "führe run_shell ls aus"}]
    fake = _FakeClient(script)
    with patch("core.chat.build_provider_client", return_value=fake):
        return await chat_with_tools(
            model="qwen38-27b-unsloth-nvfp4",
            history=history,
            on_chunk=lambda _c: None,
            approval_policy=policy,
            on_tool_done=on_tool_done,
        )


def _record(seen: list):
    """on_tool_done-Callback (2-arg: name, result) als schließbare Factory."""
    def _cb(name: str, result: str) -> None:
        seen.append((name, result))
    return _cb


# ── (4a) Strict-Default: mutating wird ABGELEHNT, nicht ausgeführt ─────────────

@pytest.mark.asyncio
async def test_strict_policy_denies_mutating_shell(tmp_path):
    """auto_approve=False + interactive=False + kein Callback → DENY."""
    policy = ApprovalPolicy(
        auto_approve=False, dry_run=False, declined=False,
        on_confirm=None, interactive=False,
    )
    seen: list[tuple[str, str]] = []
    script = [
        _tool_call_resp("run_shell", {"command": "ls"}),
        _final_resp("fertig"),
    ]
    final = await _run_chat_with_tools(script, policy, _record(seen))
    # Das Tool wurde nicht ausgeführt: das Ergebnis ist der P0-1-Deny-Report.
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "run_shell"
    assert result.startswith("[Abgelehnt]"), f"Erwartet Deny-Report, statt: {result!r}"
    # "ls"-Output (Dateilisten) darf NICHT im Result stehen.
    assert "(kein Output)" not in result and "[exit" not in result
    # Finale Antwort kommt trotzdem von der Pipeline.
    assert final == "fertig"


@pytest.mark.asyncio
async def test_strict_policy_denies_generic_mutating_tool(tmp_path):
    """Ein beliebiges MUTATING-Tool (nicht run_shell) wird ebenfalls geblockt."""
    policy = ApprovalPolicy(auto_approve=False, dry_run=False, declined=False,
                            on_confirm=None, interactive=False)
    seen: list[tuple[str, str]] = []
    # manage_tasks ist MUTATING (nicht in SAFE_TOOLS).
    script = [
        _tool_call_resp("manage_tasks", {"action": "add", "title": "x"}),
        _final_resp("fertig"),
    ]
    await _run_chat_with_tools(
        script, policy, _record(seen),
        history=[{"role": "user", "content": "task add"}],
    )
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "manage_tasks"
    assert result.startswith("[Abgelehnt]"), f"Erwartet Deny, statt: {result!r}"


# ── (4b) on_confirm-Callback True → ausgeführt (Whitelist als 2. Schranke) ─────

@pytest.mark.asyncio
async def test_on_confirm_true_executes_shell_whitelisted(tmp_path):
    """Callback=True → run_shell läuft (echo steht in ALLOWED_COMMANDS)."""

    async def _yes(_name: str, _args: dict) -> bool:
        return True

    policy = ApprovalPolicy(auto_approve=False, dry_run=False, declined=False,
                            on_confirm=_yes, interactive=False)
    seen: list[tuple[str, str]] = []
    script = [
        _tool_call_resp("run_shell", {"command": "echo ok"}),
        _final_resp("fertig"),
    ]
    await _run_chat_with_tools(script, policy, _record(seen))
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "run_shell"
    # Echtes Shell-Output (Whitelist durchgelassen), KEIN Deny-Report.
    assert "ok" in result, f"Erwartet 'ok', statt: {result!r}"
    assert not result.startswith("[Abgelehnt]")


@pytest.mark.asyncio
async def test_on_confirm_false_denies(tmp_path):
    """Callback=False → Abbruch, keine Ausführung."""

    async def _no(_name: str, _args: dict) -> bool:
        return False

    policy = ApprovalPolicy(auto_approve=False, dry_run=False, declined=False,
                            on_confirm=_no, interactive=False)
    seen: list[tuple[str, str]] = []
    script = [
        _tool_call_resp("run_shell", {"command": "echo ok"}),
        _final_resp("fertig"),
    ]
    await _run_chat_with_tools(script, policy, _record(seen))
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "run_shell"
    assert result.startswith("[Abgelehnt]"), f"Erwartet Deny, statt: {result!r}"


# ── (4c) SAFE-Tools (read-only) → auto-approved, selbst unter Strict-Policy ────

@pytest.mark.asyncio
async def test_safe_tool_auto_approved_under_strict_policy(tmp_path):
    """read-only Tools brauchen kein Approval (P0-1-Vertrag, unverändert)."""
    policy = ApprovalPolicy(auto_approve=False, dry_run=False, declined=False,
                            on_confirm=None, interactive=False)
    seen: list[tuple[str, str]] = []
    script = [
        _tool_call_resp("get_datetime", {}),
        _final_resp("fertig"),
    ]
    await _run_chat_with_tools(
        script, policy, _record(seen),
        history=[{"role": "user", "content": "wie spät ist es?"}],
    )
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "get_datetime"
    # Executed (kein Deny-Report): enthält ein Datum/Uhrzeit-Format, kein "[Abgelehnt]".
    assert not result.startswith("[Abgelehnt]"), f"SAFE-Tool wurde fälschlich geblockt: {result!r}"
    assert result.strip(), "SAFE-Tool-Lieferung darf nicht leer sein"


# ── Regression: ohne Policy bleibt der PWA-Pfad (on_shell_confirm) unverändert ─

@pytest.mark.asyncio
async def test_no_policy_keeps_shell_confirm_path(tmp_path):
    """approval_policy=None + on_shell_confirm=True → Shell läuft (PWA-Verhalten)."""
    seen: list[tuple[str, str]] = []
    fake = _FakeClient([
        _tool_call_resp("run_shell", {"command": "echo pw"}),
        _final_resp("fertig"),
    ])
    with patch("core.chat.build_provider_client", return_value=fake):
        await chat_with_tools(
            model="qwen38-27b-unsloth-nvfp4",
            history=[{"role": "user", "content": "echo pw"}],
            on_chunk=lambda _c: None,
            on_shell_confirm=lambda _cmd: True,
            on_tool_done=_record(seen),
        )
    assert len(seen) == 1
    name, result = seen[0]
    assert name == "run_shell"
    assert "pw" in result, f"on_shell_confirm-Pfad soll Shell ausführen, statt: {result!r}"

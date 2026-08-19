"""
tests/test_tg_gateway_e2e.py – Sprint 3 G1: vollständiger Telegram-Approval-Roundtrip.

Ergänzt test_tg_approval.py (Gate in chat_with_tools) um die GATEWAY-Orchestrierung:
die echte Poll-Loop (TGGateway.run_poll) postet den 🔐-Diff, wartet; die nächste
Poll-Iteration liest die ja/nein-Antwort und löst die Freigabe. Das P0-1-Gate +
execute_confirmed_shell sind ECHT (kein Mock) — nur der LLM-Client ist ein Fake,
der einen nativen run_shell-Tool-Call emittiert (dieser Schritt ist der bekannte
Engpass des nvfp4-Qwen-Builds: er emittiert Tool-Calls als Text, nicht nativ).

Die Ausführung wird über eine REALE Dateiseite (touch) verifiziert:
  - 'ja'   → touch-Datei wird angelegt (Shell ECHT ausgeführt).
  - 'nein' → touch-Datei wird NICHT angelegt (Shell ECHT abgelehnt).

VOLLSTÄNDIG OFFLINE: kein Telegram, kein DGX.
"""
from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

import core.tg_gateway as gw
from core.tg_client import TgMessage
from core.tg_gateway import TGGateway


# ── Fake-Engine-Client (emittiert einen nativen run_shell-Tool-Call) ──────────

class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    def __init__(self, name, arguments):
        self.function = _Fn(name, arguments)


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _Resp:
    def __init__(self, message):
        self.message = message


class _EngineFake:
    def __init__(self, command: str, final: str = "fertig"):
        self._command = command
        self._final = final

    async def chat(self, model=None, messages=None, tools=None, stream=False, **kw):
        # Erste Call: Tool-Call. Zweite Call (nach Tool-Ergebnis): finale Antwort.
        if not hasattr(self, "_emitted"):
            self._emitted = True
            return _Resp(_Msg(content=None,
                              tool_calls=[_ToolCall("run_shell",
                                                    {"command": self._command})]))
        return _Resp(_Msg(content=self._final, tool_calls=None))


# ── Fake-Telegram-Client (sequenzierte Updates + gesendete Messages) ─────────

class _FakeTg:
    def __init__(self):
        self._batches: list[list[TgMessage]] = []
        self.sent: list[tuple[int, str]] = []
        self.uid = 42
        self._mid = 0

    def is_allowed(self, uid):
        return True

    def get_updates(self):
        return self._batches.pop(0) if self._batches else []

    def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))
        return {"ok": True}

    def add(self, text: str):
        self._mid += 1
        m = TgMessage(update_id=self._mid, message_id=self._mid,
                      user_id=self.uid, chat_id=self.uid, text=text)
        self._batches.append([m])


async def _wait_until(cond, timeout: float = 15.0):
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        if cond():
            return True
        await asyncio.sleep(0.05)
    return False


async def _drive_roundtrip(command: str, reply: str):
    """Eine komplette Gateway-Approval-Runde: [command] → [reply].

    Liefert (fake, gateway, executed: bool). 'executed' = die Touch-Seite existiert.
    """
    marker = f"exec_{abs(hash(reply + command)) & 0xFFFFFFFF}"
    cmd = f"touch /tmp/miminox_tg_{marker}"  # 'touch' ∈ ALLOWED_COMMANDS
    fake = _FakeTg()
    gateway = TGGateway(client=fake, model="qwen38-27b-unsloth-nvfp4",
                        api_url="http://dgx.test/v1", approval_timeout=30.0)
    with patch("core.chat.build_provider_client", return_value=_EngineFake(cmd)):
        fake.add("führe den Shell-Befehl aus")
        await gateway.run_poll()                 # startet den Chat-Task
        # Warten, bis der 🔐-Approval-Diff gesendet ist (impliziert: pending gesetzt).
        ok = await _wait_until(lambda: any("🔐" in t for _, t in fake.sent), timeout=20.0)
        assert ok, f"Kein 🔐-Approval-Diff gesendet. Sent: {[t for _, t in fake.sent]}"
        # Approval-Antwort über die NÄCHSTE Poll-Iteration (on-device-Verhalten).
        fake.add(reply)
        await gateway.run_poll()                 # löst die Freigabe
        await gateway.quiesce()
    Path(cmd.split()[-1]).unlink(missing_ok=True)  # Räumung für saubere Nachprüfung
    return fake, gateway


@pytest.mark.asyncio
async def test_gateway_approval_yes_executes_shell(tmp_path):
    """'ja' → P0-1-Gate freigibt → Shell ECHT ausgeführt (Touch-Seite angelegt)."""
    marker = "yes_marker"
    cmd = f"touch /tmp/miminox_tg_{marker}"
    fake = _FakeTg()
    gateway = TGGateway(client=fake, model="m", api_url="http://x/v1",
                        approval_timeout=30.0)
    target = Path(f"/tmp/miminox_tg_{marker}")
    target.unlink(missing_ok=True)
    with patch("core.chat.build_provider_client", return_value=_EngineFake(cmd)):
        fake.add("führe es aus")
        await gateway.run_poll()
        assert await _wait_until(lambda: any("🔐" in t for _, t in fake.sent), 20.0)
        # Der 🔐-Diff enthält den Shell-Befehl (format_diff für run_shell).
        approval_msg = next(t for _, t in fake.sent if "🔐" in t)
        assert cmd in approval_msg, f"Diff fehlt den Shell-Befehl: {approval_msg!r}"
        fake.add("ja")
        await gateway.run_poll()
        await gateway.quiesce()
    # REALE Ausführung: die Touch-Seite wurde angelegt.
    assert target.exists(), "Shell wurde trotz 'ja' NICHT ausgeführt."
    # Completion-Antwort (final) wurde gesendet, kein Fehler.
    assert any(not t.startswith("⚠️") and not t.startswith("⏳")
               and "🔐" not in t for _, t in fake.sent), "Keine Completion-Antwort."
    target.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gateway_approval_no_denies_shell(tmp_path):
    """'nein' → P0-1-Gate lehnt ab → Shell wird NICHT ausgeführt."""
    marker = "no_marker"
    cmd = f"touch /tmp/miminox_tg_{marker}"
    fake = _FakeTg()
    gateway = TGGateway(client=fake, model="m", api_url="http://x/v1",
                        approval_timeout=30.0)
    target = Path(f"/tmp/miminox_tg_{marker}")
    target.unlink(missing_ok=True)
    with patch("core.chat.build_provider_client", return_value=_EngineFake(cmd)):
        fake.add("führe es aus")
        await gateway.run_poll()
        assert await _wait_until(lambda: any("🔐" in t for _, t in fake.sent), 20.0)
        fake.add("nein")
        await gateway.run_poll()
        await gateway.quiesce()
    # REALE Nicht-Ausführung: die Touch-Seite wurde NICHT angelegt.
    assert not target.exists(), "Shell wurde trotz 'nein' ECHT ausgeführt (P0-1-Verletzung)."
    target.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_gateway_strict_no_autoapprove_posts_diff(tmp_path):
    """Strict-Policy: ohne ja/nein wird der Diff gepostet und NIE auto-freigegeben."""
    marker = "strict_marker"
    cmd = f"touch /tmp/miminox_tg_{marker}"
    fake = _FakeTg()
    gateway = TGGateway(client=fake, model="m", api_url="http://x/v1",
                        approval_timeout=1.0)  # kurzer Timeout → Denial
    target = Path(f"/tmp/miminox_tg_{marker}")
    target.unlink(missing_ok=True)
    with patch("core.chat.build_provider_client", return_value=_EngineFake(cmd)):
        fake.add("führe es aus")
        await gateway.run_poll()
        assert await _wait_until(lambda: any("🔐" in t for _, t in fake.sent), 20.0)
        # KEINE Antwort senden: Approval läuft nach 1s aus → abgelehnt (kein Auto).
        await gateway.quiesce()
    # Kein Auto-Approve: Shell nicht ausgeführt.
    assert not target.exists(), "Auto-Approve statt striktem P0-1-Gate!"
    # Ein Timeout-/Denial-Hinweis wurde gesendet.
    assert any("Timeout" in t or "abgelehnt" in t.lower() for _, t in fake.sent), \
        f"Kein Denial-Hinweis. Sent: {[t for _, t in fake.sent]}"
    target.unlink(missing_ok=True)


# ── E2 (Sprint3-G2): Injection-Guard ist im Gateway VERDRAHTET ───────────────
#
# Der Offline-e2e oben testet das Approval-Gate (ja/nein). Dieser Test prüft
# die E2-Schicht: die eingehende Channel-Nachricht wird durch
# core.channels.injection_guard.guard_channel_message gewrappt (UNTRUSTED-
# Quarantäne) und das Model via extra_system_prompt mit der Injection-Policy
# versorgt. Ohne diese Verdrahtung ist Channel-Inhalt = Instruktion (Threat E2).

def _capture_chat_with_tools() -> "unittest.mock.MagicMock":
    """chat_with_tools fangen, Argumente aufzeichnen, leeren String liefern."""
    import inspect
    async def _fake(**kw):
        return "ok"
    m = unittest.mock.MagicMock(side_effect=_fake)
    return m


def test_gateway_wraps_channel_text_with_injection_guard():
    """Eine Channel-Nachricht geht GUARD-VERPACKT an die Engine (E2)."""
    from core.channels.injection_guard import UNTRUSTED_DATA_OPEN, INJECTION_POLICY_PROMPT
    from core.tg_client import TgMessage
    from core.tg_gateway import TGGateway

    class _Cap:
        def __init__(self):
            self.sent = []
            self.calls = []
        def is_allowed(self, uid):
            return True
        def get_updates(self):
            return self._batch if self._batch else []
        def send_message(self, chat_id, text):
            self.sent.append((chat_id, text)); return {"ok": True}
        def _mk(self, text):
            m = TgMessage(update_id=1, message_id=1, user_id=7, chat_id=7, text=text)
            self._batch = [m]

    cap = _Cap()
    cap._batch = []
    cap._mk("hello")
    gw = TGGateway(client=cap, model="m", api_url="http://x/v1")

    async def _run():
        with unittest.mock.patch("core.tg_gateway.chat_with_tools") as cwt:
            async def _side(**kw):
                cap.calls.append(kw); return "ok"
            cwt.side_effect = _side
            await gw.run_poll()
            await gw.quiesce()
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()

    assert cap.calls, "chat_with_tools wurde nie aufgerufen"
    hist = cap.calls[0]["history"]
    content = hist[-1]["content"]
    assert UNTRUSTED_DATA_OPEN in content, f"Text nicht UNTRUSTED-verpackt: {content!r}"
    assert cap.calls[0]["extra_system_prompt"] == INJECTION_POLICY_PROMPT, \
        "Injection-Policy nicht an die Engine durchgereicht"

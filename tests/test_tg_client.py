"""
tests/test_tg_client.py – Sprint 3 G1: Telegram-Client (on-device, kein Relay).

SPECK-DoD (Ziffer 1, 4):
  (1) On-Device-Gateway: Der Bot spricht DIREKT mit der Telegram-Long-Poll-API
      (getUpdates), NIE über ein Cloud-Relay/Webhook.
  (4) E2E-Fluss: Eine Telegram-Nachricht wird an die EXISTIERENDE
      chat_with_tools-Pipeline geroutet (Qwen auf DGX als Engine).

Diese Tests sind VOLLSTÄNDIG OFFLINE: Die Telegram-API wird durch einen
Fake-HTTP-Transport ersetzt (stdlib-urllib-Patch), kein echtes Telegram,
kein DGX. Der Fluss wird deterministisch gegen den Fake verifiziert.
"""
from __future__ import annotations

import json
import os
from typing import Any
from unittest.mock import patch

import pytest

from core.tg_client import TgClient, TgMessage


def make_update(user_id: int, text: str, update_id: int = 1) -> dict:
    """Konstruiert eine gültige getUpdates-Update-Struktur."""
    return {
        "update_id": update_id,
        "message": {
            "message_id": 100 + update_id,
            "date": 1_700_000_000,
            "from": {"id": user_id, "is_bot": False, "first_name": "Test"},
            "chat": {"id": user_id, "type": "private", "first_name": "Test"},
            "text": text,
        },
    }


def fake_urlopen(response_obj: dict, call_log: list):
    """Ersetzt urllib.request.urlopen: loggt Request-URLs, liefert Response."""
    import urllib.error

    class FakeResp:
        def __init__(self, body: dict):
            self._body = body

        def read(self) -> bytes:
            return json.dumps(self._body).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _urlopen(req, *a, **kw):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        call_log.append(url)
        # Der Fake akzeptiert getUpdates (Poll) und sendMessage (Antwort).
        if "getUpdates" in url:
            return FakeResp(response_obj)
        if "sendMessage" in url:
            return FakeResp({"ok": True, "result": {"message_id": 999}})
        raise urllib.error.URLError(f"unexpected url {url}")

    return _urlopen


class TestTgClientPolling:
    def test_get_updates_parses_message(self):
        updates = [make_update(42, "hallo", 1)]
        client = TgClient(token="TOKEN", allowlist={"42"})
        with patch("urllib.request.urlopen",
                   side_effect=fake_urlopen({"ok": True, "result": updates}, [])):
            msgs = client.get_updates()
        assert len(msgs) == 1
        assert msgs[0].user_id == 42
        assert msgs[0].text == "hallo"
        assert msgs[0].chat_id == 42

    def test_get_updates_uses_getupdates_api_no_webhook(self):
        """On-Device = Long-Polling via getUpdates, KEIN setWebhook (Relay)."""
        calls: list[str] = []
        client = TgClient(token="TOKEN", allowlist={"42"})
        with patch("urllib.request.urlopen",
                   side_effect=fake_urlopen({"ok": True, "result": []}, calls)):
            client.get_updates()
        # Der Client darf NIE setWebhook aufrufen (kein Cloud-Relay).
        assert all("setWebhook" not in u for u in calls)
        assert any("getUpdates" in u for u in calls)
        # Token wird in der API-URL übergeben (das ist korrekt: der Bot
        # muss sich bei Telegram authentifizieren), aber nicht geloggt.
        assert any("TOKEN" in u for u in calls)

    def test_send_message_posts_to_tg(self):
        calls: list[str] = []
        client = TgClient(token="TOKEN", allowlist={"42"})
        with patch("urllib.request.urlopen",
                   side_effect=fake_urlopen({"ok": True, "result": {}}, calls)):
            client.send_message(42, "antwort")
        assert any("sendMessage" in u for u in calls)
        assert any("chat_id=42" in u or "42" in u for u in calls)

    def test_send_message_redacts_token_in_exceptions(self):
        """Fehlermeldungen dürfen das Token nicht enthalten."""
        import urllib.error
        client = TgClient(token="SUPERSECRET", allowlist={"42"})
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with pytest.raises(Exception) as excinfo:
                client.send_message(42, "x")
        assert "SUPERSECRET" not in str(excinfo.value)


class TestAllowlistEnforcement:
    """SPECK-DoD Ziffer 2: Allowlist wird IM Client durchgesetzt."""

    def test_allowed_user_passes(self):
        client = TgClient(token="T", allowlist={"42"})
        assert client.is_allowed(42)

    def test_str_allowed_user_passes(self):
        client = TgClient(token="T", allowlist={"42"})
        # String- und Int-Eingaben werden normalisiert.
        assert client.is_allowed("42")

    def test_unallowed_user_denied(self):
        client = TgClient(token="T", allowlist={"42"})
        assert not client.is_allowed(999)

    def test_empty_allowlist_denies_all(self):
        client = TgClient(token="T", allowlist=set())
        assert not client.is_allowed(1)
        assert not client.is_allowed(42)


class TestMessageParsing:
    def test_message_dataclass_fields(self):
        upd = make_update(7, "text", 5)
        m = TgMessage(
            update_id=5, message_id=105, user_id=7, chat_id=7, text="text"
        )
        assert m.user_id == 7
        assert m.chat_id == 7
        assert m.text == "text"

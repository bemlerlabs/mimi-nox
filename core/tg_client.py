"""
◑ MiMi Nox – Telegram-Client (Sprint 3 G1): On-Device-Gateway, kein Relay.

Der Bot spricht DIREKT mit der Telegram-Long-Poll-API (getUpdates) — NIE über
ein Cloud-Relay/Webhook (kein setWebhook). Die Allowlist wird IM Client
durchgesetzt: Nachrichten von User-IDs außerhalb der statischen Allowlist
werden verworfen. Fehlermeldungen enthalten nie das rohe Token.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Iterable

_API_BASE = "https://api.telegram.org"


@dataclass
class TgMessage:
    """Ein normalisiertes Telegram-Update (private message)."""

    update_id: int
    message_id: int
    user_id: int
    chat_id: int
    text: str


class TgClient:
    """Minimaler, stdlib-basierter Telegram-Long-Poll-Client.

    - `get_updates`: ruft die Bot-API ab und liefert NUR erlaubte Nachrichten.
    - `send_message`: postet eine Antwort an eine erlaubte Chat-ID.
    - Token wird in der API-URL übergeben (notwendig für Auth), aber nie geloggt;
      Exceptions werden über `redact_token` maskiert.
    """

    def __init__(self, token: str, allowlist: Iterable[str | int], timeout: int = 30) -> None:
        self._token = (token or "").strip()
        self._allowlist = {str(x).strip() for x in allowlist if str(x).strip()}
        self._timeout = timeout

    # ── Allowlist ────────────────────────────────────────────────────────────
    def is_allowed(self, user_id: str | int) -> bool:
        """True, wenn die User-ID (normalisiert) in der Allowlist steht."""
        return str(user_id).strip() in self._allowlist

    def _url(self, method: str) -> str:
        return f"{_API_BASE}/bot{self._token}/{method}"

    def _call(self, method: str, params: dict | None = None) -> dict:
        url = self._url(method)
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 — wir re-raisen mit rotem Token
            from core.tg_tokens import redact_token
            raise type(exc)(redact_token(str(exc) or method)) from exc
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return {}

    # ── API ─────────────────────────────────────────────────────────────────
    def get_updates(self) -> list[TgMessage]:
        """Liefert erlaubte private Nachrichten (Long-Poll, kein Webhook).

        Updates von nicht erlaubten User-IDs werden verworfen (Default-Empty
        Allowlist → leeres Ergebnis, der Bot antwortet auf niemanden).
        """
        data = self._call("getUpdates", {"timeout": 0, "allowed_updates": '["message"]'})
        if not data.get("ok"):
            return []
        result = data.get("result") or []
        out: list[TgMessage] = []
        for upd in result:
            msg = upd.get("message")
            if not msg:
                continue
            frm = msg.get("from") or {}
            chat = msg.get("chat") or {}
            user_id = frm.get("id")
            if user_id is None:
                continue
            if not self.is_allowed(user_id):
                continue  # Nicht erlaubt → verwerfen (Allowlist-DoD)
            chat_id = chat.get("id", user_id)
            out.append(
                TgMessage(
                    update_id=int(upd.get("update_id", 0)),
                    message_id=int(msg.get("message_id", 0)),
                    user_id=int(user_id),
                    chat_id=int(chat_id),
                    text=str(msg.get("text", "")),
                )
            )
        return out

    def send_message(self, chat_id: int | str, text: str) -> dict:
        """Postet eine Antwort. Leerer Text = kein no-op-HTTP-Call."""
        if not str(text).strip():
            return {"ok": False, "error": "empty text"}
        params = {"chat_id": chat_id, "text": text}
        return self._call("sendMessage", params)


__all__ = ["TgClient", "TgMessage"]

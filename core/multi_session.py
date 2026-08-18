"""
◑ MiMi Nox – Multi-Session Persistence (Phase 2 Item 7)

Erweitert die bestehende Single-Session-Persistenz (core/session.py) um
mehrere parallele Sessions:

  ~/.mimi-nox/sessions/
    default.json          (legacy – aktive Session vor der Multi-Session-Ära)
    registry.json         (Meta-Infos: id, title, created_at, last_active)
    <8-hex>.json          (eine Session pro Datei, 8-Hex-Zeichen-Kürzel)

Design-Entscheidungen:
- Backward-compat: Bestehende `default.json` wird beim ersten Aufruf in die
  Registry migriert (kein Datenverlust, idempotent).
- Atomic writes: tmp + rename (POSIX-atomar), identisch zu core/session.py.
- Fail-safe: Corrupt JSON → leere Liste + None, nie ein Crash.
- Stabile IDs: UUID4-Hex-Kürzel (8 Zeichen) — kollisionsarm, lesbar.

MiMi Tech AI UG – Bad Liebenzell, Schwarzwald
"""

from __future__ import annotations

import json
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.types import Message

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SESSIONS_DIR: Path = Path(
    os.environ.get("MIMI_NOX_SESSIONS_DIR")
    or Path.home() / ".mimi-nox" / "sessions"
)
REGISTRY_FILE: Path = SESSIONS_DIR / "registry.json"
LEGACY_FILE: Path = SESSIONS_DIR / "default.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _new_id() -> str:
    """8-Hex-Zeichen-Kürzel aus secrets (kollisionsarm, lesbar)."""
    return secrets.token_hex(4)


def _now_iso() -> str:
    """ISO-8601 mit Mikropräzision — für deterministische Sortierung."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="microseconds")


def _atomic_write(path: Path, payload: str) -> None:
    """Atomic write via tmp + rename. Ignoriert OSError (best-effort, local-first)."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.parent / f".tmp_{os.getpid()}_{secrets.token_hex(4)}"
        tmp.write_text(payload, encoding="utf-8")
        tmp.rename(path)
    except OSError:
        # Best-effort – don't crash the app over persistence
        pass


def _load_registry() -> dict[str, Any]:
    """Lädt die Registry; bei Corrupt/Fehlend → leere Struktur. Nie raise."""
    if not REGISTRY_FILE.exists():
        return {"active_id": None, "sessions": []}
    try:
        raw = REGISTRY_FILE.read_text(encoding="utf-8")
        if not raw.strip():
            return {"active_id": None, "sessions": []}
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
            return {"active_id": None, "sessions": []}
        return data
    except (json.JSONDecodeError, OSError, TypeError, KeyError):
        return {"active_id": None, "sessions": []}


def _save_registry(registry: dict[str, Any]) -> None:
    _atomic_write(REGISTRY_FILE, json.dumps(registry, ensure_ascii=False, indent=2))


def _legacy_migration_needed() -> bool:
    """True, wenn default.json existiert und noch nicht migriert wurde."""
    if not LEGACY_FILE.exists():
        return False
    reg = _load_registry()
    # Migration ist done, wenn die "legacy"-Session in der Registry steht
    for s in reg.get("sessions", []):
        if s.get("title") == "legacy" and s.get("migrated_from") == "default.json":
            return False
    return True


def _run_legacy_migration() -> None:
    """Übernimmt default.json in die Registry (idempotent)."""
    if not _legacy_migration_needed():
        return
    try:
        raw = LEGACY_FILE.read_text(encoding="utf-8")
        data = json.loads(raw) if raw.strip() else []
    except (json.JSONDecodeError, OSError):
        # Corrupt legacy – migrieren wir die Datei nicht, lassen sie liegen.
        return
    if not isinstance(data, list):
        return

    # Nur valide Messages übernehmen (selbe Validierung wie core.session)
    valid: list[dict[str, str]] = []
    for item in data:
        if (
            isinstance(item, dict)
            and item.get("role") in ("user", "assistant", "system")
            and isinstance(item.get("content"), str)
        ):
            valid.append({"role": item["role"], "content": item["content"]})

    sid = _new_id()
    now = _now_iso()

    # Session-Datei schreiben
    _atomic_write(
        SESSIONS_DIR / f"{sid}.json",
        json.dumps(valid, ensure_ascii=False, indent=2),
    )

    # Registry aktualisieren
    reg = _load_registry()
    reg["sessions"].append(
        {
            "id": sid,
            "title": "legacy",
            "migrated_from": "default.json",
            "created_at": now,
            "last_active": now,
        }
    )
    if reg.get("active_id") is None:
        reg["active_id"] = sid
    _save_registry(reg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_session(title: str) -> dict[str, Any]:
    """Erzeugt eine neue Session und schreibt sie in die Registry."""
    sid = _new_id()
    now = _now_iso()
    # Leere Session-Datei
    _atomic_write(SESSIONS_DIR / f"{sid}.json", "[]")
    reg = _load_registry()
    entry = {
        "id": sid,
        "title": title,
        "created_at": now,
        "last_active": now,
    }
    reg["sessions"].append(entry)
    # Neue Session wird nicht automatisch aktiv – explizit via switch_to()
    _save_registry(reg)
    return entry


def list_sessions() -> list[dict[str, Any]]:
    """Gibt alle Sessions zurück, sortiert nach last_active absteigend.

    Triggert die Legacy-Migration, falls default.json existiert.
    """
    if _legacy_migration_needed():
        _run_legacy_migration()
    reg = _load_registry()
    sessions = [s for s in reg.get("sessions", []) if isinstance(s, dict)]
    sessions.sort(key=lambda s: s.get("last_active", ""), reverse=True)
    return sessions


def get_session(sid: str) -> dict[str, Any] | None:
    """Gibt die Meta-Infos einer einzelnen Session zurück oder None."""
    for s in _load_registry().get("sessions", []):
        if s.get("id") == sid:
            return s
    return None


def rename_session(sid: str, new_title: str) -> None:
    """Ändert den Titel einer Session. No-op wenn ID unbekannt."""
    reg = _load_registry()
    for s in reg.get("sessions", []):
        if s.get("id") == sid:
            s["title"] = new_title
            _save_registry(reg)
            return


def delete_session(sid: str) -> None:
    """Löscht eine Session (Meta + Message-Datei).

    Wenn die gelöschte Session aktiv war, wird active_id auf None gesetzt.
    """
    reg = _load_registry()
    reg["sessions"] = [s for s in reg.get("sessions", []) if s.get("id") != sid]
    if reg.get("active_id") == sid:
        reg["active_id"] = None
    _save_registry(reg)
    (SESSIONS_DIR / f"{sid}.json").unlink(missing_ok=True)


def switch_to(sid: str) -> None:
    """Setzt die aktive Session. No-op wenn ID unbekannt."""
    reg = _load_registry()
    known = {s.get("id") for s in reg.get("sessions", [])}
    if sid not in known:
        return
    reg["active_id"] = sid
    # last_active aktualisieren
    for s in reg.get("sessions", []):
        if s.get("id") == sid:
            s["last_active"] = _now_iso()
            break
    _save_registry(reg)


def get_active_id() -> str | None:
    """ID der aktiven Session oder None."""
    reg = _load_registry()
    active = reg.get("active_id")
    if not active:
        return None
    # Nur zurückgeben, wenn die Session noch existiert
    if not any(s.get("id") == active for s in reg.get("sessions", [])):
        return None
    return active


# ---------------------------------------------------------------------------
# Message I/O
# ---------------------------------------------------------------------------


def save_messages(sid: str, messages: list[Message]) -> None:
    """Speichert die Messages einer Session atomar auf Disk."""
    payload = json.dumps(list(messages), ensure_ascii=False, indent=2)
    _atomic_write(SESSIONS_DIR / f"{sid}.json", payload)
    # last_active aktualisieren
    reg = _load_registry()
    for s in reg.get("sessions", []):
        if s.get("id") == sid:
            s["last_active"] = _now_iso()
            break
    _save_registry(reg)


def load_messages(sid: str) -> list[Message]:
    """Lädt die Messages einer Session. Rückgabetyp ist [] bei Fehler."""
    f = SESSIONS_DIR / f"{sid}.json"
    if not f.exists():
        return []
    try:
        raw = f.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        valid: list[Message] = []
        for item in data:
            if (
                isinstance(item, dict)
                and item.get("role") in ("user", "assistant", "system")
                and isinstance(item.get("content"), str)
            ):
                valid.append(Message(role=item["role"], content=item["content"]))
        return valid
    except (json.JSONDecodeError, OSError, TypeError, KeyError):
        return []


def session_info(sid: str) -> dict[str, Any] | None:
    """Meta-Infos + Message-Zahl für eine Session. None wenn unbekannt."""
    meta = get_session(sid)
    if meta is None:
        return None
    msgs = load_messages(sid)
    return {
        "id": sid,
        "title": meta.get("title", ""),
        "message_count": len(msgs),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("last_active", ""),
        "is_active": meta.get("id") == get_active_id(),
    }


# ---------------------------------------------------------------------------
# Backward-compat Shims (für Übergangsphase: alte core.session-API)
# ---------------------------------------------------------------------------


def active_session_id() -> str:
    """ID der aktiven Session; falls keine, legt eine "default"-Session an.

    Verwendet von der TUI, damit sie ohne Kenntnis der Multi-Session-API
    weiterarbeiten kann.
    """
    sid = get_active_id()
    if sid is not None:
        return sid
    # Fallback: default.json existiert?
    if LEGACY_FILE.exists():
        # Legacy-Datei als Session übernehmen
        list_sessions()  # triggert Migration
        return get_active_id() or create_session("default")["id"]
    return create_session("default")["id"]


def save_active_session(messages: list[Message]) -> None:
    """Speichert Messages unter der aktiven Session (alias für save_messages)."""
    sid = active_session_id()
    save_messages(sid, messages)

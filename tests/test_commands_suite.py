"""Tests für die /commands-Suite (Phase 2 Item 8).

Verifiziert:
- Alle Roadmap-Commands stehen in der Registry:
  /help /model /engine /configure /swarm /post /plan /review
- Info-Commands (/help /model /engine /configure) rendern LOCALL (kein LLM),
  mit echten Daten aus model_provider / engine_config.
- Prompt-Commands (/plan /review) folgen dem {input}-Template-Muster wie /post.
- Usage-Feedback bei fehlenden Args (resolve_command).
- Completions + is_command erfassen die neuen Commands.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import core.commands as cmds


# ---------------------------------------------------------------------------
# Registry-Vollständigkeit (Roadmap Item 8)
# ---------------------------------------------------------------------------


def test_all_roadmap_commands_are_in_registry():
    required = {
        "/help", "/model", "/engine", "/configure",
        "/swarm", "/post", "/plan", "/review",
    }
    missing = required - set(cmds.COMMANDS)
    assert not missing, f"In Registry fehlt: {missing}"


def test_all_registry_commands_have_descriptions():
    for name in cmds.COMMANDS:
        desc = cmds._COMMAND_DESCRIPTIONS.get(name)
        assert desc, f"Keine Description für {name}"


def test_completions_include_new_commands():
    all_comps = cmds.get_completions("/")
    for name in ("/help", "/model", "/engine", "/configure", "/plan", "/review"):
        assert name in all_comps


def test_is_command_recognizes_new_commands():
    for name in ("/help", "/model", "/engine", "/configure", "/plan", "/review"):
        assert cmds.is_command(name)


# ---------------------------------------------------------------------------
# Info-Commands
# ---------------------------------------------------------------------------


def test_info_commands_are_detected():
    for name in ("/help", "/model", "/engine", "/configure"):
        assert cmds.is_info_command(name), f"{name} nicht als Info-Command erkannt"
        assert cmds.is_info_command(f"{name} extra"), "Args sollten Info-Status nicht ändern"


def test_non_info_commands_are_not_info():
    assert not cmds.is_info_command("/post")
    assert not cmds.is_info_command("hello")
    assert not cmds.is_info_command("/plan")


def test_render_help_lists_all_commands_with_descriptions():
    out = cmds.render_info_command("/help")
    assert out, "/help rendert nichts"
    # Alle Registry-Commands müssen gelistet sein
    for name in cmds.COMMANDS:
        assert name in out, f"{name} fehlt in /help-Output"


def test_render_model_shows_active_provider_and_model(monkeypatch):
    import core.model_provider as mp

    class _Cfg:
        provider = "local_ollama"
        model = "gemma4:e4b"
        base_url = "http://127.0.0.1:11434"
        label = "Lokale Ollama"

    monkeypatch.setattr(mp, "get_active_provider", lambda: _Cfg())
    out = cmds.render_info_command("/model")
    assert "gemma4:e4b" in out
    assert "local_ollama" in out


def test_render_engine_shows_config_or_missing(monkeypatch, tmp_path: Path):
    import core.engine_config as ec
    cfg_file = tmp_path / "engine.json"
    monkeypatch.setattr(ec, "default_config_path", lambda: cfg_file)

    # Fall 1: keine Config → Hinweis auf --configure
    out = cmds.render_info_command("/engine")
    assert "miminox tui --configure" in out

    # Fall 2: mit Config → Provider/Modell sichtbar
    ec.save_engine_config(
        ec.EngineChoice(provider="local_ollama", model="llama3.1:8b"),
        path=cfg_file,
    )
    out2 = cmds.render_info_command("/engine")
    assert "llama3.1:8b" in out2


def test_render_configure_shows_current_state(monkeypatch):
    out = cmds.render_info_command("/configure")
    # Zeigt aktiven Status + Weg zur Engine-Auswahl
    assert "miminox tui --configure" in out
    assert "engine" in out.lower()


def test_render_unknown_info_returns_empty():
    assert cmds.render_info_command("/help-missing") == ""


# ---------------------------------------------------------------------------
# Prompt-Commands (/plan, /review)
# ---------------------------------------------------------------------------


def test_plan_is_prompt_command_with_input_placeholder():
    assert "{input}" in cmds.COMMANDS["/plan"]
    resolved = cmds.resolve_command("/plan Eine REST API für ein Buchungssystem")
    assert "Eine REST API für ein Buchungssystem" in resolved
    assert "/plan" not in resolved  # Template-Form, kein roher Command


def test_plan_without_arg_gives_usage_feedback():
    out = cmds.resolve_command("/plan")
    assert "Usage" in out and "/plan" in out
    # Und die Description ist dabei
    assert "Plan" in out or "plan" in out


def test_review_is_prompt_command():
    assert "{input}" in cmds.COMMANDS["/review"]
    resolved = cmds.resolve_command("/review def f(): pass")
    assert "def f(): pass" in resolved


def test_post_still_works_unchanged():
    out = cmds.resolve_command("/post AI productivity")
    assert "AI productivity" in out
    assert "LinkedIn" in out


def test_swarm_and_learn_semantics_unchanged():
    assert cmds.is_swarm_command("/swarm task")
    assert cmds.extract_swarm_task("/swarm task") == "task"
    assert cmds.is_learn_command("/learn pattern")
    assert cmds.extract_learn_topic("/learn pattern") == "pattern"

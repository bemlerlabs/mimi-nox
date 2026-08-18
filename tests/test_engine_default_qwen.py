"""P0-2 DoD: Qwen-DGX als Standard-Engine (User-Mandat 2026-08-18).

Kein Ollama-Pull, kein Modell-Download am Mac. Provider-Wahl = END-USER-Onboarding
(--configure flag). Default bleibt Qwen 3.8 27B auf DGX Spark.

Test-Regeln (CTO-freigegeben):
- Deterministisch (keine AI-Requests).
- Evidenz: Funktion + Konstanten + Verhalten der default_engine_choice().
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch as mock_patch

import pytest

from core.engine_config import (
    DEFAULT_DGX_SPARK_URL,
    DEFAULT_DGX_SPARK_MODEL,
    OPENAI_COMPAT,
    EngineChoice,
    default_engine_choice,
    load_engine_config,
    save_engine_config,
)


# ── Konstanten: Qwen-DGX-Defaults korrekt gepinnt ────────────────────────────

def test_default_dgx_spark_url_is_correct():
    assert DEFAULT_DGX_SPARK_URL == "http://spark-2c73.tail8f685e.ts.net:8000/v1"


def test_default_dgx_spark_model_is_correct():
    assert DEFAULT_DGX_SPARK_MODEL == "qwen38-27b-unsloth-nvfp4"


# ── default_engine_choice(): Standard-Engine liefert Qwen-DGX ──────────────

def test_default_engine_choice_returns_qwen_dgx():
    choice = default_engine_choice()
    assert choice.provider == OPENAI_COMPAT
    assert choice.model == DEFAULT_DGX_SPARK_MODEL
    assert choice.api_url == DEFAULT_DGX_SPARK_URL


def test_default_engine_choice_to_flags():
    choice = default_engine_choice()
    flags = choice.to_flags()
    assert flags == ["--model", DEFAULT_DGX_SPARK_MODEL, "--api-url", DEFAULT_DGX_SPARK_URL]


def test_default_engine_choice_apply_env():
    choice = default_engine_choice()
    with mock_patch.dict(os.environ, {}, clear=True):
        choice.apply_env()
        assert os.environ["MIMI_NOX_MODEL"] == DEFAULT_DGX_SPARK_MODEL
        assert os.environ["MIMI_OPENAI_COMPAT_BASE_URL"] == DEFAULT_DGX_SPARK_URL


# ── Persistence: Default wird NIE stillschweigend persistiert ───────────────

def test_no_config_load_returns_none(tmp_path):
    cfg = tmp_path / "engine.json"
    assert load_engine_config(cfg) is None


def test_save_and_load_roundtrip(tmp_path):
    cfg = tmp_path / "engine.json"
    choice = default_engine_choice()
    assert save_engine_config(choice, cfg) is True
    loaded = load_engine_config(cfg)
    assert loaded is not None
    assert loaded.provider == OPENAI_COMPAT
    assert loaded.model == DEFAULT_DGX_SPARK_MODEL
    assert loaded.api_url == DEFAULT_DGX_SPARK_URL


def test_persisted_config_never_contains_secret(tmp_path):
    """AGENTS.md: kein Secret-Persist. engine.json darf keine API-Keys enthalten."""
    cfg = tmp_path / "engine.json"
    choice = default_engine_choice()
    save_engine_config(choice, cfg)
    raw = json.loads(cfg.read_text())
    assert "api_key" not in raw
    assert "secret" not in raw
    assert "token" not in raw


# ── Provider-Onboarding: END-USER kann Provider ändern ──────────────────────

def test_user_custom_endpoint_persisted(tmp_path):
    """END-USER wählt eigenen OpenAI-kompatiblen Endpoint (z.B. OpenRouter)."""
    cfg = tmp_path / "engine.json"
    choice = EngineChoice(
        provider=OPENAI_COMPAT,
        model="gpt-4o",
        api_url="https://openrouter.ai/api/v1",
    )
    assert save_engine_config(choice, cfg) is True
    loaded = load_engine_config(cfg)
    assert loaded is not None
    assert loaded.api_url == "https://openrouter.ai/api/v1"
    assert loaded.model == "gpt-4o"


def test_user_ollama_provider_persisted(tmp_path):
    """END-USER wählt Ollama als Provider."""
    from core.engine_config import LOCAL_OLLAMA
    cfg = tmp_path / "engine.json"
    choice = EngineChoice(
        provider=LOCAL_OLLAMA,
        model="llama3:8b",
    )
    assert save_engine_config(choice, cfg) is True
    loaded = load_engine_config(cfg)
    assert loaded is not None
    assert loaded.provider == LOCAL_OLLAMA
    assert loaded.model == "llama3:8b"
    assert loaded.api_url is None


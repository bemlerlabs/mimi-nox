"""
tests/test_finding_09_scheduler_fixes.py

Finding 9: Scheduler had model=None bug and hardcoded "Europe/Berlin" timezone.
Fix: model from env var, timezone from env var with fallback.

Given-When-Then Tests:
  1. GIVEN MIMI_NOX_TIMEZONE=Asia/Tokyo WHEN add_job() THEN CronTrigger uses Tokyo
  2. GIVEN default env WHEN add_job() THEN CronTrigger uses Europe/Berlin (fallback)
  3. GIVEN MIMI_NOX_MODEL=llama3.3 WHEN _run_task() THEN react_loop gets llama3.3
  4. GIVEN default env WHEN _run_task() THEN react_loop gets gemma4:e4b (fallback)
"""
import os
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from core.scheduler import NoxScheduler


# ── Test 1: GIVEN Tokyo timezone WHEN add_job THEN CronTrigger uses Tokyo ─────

def test_given_tokyo_tz_when_add_job_then_uses_tokyo(monkeypatch):
    """GIVEN MIMI_NOX_TIMEZONE=Asia/Tokyo WHEN add_job() THEN trigger uses Tokyo."""
    monkeypatch.setenv("MIMI_NOX_TIMEZONE", "Asia/Tokyo")

    scheduler = NoxScheduler()
    scheduler._scheduler = MagicMock()
    scheduler._scheduler.get_jobs.return_value = []

    with patch("core.scheduler._JOBS_FILE") as mock_file:
        mock_file.parent.mkdir = MagicMock()
        mock_file.write_text = MagicMock()
        scheduler.add_job("test task", "0 8 * * *", "test_id")

    call_args = scheduler._scheduler.add_job.call_args
    trigger = call_args.kwargs.get("trigger") or call_args[1].get("trigger")
    assert str(trigger.timezone) == "Asia/Tokyo"


# ── Test 2: GIVEN no timezone env WHEN add_job THEN uses Berlin fallback ──────

def test_given_no_tz_env_when_add_job_then_uses_berlin(monkeypatch):
    """GIVEN no MIMI_NOX_TIMEZONE set WHEN add_job() THEN uses Europe/Berlin."""
    monkeypatch.delenv("MIMI_NOX_TIMEZONE", raising=False)

    scheduler = NoxScheduler()
    scheduler._scheduler = MagicMock()
    scheduler._scheduler.get_jobs.return_value = []

    with patch("core.scheduler._JOBS_FILE") as mock_file:
        mock_file.parent.mkdir = MagicMock()
        mock_file.write_text = MagicMock()
        scheduler.add_job("test task", "0 8 * * *", "test_id")

    call_args = scheduler._scheduler.add_job.call_args
    trigger = call_args.kwargs.get("trigger") or call_args[1].get("trigger")
    assert str(trigger.timezone) == "Europe/Berlin"


# ── Test 3: GIVEN custom model WHEN _run_task THEN passes model to react_loop ─

@pytest.mark.asyncio
async def test_given_custom_model_when_run_task_then_passes_to_react(monkeypatch):
    """GIVEN MIMI_NOX_MODEL=llama3.3 WHEN _run_task() THEN react_loop receives llama3.3."""
    monkeypatch.setenv("MIMI_NOX_MODEL", "llama3.3")

    scheduler = NoxScheduler()
    captured_model = []

    async def fake_react_loop(question, model, context):
        captured_model.append(model)
        return "test result"

    with patch("core.react.react_loop", side_effect=fake_react_loop):
        await scheduler._run_task("test task", "test_id")

    assert captured_model[0] == "llama3.3"


# ── Test 4: GIVEN no model env WHEN _run_task THEN uses gemma4:e4b fallback ───

@pytest.mark.asyncio
async def test_given_no_model_env_when_run_task_then_uses_gemma4(monkeypatch):
    """GIVEN no MIMI_NOX_MODEL set WHEN _run_task() THEN react_loop gets gemma4:e4b."""
    monkeypatch.delenv("MIMI_NOX_MODEL", raising=False)

    scheduler = NoxScheduler()
    captured_model = []

    async def fake_react_loop(question, model, context):
        captured_model.append(model)
        return "test result"

    with patch("core.react.react_loop", side_effect=fake_react_loop):
        await scheduler._run_task("test task", "test_id")

    assert captured_model[0] == "gemma4:e4b"

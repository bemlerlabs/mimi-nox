from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.test_tool_calling import _make_ollama_response


@pytest.mark.asyncio
async def test_given_project_skill_when_fast_path_runs_then_no_model_call_is_needed(monkeypatch, tmp_path):
    """
    GIVEN /project is a deterministic local-analysis skill
    WHEN the fast path handles it
    THEN it returns a project listing without an LLM call.
    """
    project = tmp_path / "Documents" / "mimi-fast"
    project.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='mimi-fast'\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    from core.skill_fastpath import run_skill_fast_path

    result = await run_skill_fast_path("project-assistant", "finde mimi-fast")

    assert result is not None
    assert "mimi-fast" in result
    assert "Gefundene Projekte" in result


@pytest.mark.asyncio
async def test_given_project_query_mentions_current_repo_when_fast_path_runs_then_current_project_is_analyzed(monkeypatch, tmp_path):
    """
    GIVEN the user asks for the current repository by name plus analysis words
    WHEN the project fast path handles the request
    THEN it analyzes the current project instead of literal full-phrase search.
    """
    project = tmp_path / "Documents" / "mimi-nox"
    project.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='mimi-nox'\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(project)

    from core.skill_fastpath import run_skill_fast_path

    result = await run_skill_fast_path(
        "project-assistant",
        "mimi-nox Ist-Zustand analysieren und technische Fixes nennen",
    )

    assert result is not None
    assert "# Ist-Zustand: mimi-nox" in result
    assert str(project) in result


def test_given_tool_schemas_when_called_twice_then_same_cached_object_is_reused():
    """
    GIVEN tool schemas are static for the process
    WHEN get_tool_schemas is called repeatedly inside the TTL
    THEN it reuses the cached schema object.
    """
    from core.tools import get_tool_schemas

    first = get_tool_schemas()
    second = get_tool_schemas()

    assert first is second


@pytest.mark.asyncio
async def test_given_pdf_skill_when_fast_path_runs_then_real_pdf_is_created_without_model(monkeypatch, tmp_path):
    """
    GIVEN /pdf is a deterministic artifact skill
    WHEN the fast path handles a minimal PDF request
    THEN it creates a real PDF file and returns a PDF marker without an LLM call.
    """
    monkeypatch.setenv("HOME", str(tmp_path))

    from core.skill_fastpath import run_skill_fast_path

    result = await run_skill_fast_path(
        "pdf-creator",
        "Erstelle ein professionelles 1-seitiges Executive Briefing zu MiMi Nox",
    )

    assert result is not None
    assert "PDF_FILE:" in result
    pdf_path = result.split("PDF_FILE:", 1)[1].splitlines()[0].strip()
    assert pdf_path.endswith(".pdf")
    assert (tmp_path / "Downloads" / Path(pdf_path).name).exists()


def test_given_skill_loader_when_load_all_called_twice_then_second_call_uses_cache(tmp_path):
    """
    GIVEN skills have already been loaded
    WHEN load_all is called again within 60 seconds
    THEN markdown files are not read again.
    """
    skills_dir = tmp_path / "skills"
    builtin_dir = tmp_path / "builtin"
    skills_dir.mkdir()
    builtin_dir.mkdir()
    (builtin_dir / "help.md").write_text(
        "# help\n\n**Trigger**: /help\n**Description**: Hilfe\n**Tools**: \n\n## System Prompt\nHallo",
        encoding="utf-8",
    )

    from core.skills import SkillLoader

    loader = SkillLoader(skills_dir=skills_dir, builtin_dir=builtin_dir)
    first = loader.load_all()
    with patch("pathlib.Path.read_text", side_effect=AssertionError("cache miss")):
        second = loader.load_all()

    assert first[0].name == second[0].name == "help"


def test_given_discover_projects_when_called_twice_then_second_call_uses_cache(monkeypatch, tmp_path):
    """
    GIVEN project discovery already scanned a root
    WHEN the same query runs within 60 seconds
    THEN os.walk is not called again.
    """
    project = tmp_path / "Documents" / "mimi-cache"
    project.mkdir(parents=True)
    (project / ".git").mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='mimi-cache'\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))

    from core.project_discovery import discover_project_records

    first = discover_project_records(query="mimi", roots=[tmp_path / "Documents"])
    with patch("core.project_discovery.os.walk", side_effect=AssertionError("cache miss")):
        second = discover_project_records(query="mimi", roots=[tmp_path / "Documents"])

    assert first == second


@pytest.mark.asyncio
async def test_given_long_answer_when_streamed_then_no_per_word_sleep_is_used():
    """
    GIVEN the final answer is long
    WHEN chat_with_tools streams the words to the UI
    THEN it does not add artificial per-word delay.
    """
    from core.chat import chat_with_tools

    long_text = " ".join(f"wort{i}" for i in range(120))
    pure_text = _make_ollama_response(content=long_text, tool_calls=[])

    with patch("core.chat.ollama.AsyncClient") as MockClient, patch("core.chat.asyncio.sleep", new=AsyncMock()) as mock_sleep:
        client = MagicMock()
        client.chat = AsyncMock(return_value=pure_text)
        MockClient.return_value = client

        result = await chat_with_tools(
            model="gemma4:12b",
            history=[{"role": "user", "content": "lange antwort"}],
            on_chunk=lambda c: None,
        )

    assert result == long_text
    mock_sleep.assert_not_awaited()

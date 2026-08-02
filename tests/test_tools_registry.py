"""
◑ MiMi Nox – Phase 0.8 TDD
tests/test_tools_registry.py

Tests für core/tools/registry.py: execute_tool, TOOL_MAP, get_filtered_tool_schemas.

Given / When / Then – strikte Einhaltung.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tools.base import ShellConfirmationRequired
from core.tools.registry import TOOL_MAP, execute_tool, get_filtered_tool_schemas


class TestExecuteTool:

    @pytest.mark.asyncio
    async def test_executes_known_tool(self):
        """
        GIVEN  Tool-Name existiert in TOOL_MAP
        WHEN   execute_tool("get_datetime", {}) aufgerufen
        THEN   Tool wird ausgeführt und Ergebnis zurückgegeben
        """
        mock_fn = AsyncMock(return_value="Montag, ...")
        with patch.dict("core.tools.registry.TOOL_MAP", {"get_datetime": mock_fn}, clear=False):
            result = await execute_tool("get_datetime", {})

        assert "Montag" in result
        mock_fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_error_for_unknown_tool(self):
        """
        GIVEN  Tool-Name existiert nicht
        WHEN   execute_tool("unknown_tool", {}) aufgerufen
        THEN   Rückgabe enthält "nicht gefunden"
        """
        result = await execute_tool("unknown_tool", {})
        assert "nicht gefunden" in result

    @pytest.mark.asyncio
    async def test_passes_arguments_to_tool(self):
        """
        GIVEN  Tool mit Parametern
        WHEN   execute_tool("web_search", {"query": "test"}) aufgerufen
        THEN   Parameter werden weitergegeben
        """
        mock_fn = AsyncMock(return_value="Ergebnisse")
        with patch.dict("core.tools.registry.TOOL_MAP", {"web_search": mock_fn}, clear=False):
            result = await execute_tool("web_search", {"query": "test"})

        mock_fn.assert_called_once_with(query="test")

    @pytest.mark.asyncio
    async def test_converts_list_result_to_string(self):
        """
        GIVEN  Tool gibt Liste zurück
        WHEN   execute_tool aufgerufen
        THEN   Liste wird mit \n verbunden
        """
        mock_fn = AsyncMock(return_value=["a", "b", "c"])
        with patch.dict("core.tools.registry.TOOL_MAP", {"list_directory": mock_fn}, clear=False):
            result = await execute_tool("list_directory", {"path": "/tmp"})

        assert isinstance(result, str)
        assert "a\nb\nc" == result

    @pytest.mark.asyncio
    async def test_passes_shell_confirmation_through(self):
        """
        GIVEN  Tool wirft ShellConfirmationRequired
        WHEN   execute_tool("run_shell", {"command": "ls"}) aufgerufen
        THEN   Exception wird durchgereicht (nicht gefangen)
        """
        with pytest.raises(ShellConfirmationRequired):
            await execute_tool("run_shell", {"command": "ls"})

    @pytest.mark.asyncio
    async def test_catches_generic_exceptions(self):
        """
        GIVEN  Tool wirft Exception
        WHEN   execute_tool aufgerufen
        THEN   Rückgabe enthält "[Tool-Fehler"
        """
        mock_fn = AsyncMock(side_effect=ValueError("something broke"))
        with patch.dict("core.tools.registry.TOOL_MAP", {"web_search": mock_fn}, clear=False):
            result = await execute_tool("web_search", {"query": "test"})

        assert "Tool-Fehler" in result


class TestToolMap:

    def test_contains_all_expected_tools(self):
        """
        GIVEN  TOOL_MAP
        WHEN   auf Vollständigkeit geprüft
        THEN   Enthält alle 30 erwarteten Einträge
        """
        expected_tools = {
            "manage_tasks", "web_search", "file_search",
            "discover_projects", "analyze_project",
            "create_source_notebook", "query_source_notebook", "export_source_brief",
            "read_file", "list_directory",
            "get_datetime", "run_shell",
            "load_workspace", "analyze_image",
            "vision_click", "vision_type",
            "take_screenshot",
            "browser_go", "browser_screenshot", "browser_click",
            "browser_type", "browser_press",
            "generate_chart", "create_pdf",
            "create_pitch_deck", "create_pptx_deck",
            "inspect_pptx_template", "edit_pptx_template", "qa_pptx_deck",
            "create_svg",
        }
        assert set(TOOL_MAP.keys()) == expected_tools

    def test_all_tools_are_callable(self):
        """
        GIVEN  TOOL_MAP Einträge
        WHEN   auf Callable geprüft
        THEN   Jeder Eintrag ist eine Funktion
        """
        for name, func in TOOL_MAP.items():
            assert callable(func), f"TOOL_MAP['{name}'] ist nicht callable"


class TestGetFilteredToolSchemas:

    def test_returns_subset_by_whitelist(self):
        """
        GIVEN  whitelist=["web_search"]
        WHEN   get_filtered_tool_schemas(whitelist) aufgerufen
        THEN   Nur web_search Schema wird zurückgegeben
        """
        result = get_filtered_tool_schemas(["web_search"])
        assert len(result) == 1
        assert result[0]["function"]["name"] == "web_search"

    def test_returns_empty_for_empty_whitelist(self):
        """
        GIVEN  whitelist=[]
        WHEN   get_filtered_tool_schemas([]) aufgerufen
        THEN   Leere Liste wird zurückgegeben
        """
        assert get_filtered_tool_schemas([]) == []

    def test_ignores_unknown_tool_names(self):
        """
        GIVEN  whitelist enthält unbekannte Tools
        WHEN   get_filtered_tool_schemas aufgerufen
        THEN   Nur bekannte Tools werden zurückgegeben
        """
        result = get_filtered_tool_schemas(["web_search", "unknown_tool"])
        assert len(result) == 1
        assert result[0]["function"]["name"] == "web_search"

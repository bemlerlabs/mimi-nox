"""
tests/test_finding_03_websearch_returntype.py

Finding 3: web_search() Signatur sagte list[dict], gab aber str zurück.
Fix: Signatur auf -> str korrigiert.

Given-When-Then Tests:
  1. GIVEN valid query WHEN web_search() returns results THEN type is str
  2. GIVEN valid query WHEN no results found THEN type is str (not list)
  3. GIVEN empty query WHEN web_search() THEN raises ValueError
"""
import asyncio
from unittest.mock import patch, MagicMock

import pytest


# ── Test 1: GIVEN results WHEN search THEN returns str ────────────────────────

@pytest.mark.asyncio
async def test_given_results_when_search_then_returns_str():
    """GIVEN DuckDuckGo returns results WHEN web_search() THEN return type is str."""
    mock_results = [
        {"title": "Test", "href": "https://example.com", "body": "A test result"},
    ]

    with patch("core.tools.web_search.DDGS") as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = mock_results
        MockDDGS.return_value = mock_instance

        from core.tools import web_search
        result = await web_search("test query")

    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert "https://example.com" in result
    assert "Test" in result


# ── Test 2: GIVEN no results WHEN search THEN returns str (not list) ──────────

@pytest.mark.asyncio
async def test_given_no_results_when_search_then_returns_str():
    """GIVEN DuckDuckGo returns empty WHEN web_search() THEN returns str, not list."""
    with patch("core.tools.web_search.DDGS") as MockDDGS:
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = []
        MockDDGS.return_value = mock_instance

        from core.tools import web_search
        result = await web_search("nonexistent query")

    assert isinstance(result, str), f"Expected str, got {type(result)}"
    assert "Keine Ergebnisse" in result


# ── Test 3: GIVEN empty query WHEN search THEN ValueError ─────────────────────

@pytest.mark.asyncio
async def test_given_empty_query_when_search_then_raises_valueerror():
    """GIVEN empty string WHEN web_search() THEN raises ValueError."""
    from core.tools import web_search

    with pytest.raises(ValueError, match="leer"):
        await web_search("")

    with pytest.raises(ValueError, match="leer"):
        await web_search("   ")

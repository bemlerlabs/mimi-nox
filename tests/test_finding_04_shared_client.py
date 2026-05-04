"""
tests/test_finding_04_shared_client.py

Finding 4: analyze_image() created a new AsyncClient per call.
Fix: Shared module-level client via _get_shared_client().

Given-When-Then Tests:
  1. GIVEN _get_shared_client() called twice WHEN comparing instances THEN same object
  2. GIVEN shared client is None WHEN first call THEN creates new client
  3. GIVEN shared client already exists WHEN second call THEN reuses it (no new client)
"""
from unittest.mock import patch, MagicMock

import pytest

import core.tools as tools_module


# ── Test 1: GIVEN two calls WHEN getting client THEN same instance ────────────

def test_given_two_calls_when_get_shared_client_then_same_instance():
    """GIVEN _get_shared_client() called twice WHEN comparing THEN same object returned."""
    # Reset module state
    tools_module._shared_client = None

    client1 = tools_module._get_shared_client()
    client2 = tools_module._get_shared_client()

    assert client1 is client2, "Expected same client instance, got different objects"

    # Cleanup
    tools_module._shared_client = None


# ── Test 2: GIVEN client is None WHEN first call THEN creates new ─────────────

def test_given_client_none_when_first_call_then_creates_new():
    """GIVEN _shared_client is None WHEN _get_shared_client() THEN creates AsyncClient."""
    tools_module._shared_client = None

    client = tools_module._get_shared_client()

    assert client is not None
    assert tools_module._shared_client is client

    # Cleanup
    tools_module._shared_client = None


# ── Test 3: GIVEN client exists WHEN second call THEN no new creation ─────────

def test_given_client_exists_when_second_call_then_no_new_creation():
    """GIVEN _shared_client already set WHEN _get_shared_client() THEN AsyncClient() not called again."""
    tools_module._shared_client = None

    with patch("core.tools.ollama.AsyncClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        # First call: should create
        tools_module._get_shared_client()
        assert MockClient.call_count == 1

        # Second call: should NOT create new
        tools_module._get_shared_client()
        assert MockClient.call_count == 1, "AsyncClient() should not be called twice"

    # Cleanup
    tools_module._shared_client = None

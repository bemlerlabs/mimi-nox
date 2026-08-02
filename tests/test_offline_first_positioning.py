from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = [
    ROOT / "README.md",
    ROOT / "app" / "index.html",
    ROOT / "app" / "src" / "locales" / "de.json",
    ROOT / "app" / "src" / "locales" / "en.json",
]


def test_given_public_scope_when_scanned_then_absolutist_claims_are_absent():
    """GIVEN the public scope of the Root-PWA
    WHEN its copy is scanned
    THEN absolutist/over-broad claims are absent.
    """
    banned = [
        "Zero Human",
        "Firma",
        "CEO",
        "CTO",
        "Krisen",
        "never sends a single byte",
        "100% offline",
        "100% lokal",
        "weltweit erreichbar",
        "reachable worldwide",
        "Globaler Tunnel",
        "global tunnel",
        "2.5 GB",
        "2.5GB",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_FILES)
    for term in banned:
        assert term not in text, f"absolutist claim found: {term!r}"


def test_given_gemma_copy_when_checked_then_model_size_and_context_are_correct():
    """GIVEN the public copy of the Root-PWA
    WHEN the Gemma model story is checked
    THEN the artifact size and context length are accurate.
    """
    text = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_FILES)
    assert "gemma4:12b" in text
    assert "16GB RAM" in text
    assert "256K" in text


def test_given_root_pwa_when_components_checked_then_provider_badge_and_offline_help_exist():
    """GIVEN the Root-PWA is a React app
    WHEN its UI components are inspected
    THEN model provider state and offline help are first-class UI elements.
    """
    chat_input = (ROOT / "app" / "src" / "components" / "dashboard" / "ChatInput.tsx").read_text(encoding="utf-8")
    chat_layout = (ROOT / "app" / "src" / "components" / "dashboard" / "ChatLayout.tsx").read_text(encoding="utf-8")
    settings = (ROOT / "app" / "src" / "components" / "dashboard" / "SettingsPanel.tsx").read_text(encoding="utf-8")

    # Provider state badge: model name + local indicator
    assert "gemma4:12b" in chat_input
    assert "Lokal" in chat_input
    # Offline / connection status help
    assert "disconnected" in chat_layout
    assert "WifiOff" in chat_layout
    # Chat area (messages list)
    assert "messages" in chat_layout
    # Attachment + mic actions
    assert "Paperclip" in chat_input
    assert "Mic" in chat_input
    # Settings entry point opens provider panel
    assert "setSettingsOpen(true)" in chat_layout
    # Provider panel exposes OpenAI-compatible endpoint
    assert "openai_compatible" in settings

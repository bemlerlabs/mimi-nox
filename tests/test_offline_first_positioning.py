from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_FILES = [
    ROOT / "README.md",
    ROOT / "app" / "src" / "index.html",
    ROOT / "app" / "src" / "mobile.html",
    ROOT / "app" / "src" / "i18n.js",
]


def _public_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_FILES)


def test_given_public_scope_when_scanned_then_old_positioning_claims_are_absent():
    """
    GIVEN public README and Root-PWA copy
    WHEN release positioning is checked
    THEN company/crisis/cloud-absolutist claims are absent from the public scope.
    """
    text = _public_text()
    banned = [
        "Zero Human",
        "Firma",
        "CEO",
        "CTO",
        "Krisen",
        "never sends a single byte",
        "100% offline",
        "weltweit erreichbar",
        "reachable worldwide",
        "Globaler Tunnel",
        "global tunnel",
        "túnel global",
        "tunnel global",
        "グローバルトンネル",
        "全球隧道",
        "2.5 GB",
        "2.5GB",
    ]
    hits = [
        term
        for term in banned
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", text, re.IGNORECASE)
    ]
    assert hits == []


def test_given_readme_feature_matrix_when_network_feature_exists_then_marked_optional_online():
    """
    GIVEN online-capable features remain in the product
    WHEN the README is inspected
    THEN users can distinguish offline core from optional online capabilities.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Offline-first" in readme
    assert "Optional Online" in readme
    assert "Advanced Opt-in" in readme
    assert "Web search" in readme
    assert "Public mobile tunnel" in readme
    assert "OpenAI-compatible API" in readme


def test_given_gemma_copy_when_checked_then_model_size_and_context_are_correct():
    """
    GIVEN Gemma 4 E4B is the default model story
    WHEN public copy is checked
    THEN the Ollama name, artifact size and context length are accurate.
    """
    text = _public_text()
    assert "gemma4:e4b" in text
    assert "9.6 GB" in text
    assert "128K" in text


def test_given_root_pwa_when_dom_checked_then_provider_badge_and_offline_help_exist():
    """
    GIVEN the Root-PWA is the flagship UI
    WHEN its DOM is inspected
    THEN model provider state and offline help are first-class UI elements.
    """
    html = (ROOT / "app" / "src" / "index.html").read_text(encoding="utf-8")
    assert 'id="provider-badge"' in html
    assert 'id="offline-banner"' in html
    assert 'id="chat-area"' in html
    assert 'id="attach-btn"' in html
    assert 'id="mic-btn"' in html
    assert 'id="btn-provider-settings"' in html
    assert 'id="provider-modal"' in html
    assert 'value="openai_compatible"' in html

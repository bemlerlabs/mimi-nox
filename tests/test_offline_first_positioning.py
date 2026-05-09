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

GITHUB_TRUST_FILES = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / "docs" / "MIMINOX_VISION_2026.md",
    ROOT / "docs" / "TASK_LIST_TDD.md",
    ROOT / "v2" / "README.md",
    ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md",
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


def test_given_github_entrypoints_when_scanned_then_growth_copy_stays_factual():
    """
    GIVEN GitHub-facing entry points
    WHEN trust-sensitive copy is checked
    THEN README and contribution surfaces avoid unverifiable or over-broad claims.
    """
    text = "\n".join(path.read_text(encoding="utf-8") for path in GITHUB_TRUST_FILES)
    banned = [
        "doesn't exist anywhere else",
        "Full demo video coming soon",
        "Download desktop MP4",
        "Download mobile QR MP4",
        "see for yourself in 30 seconds",
        "zero cloud",
        "100% Local Inference",
        "All languages",
        "248 passed",
        "32/32 passed",
        "better than",
        "OpenClaw",
        "Open Claw",
    ]
    hits = [
        term
        for term in banned
        if re.search(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", text, re.IGNORECASE)
    ]
    assert hits == []


def test_given_readme_demo_assets_when_checked_then_referenced_media_exists():
    """
    GIVEN the GitHub README is the first product surface
    WHEN it references screenshots or demo media
    THEN those files exist in the repository.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="(docs/[^"#]+\.(?:png|gif))"', readme)
    refs += re.findall(r"\((docs/[^)#]+\.(?:png|gif))\)", readme)
    assert refs
    missing = [ref for ref in refs if not (ROOT / ref).exists()]
    assert missing == []


def test_given_readme_when_phone_pairing_is_described_then_qr_flow_is_prominent_and_honest():
    """
    GIVEN phone pairing is a core differentiator
    WHEN the README is scanned
    THEN the QR flow is visible near the top and remains LAN-first with public access opt-in.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    top = readme[:3000]

    assert "Phone Via QR" in readme
    assert "mimi-nox-mobile-qr-demo.gif" in top
    assert "LAN-first" in readme
    assert "Public access is an optional online mode" in readme
    assert "miminox start --lan" in readme


def test_given_readme_media_when_checked_then_no_video_artifacts_are_promoted():
    """
    GIVEN documentation media is a public trust surface
    WHEN README media references are checked
    THEN unstable generated videos are not promoted until reviewed.
    """
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert ".mp4" not in readme
    assert ".webm" not in readme


def test_given_project_metadata_when_checked_then_repository_urls_match_public_remote():
    """
    GIVEN package metadata is shown on GitHub and package indexes
    WHEN URLs are checked
    THEN they point to the actual public repository.
    """
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "https://github.com/MimiTechAi/mimi-nox" in pyproject
    assert "https://github.com/mimiai/mimi-nox" not in pyproject

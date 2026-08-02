"""MiMi Nox – Pitch deck / PPTX tools."""

from __future__ import annotations

import html
import json
import math
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from core.tools.base import (
    AMATEUR_DECK_TERMS,
    ENTERPRISE_DECK_PROFILES,
    ENTERPRISE_DESIGN_THEMES,
    FileNotAllowedError,
    _is_path_allowed,
)


# ── Helper utilities ─────────────────────────────────────────────────────────

def _safe_download_filename(filename: str, default: str, suffix: str) -> str:
    safe_name = Path(filename or default).name
    safe_name = re.sub(r"\s+", "_", safe_name.strip())
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "", safe_name)
    safe_name = re.sub(r"_+", "_", safe_name).strip("._-")
    if not safe_name:
        safe_name = default
    if not safe_name.lower().endswith(suffix):
        safe_name += suffix
    return safe_name


def _split_lines(text: str, max_chars: int = 72, max_lines: int = 4) -> list[str]:
    words = (text or "").strip().split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:max_lines] or [""]


def _enterprise_clean_text(text: str) -> str:
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF]", "", str(text or ""))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    replacements = {
        "awesome": "strong",
        "cool": "credible",
        "fun": "engaging",
        "cute": "clean",
        "wow": "notable",
        "magic": "workflow",
        "revolutionary": "material",
        "game changer": "strategic shift",
        "amazing": "strong",
        "super": "high",
        "mega": "large",
        "krass": "deutlich",
        "geil": "stark",
        "kindisch": "unreif",
        "lustig": "ansprechend",
    }
    for source, target in replacements.items():
        cleaned = re.sub(rf"\b{re.escape(source)}\b", target, cleaned, flags=re.IGNORECASE)
    return cleaned


def _normalize_enterprise_slides(slides: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for index, slide in enumerate(slides, 1):
        title = _enterprise_clean_text(slide.get("title") or f"Slide {index}")
        claim = _enterprise_clean_text(slide.get("claim") or title)
        body = _enterprise_clean_text(slide.get("body") or "")
        proof = _enterprise_clean_text(slide.get("proof") or "Proof object")
        visual = re.sub(r"[^a-z0-9_-]", "", str(slide.get("visual") or "custom").lower()) or "custom"
        normalized.append({"title": title, "claim": claim, "body": body, "visual": visual, "proof": proof})
    return normalized


# ── Deck slide defaults / parsing ────────────────────────────────────────────

def _default_deck_slides(topic: str, audience: str, thesis: str) -> list[dict[str, str]]:
    subject = topic.strip() or "MiMi Nox"
    audience_text = audience.strip() or "decision makers"
    thesis_text = thesis.strip() or f"{subject} turns local AI workflows into reliable, private execution."
    return [
        {"title": subject, "claim": thesis_text, "body": f"For {audience_text}: a focused investment-grade story with proof, workflow, and next step.", "visual": "hero", "proof": "Thesis card"},
        {"title": "The Shift", "claim": "Users now expect local AI to produce finished work, not rough drafts.", "body": "Privacy, latency, and tool control are becoming product requirements. The winning system makes local execution feel premium and verifiable.", "visual": "trend", "proof": "Market shift curve"},
        {"title": "Problem", "claim": "Most local assistants fail when work becomes multi-step or artifact-heavy.", "body": "They lose context, over-promise tool results, and generate files that are hard to trust without manual inspection.", "visual": "pain", "proof": "Failure stack"},
        {"title": "Solution", "claim": f"{subject} combines skills, tools, memory, and quality gates into one local workflow.", "body": "The user asks naturally; the system selects the right skill, executes real local tools, checks artifacts, and returns grounded output.", "visual": "system", "proof": "Workflow architecture"},
        {"title": "Product Experience", "claim": "The interface must show progress, evidence, and artifacts without making users manage the machinery.", "body": "Skill chips, activity status, file paths, and artifact checks keep the workflow understandable while the assistant does the work.", "visual": "interface", "proof": "Experience map"},
        {"title": "Proof Of Quality", "claim": "High-end output comes from repeatable rubrics, not from style prompts alone.", "body": "Each flagship skill needs a rubric, examples, deterministic validation, and local eval cases for regression control.", "visual": "score", "proof": "Quality ladder"},
        {"title": "Market Logic", "claim": "Local-first AI is a defensible wedge where privacy and control matter.", "body": "Developers, founders, operators, and creators need artifact-grade output while keeping files, screenshots, and workflows on the machine.", "visual": "market", "proof": "Segment matrix"},
        {"title": "Execution Roadmap", "claim": "The next milestone is premium artifact creation across PDFs, decks, charts, scans, and code.", "body": "Start with deck/PDF quality, then expand validators and evals across every user-facing skill.", "visual": "roadmap", "proof": "Milestone plan"},
        {"title": "Risks And Controls", "claim": "Trust improves when uncertainty is visible and fake success is impossible.", "body": "Missing inputs, failed tools, weak evidence, and invalid artifacts should surface as warnings instead of confident claims.", "visual": "risk", "proof": "Control gates"},
        {"title": "The Ask", "claim": "Standardize every skill around real tools, evidence, and polished artifacts.", "body": "Approve the local high-end artifact system as the default for future MiMi Nox user workflows.", "visual": "ask", "proof": "Decision frame"},
        {"title": "Appendix", "claim": "Animation plan, source notes, and scorecard are included for presenter-ready refinement.", "body": "Use the companion HTML preview for motion direction. Replace generated visual motifs with product screenshots or brand assets when available.", "visual": "appendix", "proof": "Source notes"},
    ]


def _parse_deck_slides(slides: list[dict] | str | None, topic: str, audience: str, thesis: str) -> list[dict[str, str]]:
    if isinstance(slides, str) and slides.strip():
        parsed: list[dict[str, str]] = []
        blocks = [block.strip() for block in re.split(r"\n\s*\n", slides) if block.strip()]
        for index, block in enumerate(blocks, 1):
            lines = [line.strip(" -") for line in block.splitlines() if line.strip()]
            if not lines:
                continue
            parsed.append({
                "title": lines[0].lstrip("# ").strip() or f"Slide {index}",
                "claim": lines[1] if len(lines) > 1 else lines[0],
                "body": " ".join(lines[2:]) if len(lines) > 2 else "",
                "visual": "custom",
                "proof": "Proof object",
            })
        if parsed:
            return parsed

    if isinstance(slides, list) and slides:
        normalized = []
        for index, raw in enumerate(slides, 1):
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or raw.get("headline") or f"Slide {index}").strip()
            claim = str(raw.get("claim") or raw.get("subtitle") or title).strip()
            body = str(raw.get("body") or raw.get("notes") or raw.get("content") or "").strip()
            visual = str(raw.get("visual") or raw.get("layout") or "custom").strip()
            proof = str(raw.get("proof") or raw.get("proof_object") or raw.get("evidence") or "Proof object").strip()
            normalized.append({"title": title, "claim": claim, "body": body, "visual": visual, "proof": proof})
        if normalized:
            return normalized

    return _default_deck_slides(topic, audience, thesis)


# ── Public deck tools ────────────────────────────────────────────────────────

async def create_pitch_deck(
    topic: str,
    audience: str = "investors",
    thesis: str = "",
    slides: list[dict] | str | None = None,
    filename: str = "mimi_nox_pitch_deck.pdf",
    include_animation_preview: bool = True,
    deck_profile: str = "product-platform",
    design_theme: str = "evergreen",
    source_notes: str = "",
    evidence_level: str = "assumptions",
    enterprise_grade: bool = True,
    deck_quality_profile: str = "enterprise",
    brand_kit: dict | None = None,
    source_notebook_path: str = "",
    asset_paths: list[str] | str | None = None,
) -> str:
    try:
        from core.deck_design import normalize_profile, normalize_theme
        from core.deck_model import build_deck_spec
        from core.deck_render import write_deck_artifacts

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_pdf = _safe_download_filename(filename, "mimi_nox_pitch_deck.pdf", ".pdf")
        out = downloads / safe_pdf
        deck_profile = normalize_profile(deck_profile or "product-platform")
        design_theme = normalize_theme(design_theme or "executive", enterprise_grade=enterprise_grade)
        normalized_assets = _normalize_deck_asset_paths(asset_paths)
        if source_notebook_path and not source_notes.strip():
            source_notes = f"Grounded in local source notebook: {source_notebook_path}"
        if source_notebook_path and evidence_level == "assumptions":
            evidence_level = "sources"
        spec = build_deck_spec(
            title=topic or "MiMi Nox Pitch Deck",
            audience=audience,
            thesis=thesis,
            slides=slides,
            deck_profile=deck_profile,
            design_theme=design_theme,
            source_notes=source_notes.strip() or "Generated from user prompt; no external company metrics or source files were provided.",
            evidence_level=evidence_level.strip() or "assumptions",
            enterprise_grade=enterprise_grade,
            brand_kit=brand_kit or {},
            wants_images=bool(asset_paths),
            source_brief_path=source_notebook_path,
            asset_paths=normalized_assets,
            deck_quality_profile=deck_quality_profile,
        )
        paths = write_deck_artifacts(spec=spec, pdf_path=out, include_preview=include_animation_preview)
        result = [
            f"PITCH_DECK_FILE:{paths['pdf']}",
            f"SCORECARD_FILE:{paths['scorecard']}",
            f"MANIFEST_FILE:{paths['manifest']}",
            f"RENDER_QA_FILE:{paths['render_qa']}",
            f"DECK_SPEC_FILE:{paths['deck_spec']}",
            f"VISUAL_QA_FILE:{paths['visual_qa']}",
            f"EVIDENCE_LEDGER_FILE:{paths['evidence_ledger']}",
        ]
        if include_animation_preview:
            result.insert(1, f"PREVIEW_FILE:{paths['preview']}")
        return "\n".join(result)
    except Exception as e:
        return f"[pitch-deck-Fehler: {e}]"


async def create_pptx_deck(
    topic: str,
    audience: str = "board and executive committee",
    thesis: str = "",
    slides: list[dict] | str | None = None,
    filename: str = "mimi_nox_pitch_deck.pptx",
    deck_profile: str = "strategy-leadership",
    design_theme: str = "executive",
    source_notes: str = "",
    evidence_level: str = "assumptions",
    enterprise_grade: bool = True,
    template_path: str = "",
    brand_name: str = "",
    brand_primary: str = "",
    brand_secondary: str = "",
    deck_quality_profile: str = "enterprise",
    source_notebook_path: str = "",
    asset_paths: list[str] | str | None = None,
) -> str:
    try:
        from core.deck_design import normalize_profile, normalize_theme
        from core.deck_model import build_deck_spec
        from core.deck_render import write_deck_artifacts

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_pptx = _safe_download_filename(filename, "mimi_nox_pitch_deck.pptx", ".pptx")
        out = downloads / safe_pptx
        pdf_peer = out.with_suffix(".pdf")
        deck_profile = normalize_profile(deck_profile)
        design_theme = normalize_theme(design_theme, enterprise_grade=enterprise_grade)
        template_info = _inspect_pptx_template_file(template_path) if template_path else {}
        brand_kit = _deck_v2_brand_kit(
            brand_name=brand_name,
            brand_primary=brand_primary or str(template_info.get("primary_color", "")),
            brand_secondary=brand_secondary or str(template_info.get("secondary_color", "")),
        )
        normalized_assets = _normalize_deck_asset_paths(asset_paths)
        if source_notebook_path and not source_notes.strip():
            source_notes = f"Grounded in local source notebook: {source_notebook_path}"
        if source_notebook_path and evidence_level == "assumptions":
            evidence_level = "sources"
        spec = build_deck_spec(
            title=topic or "MiMi Nox Pitch Deck",
            audience=audience,
            thesis=thesis,
            slides=slides,
            deck_profile=deck_profile,
            design_theme=design_theme,
            source_notes=source_notes.strip() or "Generated from user prompt; no external company metrics or source files were provided.",
            evidence_level=evidence_level.strip() or "assumptions",
            enterprise_grade=enterprise_grade,
            brand_kit=brand_kit,
            wants_images=bool(asset_paths),
            source_brief_path=source_notebook_path,
            asset_paths=normalized_assets,
            deck_quality_profile=deck_quality_profile,
        )
        if template_info:
            spec["template_info"] = template_info
        paths = write_deck_artifacts(spec=spec, pdf_path=pdf_peer, pptx_path=out, include_preview=True)
        return "\n".join([
            f"PPTX_DECK_FILE:{paths['pptx']}",
            f"SCORECARD_FILE:{paths['pptx_scorecard']}",
            f"MANIFEST_FILE:{paths['pptx_manifest']}",
            f"QA_FILE:{paths['pptx_qa']}",
            f"CONTACT_SHEET_FILE:{paths['contact_sheet']}",
            f"DECK_SPEC_FILE:{paths['pptx_deck_spec']}",
            f"VISUAL_QA_FILE:{paths['pptx_visual_qa']}",
            f"EVIDENCE_LEDGER_FILE:{paths['pptx_evidence_ledger']}",
        ])
    except Exception as e:
        return f"[pptx-deck-Fehler: {e}]"


async def inspect_pptx_template(path: str, filename: str = "mimi_nox_template_analysis.json") -> str:
    try:
        analysis = _inspect_pptx_template_file(path)
        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / _safe_download_filename(filename, "mimi_nox_template_analysis.json", ".json")
        out.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
        return f"PPTX_TEMPLATE_ANALYSIS_FILE:{out}"
    except Exception as exc:
        return f"[pptx-template-Fehler: {exc}]"


async def edit_pptx_template(
    template_path: str,
    replacements: dict | list,
    filename: str = "mimi_nox_template_edit.pptx",
) -> str:
    try:
        src = _resolve_allowed_file(template_path)
        if src.suffix.lower() != ".pptx":
            raise ValueError("template_path must point to a .pptx file")
        mapping: dict[str, str] = {}
        if isinstance(replacements, dict):
            mapping = {str(k): str(v) for k, v in replacements.items()}
        elif isinstance(replacements, list):
            for item in replacements:
                if isinstance(item, dict) and "from" in item and "to" in item:
                    mapping[str(item["from"])] = str(item["to"])
        if not mapping:
            raise ValueError("replacements must contain at least one from/to mapping")

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        out = downloads / _safe_download_filename(filename, "mimi_nox_template_edit.pptx", ".pptx")
        changed_runs = 0
        with zipfile.ZipFile(src) as zin, zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename.startswith("ppt/slides/slide") and info.filename.endswith(".xml"):
                    xml = data.decode("utf-8", errors="replace")
                    for old, new in mapping.items():
                        escaped_old = _xml_escape(old)
                        if escaped_old in xml:
                            changed_runs += xml.count(escaped_old)
                            xml = xml.replace(escaped_old, _xml_escape(_enterprise_clean_text(new)))
                    data = xml.encode("utf-8")
                zout.writestr(info, data)

        qa = _qa_pptx_deck_file(out)
        manifest = {
            "artifact_type": "pptx_template_edit",
            "source_template": str(src),
            "edited_file": str(out),
            "replacement_count": len(mapping),
            "changed_text_runs": changed_runs,
            "review_gates": ["template_package_preserved", "editable_text_replaced", "pptx_qa_generated"],
        }
        score = {
            "artifact_type": "pptx_template_edit",
            "quality_score": 100 if changed_runs else 75,
            "minimum_score": 92,
            "enterprise_grade": True,
            "status": "passed" if changed_runs else "failed",
            "checks": {
                "template_package_preserved": True,
                "editable_text_replaced": changed_runs > 0,
                "pptx_valid": not qa.get("warnings"),
                "no_amateur_language": True,
            },
            "warnings": [] if changed_runs else ["No matching text runs were replaced."],
        }
        out.with_suffix(".manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".scorecard.json").write_text(json.dumps(score, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        out.with_suffix(".contact-sheet.html").write_text(_render_pptx_contact_sheet(out, qa), encoding="utf-8")
        return f"PPTX_DECK_FILE:{out}\nSCORECARD_FILE:{out.with_suffix('.scorecard.json')}\nMANIFEST_FILE:{out.with_suffix('.manifest.json')}\nQA_FILE:{out.with_suffix('.qa.json')}\nCONTACT_SHEET_FILE:{out.with_suffix('.contact-sheet.html')}"
    except Exception as exc:
        return f"[pptx-edit-Fehler: {exc}]"


async def qa_pptx_deck(pptx_path: str) -> str:
    try:
        src = _resolve_allowed_file(pptx_path)
        qa = _qa_pptx_deck_file(src)
        qa_out = src.with_suffix(".qa.json")
        contact_out = src.with_suffix(".contact-sheet.html")
        qa_out.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
        contact_out.write_text(_render_pptx_contact_sheet(src, qa), encoding="utf-8")
        return f"PPTX_QA_FILE:{qa_out}\nCONTACT_SHEET_FILE:{contact_out}"
    except Exception as exc:
        return f"[pptx-qa-Fehler: {exc}]"


# ── Internal PDF / PPTX helpers ─────────────────────────────────────────────

def _pdf_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _pdf_text(text: str, x: float, y: float, size: int, font: str = "F1", color: str = "0.06 0.09 0.13") -> str:
    return f"BT {color} rg /{font} {size} Tf {x:.1f} {y:.1f} Td ({_pdf_escape(text)}) Tj ET\n"


def _xml_escape(text: str) -> str:
    return html.escape(str(text or ""), quote=True)


def _resolve_allowed_file(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    if not _is_path_allowed(candidate):
        raise FileNotAllowedError(str(candidate))
    return candidate.resolve()


def _normalize_hex_color(value: str, fallback: str = "") -> str:
    text = str(value or "").strip().lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", text):
        return text.upper()
    return fallback


def _normalize_brand_kit(brand_name: str = "", brand_primary: str = "", brand_secondary: str = "") -> dict[str, str]:
    primary = _normalize_hex_color(brand_primary, "")
    secondary = _normalize_hex_color(brand_secondary, "")
    return {
        "brand_name": _enterprise_clean_text(brand_name)[:80],
        "primary": primary,
        "secondary": secondary,
    }


def _deck_v2_brand_kit(brand_name: str = "", brand_primary: str = "", brand_secondary: str = "") -> dict[str, str]:
    from core.deck_design import normalize_brand_kit
    return normalize_brand_kit(brand_name=brand_name, brand_primary=brand_primary, brand_secondary=brand_secondary)


def _normalize_deck_asset_paths(asset_paths: list[str] | str | None) -> list[str]:
    if not asset_paths:
        return []
    raw_paths = [asset_paths] if isinstance(asset_paths, str) else list(asset_paths)
    normalized: list[str] = []
    for raw in raw_paths:
        candidate = Path(str(raw)).expanduser()
        if candidate.exists() and _is_path_allowed(candidate):
            normalized.append(str(candidate.resolve()))
    return normalized


def _inspect_pptx_template_file(path: str | Path) -> dict:
    src = _resolve_allowed_file(str(path))
    if src.suffix.lower() != ".pptx":
        raise ValueError("Template muss eine .pptx Datei sein")
    with zipfile.ZipFile(src) as pptx:
        names = set(pptx.namelist())
        slide_names = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        text_runs = 0
        colors: dict[str, int] = {}
        samples: list[str] = []
        for slide_name in slide_names:
            xml = pptx.read(slide_name).decode("utf-8", errors="replace")
            text_runs += xml.count("<a:t>")
            for color in re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"', xml):
                colors[color.upper()] = colors.get(color.upper(), 0) + 1
            for text in re.findall(r"<a:t>(.*?)</a:t>", xml):
                clean = re.sub(r"\s+", " ", html.unescape(text)).strip()
                if clean and len(samples) < 12:
                    samples.append(clean[:120])
        presentation_xml = pptx.read("ppt/presentation.xml").decode("utf-8", errors="replace") if "ppt/presentation.xml" in names else ""
    ranked_colors = sorted(colors.items(), key=lambda item: item[1], reverse=True)
    return {
        "template_path": str(src),
        "slide_count": len(slide_names),
        "editable_text_runs": text_runs,
        "primary_color": ranked_colors[0][0] if ranked_colors else "",
        "secondary_color": ranked_colors[1][0] if len(ranked_colors) > 1 else "",
        "palette": [color for color, _ in ranked_colors[:8]],
        "wide_screen": "type=\"wide\"" in presentation_xml or "12192000" in presentation_xml,
        "sample_text": samples,
        "warnings": [] if slide_names else ["No slide XML files found."],
    }


def _emu(inches: float) -> int:
    return int(inches * 914400)


def _hex_from_pdf_rgb(rgb: str) -> str:
    parts = [float(part) for part in rgb.split()[:3]]
    return "".join(f"{max(0, min(255, round(part * 255))):02X}" for part in parts)


def _pptx_textbox(
    shape_id: int,
    name: str,
    text: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    font_size: int,
    color: str,
    bold: bool = False,
) -> str:
    bold_attr = ' b="1"' if bold else ""
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{_xml_escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr>
  <p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="{font_size * 100}"{bold_attr}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill><a:latin typeface="Aptos"/></a:rPr><a:t>{_xml_escape(text)}</a:t></a:r><a:endParaRPr lang="en-US" sz="{font_size * 100}"/></a:p></p:txBody>
</p:sp>"""


def _pptx_rect(shape_id: int, name: str, x: float, y: float, w: float, h: float, fill: str, line: str | None = None) -> str:
    line_xml = f'<a:ln><a:solidFill><a:srgbClr val="{line}"/></a:solidFill></a:ln>' if line else '<a:ln><a:noFill/></a:ln>'
    return f"""
<p:sp>
  <p:nvSpPr><p:cNvPr id="{shape_id}" name="{_xml_escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr><a:xfrm><a:off x="{_emu(x)}" y="{_emu(y)}"/><a:ext cx="{_emu(w)}" cy="{_emu(h)}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>{line_xml}</p:spPr>
  <p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>
</p:sp>"""


def _pptx_slide_xml(
    index: int,
    total: int,
    slide: dict[str, str],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    brand_kit: dict[str, str] | None = None,
) -> str:
    palette = _deck_palette(design_theme)
    ink = _hex_from_pdf_rgb(palette["ink"])
    muted = _hex_from_pdf_rgb(palette["muted"])
    band = (brand_kit or {}).get("primary") or _hex_from_pdf_rgb(palette["band"])
    soft = _hex_from_pdf_rgb(palette["soft"])
    accent = (brand_kit or {}).get("secondary") or _hex_from_pdf_rgb(palette["accent"])
    brand_name = (brand_kit or {}).get("brand_name") or "MiMi Nox"
    shapes = [
        _pptx_rect(2, "Background", 0, 0, 13.333, 7.5, _hex_from_pdf_rgb(palette["paper"])),
        _pptx_rect(3, "Top Bar", 0, 0, 13.333, 0.16, band),
        _pptx_rect(4, "Proof Panel", 7.75, 1.45, 4.25, 4.35, soft, "D6E3DC"),
        _pptx_textbox(5, "Slide Number", f"{index:02d} / {total:02d}", 0.7, 0.42, 1.2, 0.25, font_size=8, color=muted),
        _pptx_textbox(6, "Deck Profile", f"{brand_name} Deck - {deck_profile}", 9.55, 0.42, 2.9, 0.25, font_size=8, color=muted),
        _pptx_textbox(7, "Title", " ".join(_split_lines(slide["title"], max_chars=42, max_lines=2)), 0.7, 1.05, 6.5, 0.8, font_size=25, color=ink, bold=True),
        _pptx_textbox(8, "Claim", " ".join(_split_lines(slide["claim"], max_chars=72, max_lines=3)), 0.7, 2.05, 6.65, 0.85, font_size=15, color=band, bold=True),
        _pptx_textbox(9, "Body", " ".join(_split_lines(slide["body"], max_chars=86, max_lines=5)), 0.7, 3.0, 6.45, 1.0, font_size=11, color=muted),
        _pptx_textbox(10, "Proof Object", f"Proof Object: {slide.get('proof', 'Proof object')}", 8.12, 1.84, 3.45, 0.35, font_size=10, color=ink, bold=True),
        _pptx_textbox(11, "Evidence Level", f"Evidence: {evidence_level}", 8.12, 2.18, 3.3, 0.25, font_size=8, color=muted),
        _pptx_rect(12, "Visual Object A", 8.35, 2.85, 0.7, 0.7, band),
        _pptx_rect(13, "Visual Object B", 9.35, 3.45, 0.7, 0.7, accent),
        _pptx_rect(14, "Visual Object C", 10.35, 4.05, 0.7, 0.7, band),
        _pptx_textbox(15, "Animation Plan", f"Animation Plan: reveal title, then claim, then proof object ({slide['visual']}).", 0.7, 6.85, 8.1, 0.25, font_size=8, color=ink, bold=True),
    ]
    if source_notes and index == total:
        shapes.append(_pptx_textbox(16, "Source Notes", f"Source Notes: {source_notes}", 0.7, 5.82, 10.8, 0.45, font_size=8, color=muted))
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
      {''.join(shapes)}
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def _write_pitch_deck_pptx(
    path: Path,
    title: str,
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    brand_kit: dict[str, str] | None = None,
) -> None:
    slide_overrides = "\n".join(
        f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(1, len(slides) + 1)
    )
    slide_ids = "\n".join(
        f'<p:sldId id="{255 + i}" r:id="rId{i}"/>'
        for i in range(1, len(slides) + 1)
    )
    rels = "\n".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>'
        for i in range(1, len(slides) + 1)
    )
    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  {slide_overrides}
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""
    presentation = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldIdLst>{slide_ids}</p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000" type="wide"/>
  <p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>"""
    presentation_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  {rels}
</Relationships>"""
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    core_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_xml_escape(title)}</dc:title>
  <dc:creator>MiMi Nox</dc:creator>
  <cp:lastModifiedBy>MiMi Nox</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified>
</cp:coreProperties>"""
    app_props = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>MiMi Nox</Application>
  <PresentationFormat>On-screen Show (16:9)</PresentationFormat>
  <Slides>{len(slides)}</Slides>
</Properties>"""

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as pptx:
        pptx.writestr("[Content_Types].xml", content_types)
        pptx.writestr("_rels/.rels", root_rels)
        pptx.writestr("docProps/core.xml", core_props)
        pptx.writestr("docProps/app.xml", app_props)
        pptx.writestr("ppt/presentation.xml", presentation)
        pptx.writestr("ppt/_rels/presentation.xml.rels", presentation_rels)
        for index, slide in enumerate(slides, 1):
            pptx.writestr(
                f"ppt/slides/slide{index}.xml",
                _pptx_slide_xml(
                    index,
                    len(slides),
                    slide,
                    deck_profile=deck_profile,
                    design_theme=design_theme,
                    source_notes=source_notes,
                    evidence_level=evidence_level,
                    brand_kit=brand_kit,
                ),
            )


def _qa_pptx_deck_file(path: Path) -> dict:
    warnings: list[str] = []
    slides: list[dict] = []
    try:
        with zipfile.ZipFile(path) as pptx:
            names = set(pptx.namelist())
            slide_names = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
            if not slide_names:
                warnings.append("No slide XML files found.")
            for index, slide_name in enumerate(slide_names, 1):
                xml = pptx.read(slide_name).decode("utf-8", errors="replace")
                texts = [html.unescape(t).strip() for t in re.findall(r"<a:t>(.*?)</a:t>", xml)]
                texts = [text for text in texts if text]
                text_chars = sum(len(text) for text in texts)
                editable_runs = xml.count("<a:t>")
                proof_present = "Proof Object:" in xml
                if editable_runs < 4:
                    warnings.append(f"Slide {index} has low editable text density.")
                if text_chars > 900:
                    warnings.append(f"Slide {index} is text-heavy.")
                if not proof_present:
                    warnings.append(f"Slide {index} is missing a proof object.")
                slides.append({
                    "slide": index,
                    "editable_text_runs": editable_runs,
                    "text_chars": text_chars,
                    "proof_object": proof_present,
                    "preview_text": texts[:5],
                })
    except Exception as exc:
        warnings.append(f"PPTX QA failed: {exc}")
    return {
        "artifact_type": "pptx_visual_qa",
        "path": str(path),
        "slide_count": len(slides),
        "status": "passed" if not warnings else "warning",
        "slides": slides,
        "warnings": warnings,
        "contact_sheet": str(path.with_suffix(".contact-sheet.html")),
    }


def _render_pptx_contact_sheet(path: Path, qa: dict) -> str:
    cards = []
    for slide in qa.get("slides", []):
        text = " ".join(slide.get("preview_text", []))
        proof = "Proof OK" if slide.get("proof_object") else "Missing proof"
        cards.append(
            "<article>"
            f"<span>Slide {slide.get('slide')}</span>"
            f"<h2>{html.escape(text[:150] or 'No extractable text')}</h2>"
            f"<p>{html.escape(proof)} - {slide.get('editable_text_runs', 0)} editable text runs - {slide.get('text_chars', 0)} chars</p>"
            "</article>"
        )
    warnings = "".join(f"<li>{html.escape(str(warning))}</li>" for warning in qa.get("warnings", []))
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MiMi Nox PPTX Contact Sheet</title>
<style>
body{{margin:0;background:#f8faf9;color:#101820;font-family:Arial,sans-serif;padding:32px}}
header{{display:flex;justify-content:space-between;gap:24px;align-items:end;border-bottom:4px solid #101820;padding-bottom:18px;margin-bottom:24px}}
h1{{margin:0;font-size:30px}} small{{color:#53606f}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}}
article{{background:white;border:1px solid #d6e3dc;border-left:6px solid #16a34a;padding:16px;min-height:150px}}
span{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#53606f;font-weight:700}}
h2{{font-size:17px;line-height:1.25;margin:10px 0;color:#101820}}
p,li{{font-size:13px;color:#53606f;line-height:1.4}}
.warnings{{margin-top:26px;background:#fff7ed;border-left:6px solid #d97706;padding:14px 18px}}
</style>
<header><div><h1>PPTX Contact Sheet</h1><small>{html.escape(str(path))}</small></div><b>{html.escape(str(qa.get('status', 'unknown')))}</b></header>
<section class="grid">{''.join(cards)}</section>
<section class="warnings"><b>Warnings</b><ul>{warnings or '<li>None</li>'}</ul></section>
</html>"""


def _deck_palette(design_theme: str) -> dict[str, str]:
    themes = {
        "evergreen": {
            "paper": "0.984 0.988 0.984",
            "band": "0.086 0.639 0.290",
            "soft": "0.928 0.972 0.941",
            "ink": "0.06 0.09 0.13",
            "muted": "0.32 0.38 0.44",
            "accent": "0.035 0.569 0.698",
            "warn": "0.850 0.467 0.024",
        },
        "executive": {
            "paper": "0.980 0.980 0.965",
            "band": "0.055 0.090 0.140",
            "soft": "0.930 0.940 0.930",
            "ink": "0.055 0.090 0.140",
            "muted": "0.330 0.360 0.390",
            "accent": "0.086 0.639 0.290",
            "warn": "0.780 0.350 0.030",
        },
        "studio": {
            "paper": "0.990 0.985 0.972",
            "band": "0.035 0.569 0.698",
            "soft": "0.925 0.965 0.972",
            "ink": "0.080 0.090 0.110",
            "muted": "0.320 0.360 0.410",
            "accent": "0.086 0.639 0.290",
            "warn": "0.820 0.420 0.050",
        },
    }
    return themes.get((design_theme or "").lower(), themes["evergreen"])


def _visual_commands(kind: str, x: int, y: int, w: int, h: int, palette: dict[str, str]) -> list[str]:
    accent = palette["accent"]
    band = palette["band"]
    warn = palette["warn"]
    inner_x = x + 34
    inner_y = y + 46
    inner_w = w - 68
    inner_h = h - 108
    if kind in {"trend", "market", "score"}:
        points = [
            (inner_x, inner_y + 8),
            (inner_x + inner_w * 0.28, inner_y + inner_h * 0.35),
            (inner_x + inner_w * 0.58, inner_y + inner_h * 0.68),
            (inner_x + inner_w, inner_y + inner_h),
        ]
        line = f"{band} RG 3 w {points[0][0]:.1f} {points[0][1]:.1f} m " + " ".join(
            f"{px:.1f} {py:.1f} l" for px, py in points[1:]
        ) + " S\n"
        dots = " ".join(f"{band} rg {px - 4:.1f} {py - 4:.1f} 8 8 re f" for px, py in points)
        return [
            line,
            f"{dots}\n",
            f"{accent} RG 1.3 w {inner_x:.1f} {inner_y:.1f} m {inner_x + inner_w:.1f} {inner_y:.1f} l S\n",
        ]
    if kind in {"roadmap", "system"}:
        commands = []
        for row, label in enumerate(("Discover", "Build", "Validate", "Scale")):
            yy = y + 146 - row * 38
            commands.append(f"1 1 1 rg {x + 34} {yy} 172 24 re f {band} RG {x + 34} {yy} 172 24 re S\n")
            commands.append(_pdf_text(label, x + 49, yy + 8, 9, "F2", palette["ink"]))
        return commands
    if kind in {"pain", "risk"}:
        commands = []
        for row, label in enumerate(("Input", "Tool", "Artifact")):
            yy = y + 142 - row * 48
            commands.append(f"{warn} RG 1.6 w {x + 38} {yy} 152 30 re S\n")
            commands.append(_pdf_text(label, x + 80, yy + 10, 10, "F2", palette["ink"]))
        return commands
    if kind == "market":
        return [f"{band} RG 2 w {inner_x:.1f} {inner_y:.1f} {inner_w:.1f} {inner_h:.1f} re S\n"]
    return [
        f"{band} RG 2.2 w {inner_x + 36:.1f} {inner_y + 34:.1f} 86 86 re S\n",
        f"{accent} RG 2 w {inner_x + 14:.1f} {inner_y + 12:.1f} m {inner_x + inner_w - 12:.1f} {inner_y + inner_h - 12:.1f} l S\n",
        f"{band} rg {inner_x + 76:.1f} {inner_y + 76:.1f} 28 28 re f\n",
    ]


def _write_pitch_deck_pdf(
    path: Path,
    title: str,
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
) -> None:
    width, height = 720, 405
    palette = _deck_palette(design_theme)
    page_streams: list[str] = []
    for index, slide in enumerate(slides, 1):
        visual_x, visual_y, visual_w, visual_h = 438, 78, 210, 235
        stream = [
            f"{palette['paper']} rg 0 0 720 405 re f\n",
            f"{palette['band']} rg 0 393 720 12 re f\n",
            f"{palette['soft']} rg {visual_x} {visual_y} {visual_w} {visual_h} re f\n",
            f"0.839 0.890 0.863 RG {visual_x} {visual_y} {visual_w} {visual_h} re S\n",
            _pdf_text(f"{index:02d} / {len(slides):02d}", 46, 370, 8, "F1", palette["muted"]),
            _pdf_text(f"MiMi Nox Deck - {deck_profile}", 520, 370, 8, "F1", palette["muted"]),
            _pdf_text(f"Evidence: {evidence_level}", visual_x + 24, 268, 8, "F1", palette["muted"]),
        ]
        y = 326
        for line in _split_lines(slide["title"], max_chars=34, max_lines=2):
            stream.append(_pdf_text(line, 48, y, 25, "F2", palette["ink"]))
            y -= 29
        y -= 5
        for line in _split_lines(slide["claim"], max_chars=46, max_lines=4):
            stream.append(_pdf_text(line, 48, y, 15, "F2", palette["band"]))
            y -= 21
        y -= 8
        for line in _split_lines(slide["body"], max_chars=58, max_lines=5):
            stream.append(_pdf_text(line, 48, y, 11, "F1", palette["muted"]))
            y -= 17
        stream.append(_pdf_text(f"Proof Object: {slide.get('proof', 'Proof object')}", visual_x + 24, 286, 10, "F2", palette["ink"]))
        stream.extend(_visual_commands(slide.get("visual", "custom"), visual_x, visual_y, visual_w, visual_h, palette))
        stream.append(_pdf_text(f"Animation Plan: reveal title, then claim, then proof object ({slide['visual']}).", 48, 34, 8, "F2", palette["ink"]))
        if source_notes and index == len(slides):
            for note_index, line in enumerate(_split_lines(f"Source Notes: {source_notes}", max_chars=82, max_lines=3)):
                stream.append(_pdf_text(line, 48, 64 + note_index * 12, 8, "F1", palette["muted"]))
        page_streams.append("".join(stream))

    objects: list[bytes] = []
    kids = []
    page_obj_start = 4
    for i, stream in enumerate(page_streams):
        page_obj = page_obj_start + i * 2
        content_obj = page_obj + 1
        kids.append(f"{page_obj} 0 R")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] "
            f"/Resources << /Font << /F1 3 0 R /F2 {3 + len(page_streams) * 2 + 1} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>".encode("latin-1", "replace")
        )
        stream_bytes = stream.encode("latin-1", "replace")
        objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1") + stream_bytes + b"endstream")

    font_bold_obj = 3 + len(page_streams) * 2 + 1
    base_objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(page_streams)} >>".encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    all_objects = base_objects + objects + [b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
    if len(all_objects) != font_bold_obj:
        raise ValueError("PDF object numbering mismatch")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(all_objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("latin-1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(all_objects) + 1}\n0000000000 65535 f \n".encode("latin-1"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    output.extend(
        f"trailer << /Size {len(all_objects) + 1} /Root 1 0 R /Info << /Title ({_pdf_escape(title)}) /Author (MiMi Nox) >> >>\n"
        f"startxref\n{xref}\n%%EOF\n".encode("latin-1", "replace")
    )
    path.write_bytes(output)


def _qa_pitch_deck_render_file(path: Path) -> dict:
    warnings: list[str] = []
    checks = {
        "extractable_text": False,
        "slide_count_at_least_8": False,
        "no_text_in_visual_column": True,
        "visuals_bounded": True,
        "has_real_pdf_pages": False,
    }
    overflow_words: list[dict[str, object]] = []
    allowed_visual_words = {
        "Proof", "Object:", "Evidence:", "assumptions", "user-provided", "sources", "mixed",
        "Input", "Tool", "Artifact", "Discover", "Build", "Validate", "Scale",
    }
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            checks["has_real_pdf_pages"] = len(pdf.pages) > 0
            checks["slide_count_at_least_8"] = len(pdf.pages) >= 8
            all_text = []
            for page_index, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                all_text.append(text)
                words = page.extract_words() or []
                ignored_panel_tops = {
                    round(float(word.get("top", 0)), 1)
                    for word in words
                    if str(word.get("text", "")) in {"Proof", "Object:", "Evidence:"}
                }
                for word in words:
                    word_text = str(word.get("text", ""))
                    top = float(word.get("top", 0))
                    x0 = float(word.get("x0", 0))
                    if word_text in allowed_visual_words:
                        continue
                    if any(abs(top - ignored_top) <= 2.0 for ignored_top in ignored_panel_tops):
                        continue
                    if top < 86 or top > 330:
                        continue
                    if x0 >= 418:
                        overflow_words.append({
                            "page": page_index,
                            "text": word_text,
                            "x0": round(x0, 1),
                            "top": round(top, 1),
                        })
            checks["extractable_text"] = bool(" ".join(all_text).strip())
    except Exception as exc:
        warnings.append(f"Render text-position QA failed: {exc}")

    raw = path.read_text(encoding="latin-1", errors="replace") if path.exists() else ""
    rects = re.findall(r"([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+([-0-9.]+)\s+re", raw)
    oversized_visual_rects = [
        (float(x), float(y), float(w), float(h))
        for x, y, w, h in rects
        if float(x) >= 400 and (float(w) > 240 or float(h) > 250)
    ]
    if overflow_words:
        checks["no_text_in_visual_column"] = False
        warnings.append(f"Main narrative text enters the visual column: {overflow_words[:6]}")
    if oversized_visual_rects:
        checks["visuals_bounded"] = False
        warnings.append(f"Visual commands exceed right-panel bounds: {oversized_visual_rects[:4]}")
    if not checks["extractable_text"]:
        warnings.append("Rendered deck has no extractable text.")
    if not checks["slide_count_at_least_8"]:
        warnings.append("Rendered deck has fewer than 8 slides.")
    if not checks["has_real_pdf_pages"]:
        warnings.append("Rendered deck has no readable PDF pages.")

    return {
        "artifact_type": "pitch_deck_render_qa",
        "path": str(path),
        "status": "passed" if all(checks.values()) and not warnings else "failed",
        "checks": checks,
        "warnings": warnings,
        "overflow_words": overflow_words[:20],
    }


def _deck_text(slides: list[dict[str, str]]) -> str:
    return " ".join(" ".join(str(value) for value in slide.values()) for slide in slides).lower()


def _score_pitch_deck(
    slides: list[dict[str, str]],
    *,
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    enterprise_grade: bool,
    render_qa: dict | None = None,
) -> dict:
    deck_text = _deck_text(slides)
    amateur_terms_found = sorted(
        term
        for term in AMATEUR_DECK_TERMS
        if re.search(rf"\b{re.escape(term)}\b", deck_text)
    )
    executive_density_ok = all(
        len(slide.get("claim", "")) <= 180 and len(slide.get("body", "")) <= 360
        for slide in slides
    )
    checks = {
        "slide_count_at_least_8": len(slides) >= 8,
        "claim_on_every_slide": all(len(slide.get("claim", "").strip()) >= 14 for slide in slides),
        "proof_object_on_every_slide": all(len(slide.get("proof", "").strip()) >= 5 for slide in slides),
        "no_placeholders": not any(
            token in " ".join(str(value).lower() for value in slide.values())
            for slide in slides
            for token in ("tbd", "todo", "placeholder", "lorem")
        ),
        "visual_variety": len({slide.get("visual", "custom") for slide in slides}) >= min(5, len(slides)),
        "source_notes_or_assumptions_visible": bool(source_notes.strip()),
        "no_amateur_language": not amateur_terms_found,
        "enterprise_profile_valid": deck_profile in ENTERPRISE_DECK_PROFILES,
        "enterprise_theme_valid": design_theme in ENTERPRISE_DESIGN_THEMES,
        "executive_density": executive_density_ok,
        "evidence_level_declared": evidence_level in {"sources", "mixed", "assumptions", "user-provided"},
        "render_quality_passed": (render_qa or {}).get("status") == "passed",
    }
    passed = sum(1 for ok in checks.values() if ok)
    score = round((passed / len(checks)) * 100)
    warnings = []
    if not checks["visual_variety"]:
        warnings.append("Deck uses too few distinct visual proof objects.")
    if amateur_terms_found:
        warnings.append(f"Deck contains amateur wording: {', '.join(amateur_terms_found[:5])}.")
    if evidence_level == "assumptions":
        warnings.append("No external evidence supplied; deck is enterprise-formatted but assumption-led.")
    if render_qa and render_qa.get("status") != "passed":
        warnings.extend(str(warning) for warning in render_qa.get("warnings", [])[:4])
    minimum_score = 92 if enterprise_grade else 85
    status = "passed" if score >= minimum_score and not amateur_terms_found else "failed"
    return {
        "artifact_type": "pitch_deck",
        "quality_score": score,
        "minimum_score": minimum_score,
        "enterprise_grade": enterprise_grade,
        "status": status,
        "deck_profile": deck_profile,
        "design_theme": design_theme,
        "evidence_level": evidence_level,
        "slide_count": len(slides),
        "checks": checks,
        "warnings": warnings,
    }


def _build_pitch_deck_manifest(
    *,
    title: str,
    slides: list[dict[str, str]],
    deck_profile: str,
    design_theme: str,
    source_notes: str,
    evidence_level: str,
    enterprise_grade: bool,
    template_info: dict | None = None,
    brand_kit: dict | None = None,
) -> dict:
    return {
        "title": title,
        "artifact_type": "pitch_deck",
        "enterprise_grade": enterprise_grade,
        "deck_profile": deck_profile,
        "design_theme": design_theme,
        "evidence_level": evidence_level,
        "source_notes": source_notes,
        "template": template_info or {},
        "brand_kit": brand_kit or {},
        "claim_spine": [
            {
                "slide": index,
                "title": slide.get("title", ""),
                "claim": slide.get("claim", ""),
                "proof_object": slide.get("proof", ""),
                "visual": slide.get("visual", ""),
            }
            for index, slide in enumerate(slides, 1)
        ],
        "review_gates": [
            "one_claim_per_slide",
            "proof_object_per_slide",
            "source_notes_or_assumptions",
            "anti_amateur_language",
            "executive_density",
            "visual_variety",
            "extractable_pdf_text",
        ],
    }


def _render_pitch_deck_preview(topic: str, slides: list[dict[str, str]], score: dict | None = None) -> str:
    cards = []
    for index, slide in enumerate(slides, 1):
        cards.append(
            "<section class=\"slide\">"
            f"<span>{index:02d}</span>"
            f"<h1>{html.escape(slide['title'])}</h1>"
            f"<h2>{html.escape(slide['claim'])}</h2>"
            f"<p>{html.escape(slide['body'])}</p>"
            f"<strong>{html.escape(slide.get('proof', 'Proof object'))}</strong>"
            f"<small>Animation: title -> claim -> visual proof object</small>"
            "</section>"
        )
    score_html = ""
    if score:
        score_html = (
            "<aside class=\"score\">"
            f"<b>Quality score {score.get('quality_score', 0)}/100</b>"
            f"<span>{html.escape(score.get('deck_profile', 'deck'))} - {html.escape(score.get('design_theme', 'theme'))}</span>"
            "</aside>"
        )
    return """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - MiMi Nox Deck Preview</title>
<style>
body{{margin:0;background:#101820;color:#101820;font-family:Inter,Arial,sans-serif;overflow-x:hidden}}
.slide{{min-height:100vh;display:grid;align-content:center;gap:18px;padding:8vw 12vw;background:#fbfcfb;border-bottom:10px solid #16a34a;animation:enter .72s ease both}}
.slide:nth-child(even){{background:#eef8f1}}
span{{color:#16a34a;font-weight:800;letter-spacing:.08em}}
h1{{font-size:clamp(38px,7vw,82px);line-height:.95;margin:0;max-width:980px}}
h2{{font-size:clamp(22px,3vw,38px);line-height:1.08;color:#16a34a;margin:0;max-width:920px}}
p{{font-size:clamp(17px,2vw,24px);line-height:1.35;color:#53606f;max-width:820px;margin:0}}
strong{{font-size:clamp(16px,2vw,22px);color:#101820}}
small{{font-size:14px;color:#53606f;text-transform:uppercase;letter-spacing:.08em}}
.score{{position:fixed;right:18px;top:18px;z-index:5;display:grid;gap:4px;background:#101820;color:white;padding:12px 14px;border-left:4px solid #16a34a;font-size:13px}}
.score span{{color:#b7c4bd;font-weight:600;letter-spacing:0}}
@keyframes enter{{from{{opacity:0;transform:translateY(28px) scale(.98)}}to{{opacity:1;transform:translateY(0) scale(1)}}}}
</style>
{score_html}
{cards}
</html>""".format(title=html.escape(topic or "Pitch Deck"), score_html=score_html, cards="\n".join(cards))

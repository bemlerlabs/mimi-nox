"""Deterministic skill fast paths that bypass LLM tool detection."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

from core.tools import (
    analyze_project,
    create_pdf,
    create_pitch_deck,
    create_pptx_deck,
    create_source_notebook,
    discover_projects,
    export_source_brief,
    list_directory,
    query_source_notebook,
    read_file,
)


async def run_skill_fast_path(skill_name: str, user_content: str) -> str | None:
    """Return a direct answer for deterministic skills, or None to use the model path."""
    text = (user_content or "").strip()
    if skill_name == "project-assistant":
        return await _project_fast_path(text)
    if skill_name == "file-assistant":
        return await _file_fast_path(text)
    if skill_name == "pdf-creator":
        return await _pdf_fast_path(text)
    if skill_name == "deck-creator":
        return await _deck_fast_path(text)
    if skill_name == "source-notebook":
        return await _source_notebook_fast_path(text)
    if skill_name == "help":
        return _help_fast_path()
    return None


async def _project_fast_path(text: str) -> str:
    path = _extract_existing_path(text)
    if path and path.is_dir():
        return await analyze_project(str(path))
    query = _clean_query(text)
    current = Path.cwd()
    if _looks_like_project(current) and _query_targets_project(query, current.name, text):
        return await analyze_project(str(current))
    return await discover_projects(query=query, max_results=8)


async def _file_fast_path(text: str) -> str | None:
    path = _extract_existing_path(text)
    if not path:
        return None
    if path.is_dir():
        entries = await list_directory(str(path))
        return "## Ordnerinhalt\n" + "\n".join(f"- {entry}" for entry in entries)
    if path.is_file():
        return await read_file(str(path))
    return None


async def _pdf_fast_path(text: str) -> str:
    topic = _topic_from_text(text, default="MiMi Nox Executive Briefing")
    filename = f"{_filename_slug(topic)}_briefing.pdf"
    content = _build_pdf_brief_content(topic, text)
    result = await create_pdf(
        title=topic,
        content=content,
        filename=filename,
        template="brief",
    )
    if result.startswith("PDF_FILE:"):
        return "\n".join([
            "## PDF erstellt",
            "Das Dokument wurde lokal erzeugt und kann direkt geöffnet werden.",
            result,
            "",
            "Kurzinhalt: Executive Summary, Kernpunkte, Empfehlungen und Source Notes wurden strukturiert in das PDF übernommen.",
        ])
    return "\n".join([
        "## PDF-Erstellung fehlgeschlagen",
        result,
    ])


def _build_pdf_brief_content(topic: str, original_request: str) -> str:
    today = datetime.now().strftime("%d.%m.%Y")
    cleaned_request = re.sub(r"^/\w+\s*", "", original_request or "").strip()
    return "\n".join([
        "# Executive Summary",
        (
            f"{topic} wird als entscheidungsreifes Kurzbriefing aufbereitet. "
            "Der Fokus liegt auf klarer Einordnung, umsetzbaren Empfehlungen und transparenten Annahmen."
        ),
        "",
        "## Key Points",
        "- Zielbild, Nutzen und naechste Schritte sind getrennt dargestellt.",
        "- Offene Annahmen werden nicht als belegte Fakten ausgegeben.",
        "- Der Inhalt ist fuer schnelle Management- oder Projektentscheidungen strukturiert.",
        "",
        "## Empfehlungen",
        "1. Zielgruppe, Entscheidung und gewuenschtes Ergebnis vor dem finalen Versand pruefen.",
        "2. Wenn externe Quellen oder Unternehmensdaten relevant sind, diese als Input anhaengen.",
        "3. Fuer Board-, Kunden- oder Investorenmaterial danach ein Deck oder Source Notebook ableiten.",
        "",
        "### Source Notes",
        f"- Erstellt lokal am {today} aus der Nutzeranfrage.",
        f"- Nutzeranfrage: {cleaned_request or topic}",
        "- Keine externen Quellen oder Datei-Anhaenge wurden fuer dieses Briefing bereitgestellt.",
    ])


def _help_fast_path() -> str:
    return (
        "## MiMi Nox Kurzuebersicht\n"
        "- `/project`: lokale Projekte finden und analysieren\n"
        "- `/files`: Dateien und Ordner lesen\n"
        "- `/pdf`, `/chart`, `/svg`: hochwertige lokale Artefakte erstellen\n"
        "- `/scan`: Bilder und Screenshots analysieren\n"
        "- `/research`: aktuelle Web-Recherche mit Quellen\n"
        "- `/shell`: Terminal-Befehle nur nach deiner Bestätigung"
    )


async def _source_notebook_fast_path(text: str) -> str | None:
    if _wants_deck(text):
        return await _deck_fast_path(text, notebook_mode=True)
    path = _extract_existing_path(text)
    if not path:
        return None
    created = await create_source_notebook(
        paths=[str(path)],
        title=_topic_from_text(text, default="MiMi Nox Source Notebook"),
    )
    notebook_path = _extract_marker_path(created, "SOURCE_NOTEBOOK_FILE:")
    if not notebook_path:
        return created
    question = _clean_notebook_question(text)
    queried = await query_source_notebook(notebook_path=notebook_path, question=question)
    brief = await export_source_brief(
        notebook_path=notebook_path,
        question=question,
        filename="mimi_nox_source_brief.md",
    )
    return "\n\n".join([
        "## Quellen-Notebook erstellt",
        created,
        "## Quellengebundene Antwort",
        queried,
        "## Briefing",
        brief,
    ])


async def _deck_fast_path(text: str, notebook_mode: bool = False) -> str:
    topic = _topic_from_text(text, default="KI Architektur 2026")
    lower = text.lower()
    audience = "board, executive committee, and technical leadership"
    if any(word in lower for word in ("investor", "investoren", "vc", "fundraising")):
        audience = "investors and venture partners"
    elif any(word in lower for word in ("kunde", "kunden", "sales", "vertrieb")):
        audience = "enterprise customers and buying committees"

    thesis = (
        f"{topic} braucht eine klare Executive-Storyline fuer Architekturentscheidungen, Risiken und Roadmap."
    )
    source_notes = "Generated from user prompt; no local source path was provided."
    evidence_level = "assumptions"
    brief_result = ""

    source_path = _extract_existing_path(text)
    if notebook_mode and source_path:
        created = await create_source_notebook(
            paths=[str(source_path)],
            title=f"{topic} Source Notebook",
        )
        notebook_path = _extract_marker_path(created, "SOURCE_NOTEBOOK_FILE:")
        if notebook_path:
            question = f"Welche belastbaren Aussagen und Belege sind fuer ein Executive Slide Deck zu {topic} relevant?"
            queried = await query_source_notebook(notebook_path=notebook_path, question=question, max_chunks=8)
            brief_result = await export_source_brief(
                notebook_path=notebook_path,
                question=question,
                filename="mimi_nox_deck_source_brief.md",
            )
            source_notes = f"Grounded in local source notebook: {notebook_path}"
            evidence_level = "sources"
            thesis = _thesis_from_query_result(queried, fallback=thesis)

    filename_slug = _filename_slug(topic)
    pptx = await create_pptx_deck(
        topic=topic,
        audience=audience,
        thesis=thesis,
        filename=f"{filename_slug}_executive_deck.pptx",
        deck_profile="strategy-leadership",
        design_theme="executive",
        source_notes=source_notes,
        evidence_level=evidence_level,
        enterprise_grade=True,
        brand_name="MiMi Nox",
        brand_primary="#0f5132",
        brand_secondary="#16a34a",
    )
    pdf = await create_pitch_deck(
        topic=topic,
        audience=audience,
        thesis=thesis,
        filename=f"{filename_slug}_executive_deck.pdf",
        include_animation_preview=True,
        deck_profile="strategy-leadership",
        design_theme="executive",
        source_notes=source_notes,
        evidence_level=evidence_level,
        enterprise_grade=True,
    )
    studio = _write_deck_studio_page(
        topic=topic,
        pptx_result=pptx,
        pdf_result=pdf,
        brief_result=brief_result,
        wants_images=_wants_images(text),
        evidence_level=evidence_level,
        source_notes=source_notes,
    )

    parts = [
        "## Slide Studio erstellt",
        "Ich habe eine lokale Studio-Preview mit auswählbaren Downloads erzeugt.",
        "",
        "### Öffnen und auswählen",
        f"DECK_STUDIO_FILE:{studio}",
        "",
        "### Enthaltene Artefakte",
        _summarize_delivery_artifacts(pptx, pdf, brief_result),
    ]
    if brief_result:
        parts.extend(["", "### Source Brief", brief_result])
    parts.extend([
        "",
        "Hinweis: Falls du konkrete Firmen-Bilder, Brand-Guidelines oder vorhandene PPTX-Templates einbindest, kann ich daraus eine strengere Template-/Brand-Version erzeugen.",
    ])
    return "\n".join(parts)


def _extract_existing_path(text: str) -> Path | None:
    candidates = re.findall(r"(?:~|/)[^\s`'\"<>]+", text)
    for raw in candidates:
        candidate = Path(raw.rstrip(".,;:")).expanduser()
        if candidate.exists():
            return candidate
    return None


def _wants_deck(text: str) -> bool:
    return bool(re.search(
        r"\b(slides?|folien|pitch\s*deck|pitchdeck|praesentation|präsentation|pptx|powerpoint|deck)\b",
        text or "",
        flags=re.IGNORECASE,
    ))


def _topic_from_text(text: str, default: str) -> str:
    cleaned = re.sub(r"^/\w+\s*", " ", text or "").strip()
    cleaned = re.sub(
        r"\b(erstell(e|en)?|mach(e|en)?|notebook\s*lm|slides?|folien|pitch\s*deck|pitchdeck|pptx|powerpoint|mit bilder(n)?|bilder|für|fuer|mir|ein|eine|einen)\b",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    topic = " ".join(cleaned.split()).strip(" .,:;-")
    return topic[:90] if topic else default


def _clean_notebook_question(text: str) -> str:
    cleaned = re.sub(r"^/\w+\s*", "", text or "").strip()
    return cleaned or "Fasse die wichtigsten belegten Aussagen aus den Quellen zusammen."


def _extract_marker_path(result: str, marker: str) -> str:
    if marker not in result:
        return ""
    return result.split(marker, 1)[1].splitlines()[0].strip()


def _thesis_from_query_result(result: str, fallback: str) -> str:
    for line in result.splitlines():
        stripped = line.strip(" -")
        if 80 <= len(stripped) <= 220 and "[S" in stripped:
            return re.sub(r"\s*\[S\d{3}-C\d{3}\]", "", stripped).strip()
    return fallback


def _filename_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.lower()).strip("._-")
    return slug[:64] or "mimi_nox_deck"


def _wants_images(text: str) -> bool:
    return bool(re.search(r"\b(bild|bilder|image|images|visuals?|grafiken|graphics)\b", text or "", re.IGNORECASE))


def _marker_path(result: str, marker: str) -> str:
    return _extract_marker_path(result, marker)


def _summarize_delivery_artifacts(pptx: str, pdf: str, brief: str = "") -> str:
    items = [
        ("Studio PPTX", _marker_path(pptx, "PPTX_DECK_FILE:")),
        ("PDF Slides", _marker_path(pdf, "PITCH_DECK_FILE:")),
        ("Animated Preview", _marker_path(pdf, "PREVIEW_FILE:")),
        ("Render QA", _marker_path(pdf, "RENDER_QA_FILE:")),
        ("Quality Scorecard", _marker_path(pptx, "SCORECARD_FILE:")),
        ("Contact Sheet", _marker_path(pptx, "CONTACT_SHEET_FILE:")),
        ("Deck Spec", _marker_path(pptx, "DECK_SPEC_FILE:") or _marker_path(pdf, "DECK_SPEC_FILE:")),
        ("Visual QA", _marker_path(pptx, "VISUAL_QA_FILE:") or _marker_path(pdf, "VISUAL_QA_FILE:")),
        ("Evidence Ledger", _marker_path(pptx, "EVIDENCE_LEDGER_FILE:") or _marker_path(pdf, "EVIDENCE_LEDGER_FILE:")),
    ]
    if brief:
        items.append(("Source Brief", _marker_path(brief, "SOURCE_BRIEF_FILE:")))
    return "\n".join(f"- {label}: `{path}`" for label, path in items if path)


def _write_deck_studio_page(
    *,
    topic: str,
    pptx_result: str,
    pdf_result: str,
    brief_result: str,
    wants_images: bool,
    evidence_level: str,
    source_notes: str,
) -> Path:
    from core.deck_render import render_studio

    pptx_path = Path(_marker_path(pptx_result, "PPTX_DECK_FILE:"))
    pdf_path = Path(_marker_path(pdf_result, "PITCH_DECK_FILE:"))
    preview_path = Path(_marker_path(pdf_result, "PREVIEW_FILE:"))
    render_qa_path = Path(_marker_path(pdf_result, "RENDER_QA_FILE:"))
    score_path = Path(_marker_path(pptx_result, "SCORECARD_FILE:"))
    manifest_path = Path(_marker_path(pptx_result, "MANIFEST_FILE:"))
    qa_path = Path(_marker_path(pptx_result, "QA_FILE:"))
    contact_path = Path(_marker_path(pptx_result, "CONTACT_SHEET_FILE:"))
    deck_spec_path = Path(_marker_path(pptx_result, "DECK_SPEC_FILE:") or _marker_path(pdf_result, "DECK_SPEC_FILE:"))
    visual_qa_path = Path(_marker_path(pptx_result, "VISUAL_QA_FILE:") or _marker_path(pdf_result, "VISUAL_QA_FILE:"))
    evidence_ledger_path = Path(_marker_path(pptx_result, "EVIDENCE_LEDGER_FILE:") or _marker_path(pdf_result, "EVIDENCE_LEDGER_FILE:"))
    brief_path = Path(_marker_path(brief_result, "SOURCE_BRIEF_FILE:")) if brief_result else None
    out = pdf_path.with_suffix(".studio.html") if str(pdf_path) else Path.home() / "Downloads" / "mimi_nox_slide_studio.html"

    spec = _read_json(deck_spec_path)
    if spec:
        paths = {
            "pdf": pdf_path,
            "pptx": pptx_path,
            "preview": preview_path,
            "render_qa": render_qa_path,
            "scorecard": score_path,
            "manifest": manifest_path,
            "pptx_qa": qa_path,
            "contact_sheet": contact_path,
            "deck_spec": deck_spec_path,
            "visual_qa": visual_qa_path,
            "evidence_ledger": evidence_ledger_path,
        }
        out.write_text(render_studio(spec, paths, wants_images=wants_images), encoding="utf-8")
        return out

    score = _read_json(score_path)
    manifest = _read_json(manifest_path)
    qa = _read_json(qa_path)
    slides = manifest.get("slides", []) if isinstance(manifest, dict) else []
    qa_slides = qa.get("slides", []) if isinstance(qa, dict) else []
    score_value = score.get("quality_score", 0) if isinstance(score, dict) else 0
    warnings = list(score.get("warnings", []) if isinstance(score, dict) else [])
    if wants_images:
        warnings.append("Image request handled with executive abstract visuals. Add local image assets or a brand kit for photo-level visual replacement.")

    download_cards = [
        ("Download PDF", pdf_path, "Best for sharing and review"),
        ("Download PPTX", pptx_path, "Best for PowerPoint/Keynote editing"),
        ("Open HTML Preview", preview_path, "Best for presenting the flow"),
        ("Open Render QA", render_qa_path, "PDF visual bounds, text flow, and render checks"),
        ("Open Contact Sheet", contact_path, "Best for QA before sharing"),
        ("Open QA Report", qa_path, "Deterministic slide-level quality checks"),
        ("Open Claim Manifest", manifest_path, "Storyline, evidence, brand, and export metadata"),
        ("Open QA Scorecard", score_path, "Quality/rubric evidence"),
    ]
    if brief_path:
        download_cards.append(("Source Brief", brief_path, "NotebookLM-style evidence register"))

    cards_html = "\n".join(
        f"""
        <a class="download" data-qa="deck-studio-download" href="file://{html.escape(str(path))}">
          <b>{html.escape(label)}</b>
          <span>{html.escape(desc)}</span>
          <small>{html.escape(path.name)}</small>
        </a>"""
        for label, path, desc in download_cards
        if str(path)
    )
    slide_cards = "\n".join(
        _studio_slide_card(index, slide, qa_slides[index - 1] if index - 1 < len(qa_slides) else {})
        for index, slide in enumerate(slides, 1)
    )
    warning_html = "\n".join(f"<li>{html.escape(str(warning))}</li>" for warning in warnings) or "<li>No blocking warnings.</li>"
    status_cards = _studio_status_cards(
        score=score,
        evidence_level=evidence_level,
        source_notes=source_notes,
        wants_images=wants_images,
        brief_path=brief_path,
    )
    out.write_text(f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(topic)} - MiMi Nox Slide Studio</title>
<style>
:root{{color-scheme:light;--ink:#101820;--muted:#56616b;--line:#d9e2dc;--green:#16a34a;--green2:#0f5132;--paper:#fbfcfb;--soft:#eef7f1}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,Aptos,Arial,sans-serif}}
header{{min-height:78vh;display:grid;align-content:end;padding:7vw 8vw 5vw;background:linear-gradient(135deg,#f8faf7 0%,#eef7f1 52%,#ffffff 100%);border-bottom:1px solid var(--line)}}
.eyebrow{{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--green2);font-weight:800}}
h1{{font-size:clamp(44px,7vw,94px);line-height:.92;max-width:980px;margin:18px 0 20px;letter-spacing:0}}
.lead{{font-size:clamp(18px,2.2vw,28px);line-height:1.28;max-width:850px;color:var(--muted);margin:0}}
.score{{display:inline-flex;gap:12px;align-items:center;margin-top:34px;padding:12px 16px;border:1px solid var(--line);background:white}}
.score b{{font-size:28px;color:var(--green2)}} .score span{{font-size:13px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-weight:800}}
main{{padding:34px 8vw 70px}} h2{{font-size:26px;margin:0 0 18px}} .downloads{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-bottom:38px}}
.download{{display:grid;gap:8px;text-decoration:none;color:var(--ink);background:white;border:1px solid var(--line);border-left:5px solid var(--green);padding:18px;min-height:128px}}
.download:hover{{transform:translateY(-2px);box-shadow:0 18px 42px rgba(16,24,32,.10)}} .download span,.download small{{color:var(--muted);line-height:1.35}}
.status-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-bottom:34px}} .status-card{{background:white;border:1px solid var(--line);border-top:5px solid var(--green);padding:18px}} .status-card b{{display:block;font-size:18px;margin-bottom:8px}} .status-card span{{color:var(--muted);font-size:13px;line-height:1.35}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}} article{{background:white;border:1px solid var(--line);padding:20px;min-height:220px}}
article .num{{color:var(--green);font-size:12px;font-weight:900;letter-spacing:.12em}} article h3{{font-size:22px;line-height:1.1;margin:12px 0}} article p{{color:var(--muted);line-height:1.45}} article strong{{display:block;margin-top:12px;color:var(--green2)}}
.warnings{{margin-top:34px;background:#fffaf0;border:1px solid #f2d7aa;border-left:5px solid #b7791f;padding:18px 22px;color:#5a3b0b}}
footer{{border-top:1px solid var(--line);padding:22px 8vw;color:var(--muted);font-size:13px}}
</style>
<header>
  <div class="eyebrow">MiMi Nox Slide Studio · NotebookLM-style local delivery</div>
  <h1>{html.escape(topic)}</h1>
  <p class="lead">Review the executive storyline, inspect QA, then choose the file format you want to download. Files stay local on this Mac.</p>
  <div class="score"><b>{int(score_value)}/100</b><span>Enterprise quality score · evidence: {html.escape(evidence_level)}</span></div>
</header>
<main>
  <h2>Studio Status</h2>
  <section class="status-grid">{status_cards}</section>
  <h2>Choose Output</h2>
  <section class="downloads">{cards_html}</section>
  <h2>Slide Contact Sheet</h2>
  <section class="grid">{slide_cards}</section>
  <section class="warnings"><b>Quality Notes</b><ul>{warning_html}</ul></section>
</main>
<footer>Source notes: {html.escape(source_notes)}</footer>
</html>""", encoding="utf-8")
    return out


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _studio_status_cards(
    *,
    score: dict,
    evidence_level: str,
    source_notes: str,
    wants_images: bool,
    brief_path: Path | None,
) -> str:
    layout_score = int(score.get("quality_score", 0)) if isinstance(score, dict) else 0
    evidence_label = "Source-grounded" if evidence_level == "sources" else "Assumption-led"
    image_label = "Asset-ready" if wants_images else "Executive abstract visuals"
    source_label = "Source brief available" if brief_path else "No source brief yet"
    cards = [
        ("Narrative", f"{layout_score}/100 enterprise storyline and design score."),
        ("Evidence Coverage", f"{evidence_label}. {source_notes[:130]}"),
        ("Visual System", f"{image_label}; local brand assets can be attached for photo-level slides."),
        ("Exports", "Studio preview, PDF, editable PPTX, contact sheet, QA, and scorecard."),
        ("NotebookLM Layer", source_label),
    ]
    return "\n".join(
        f"<div class=\"status-card\"><b>{html.escape(title)}</b><span>{html.escape(body)}</span></div>"
        for title, body in cards
    )


def _studio_slide_card(index: int, slide: dict, qa_slide: dict) -> str:
    title = str(slide.get("title") or f"Slide {index}")
    claim = str(slide.get("claim") or "")
    evidence = str(slide.get("proof") or slide.get("source_status") or "Evidence status")
    runs = qa_slide.get("editable_text_runs", 0)
    return (
        "<article>"
        f"<div class=\"num\">SLIDE {index:02d}</div>"
        f"<h3>{html.escape(title)}</h3>"
        f"<p>{html.escape(claim)}</p>"
        f"<strong>{html.escape(evidence)}</strong>"
        f"<p>{int(runs)} editable text runs</p>"
        "</article>"
    )


def _clean_query(text: str) -> str:
    query = text
    for word in (
        "finde", "such", "suche", "analysiere", "analysieren", "analyse",
        "projekt", "project", "repo", "repository", "ist-zustand",
        "technische", "technischen", "fixes", "nennen", "wichtigsten",
    ):
        query = re.sub(rf"\b{re.escape(word)}\b", " ", query, flags=re.IGNORECASE)
    return " ".join(query.split())


def _looks_like_project(path: Path) -> bool:
    return any(
        (path / marker).exists()
        for marker in (".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod", "requirements.txt")
    )


def _query_targets_project(query: str, project_name: str, original_text: str) -> bool:
    lower_query = (query or "").lower()
    lower_original = (original_text or "").lower()
    name = (project_name or "").lower()
    if name and name in lower_query:
        return True
    return bool(re.search(r"\b(dieses|aktuelles|current|this)\s+(repo|repository|projekt|project)\b", lower_original))

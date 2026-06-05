"""Local quality gates for MiMi Nox skills and artifacts."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import zipfile
import html as html_lib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ToolResult:
    tool: str
    status: str
    summary: str
    evidence: list[str] = field(default_factory=list)
    artifacts: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: str = ""


@dataclass
class QualityReport:
    status: str
    needs_revision: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class ArtifactValidationReport:
    artifact_type: str
    status: str
    path: str
    warnings: list[str] = field(default_factory=list)


def normalize_tool_result(tool: str, result: str) -> ToolResult:
    raw = str(result or "")
    if raw.startswith("[") and ("Fehler" in raw or "Error" in raw or "error" in raw.lower()):
        return ToolResult(
            tool=tool,
            status="error",
            summary=raw.strip("[]"),
            warnings=[raw],
            raw=raw,
        )

    artifacts = _artifacts_from_raw(raw)
    if artifacts:
        artifact_type = artifacts[0]["type"].upper()
        summary = f"{len(artifacts)} artifacts created" if len(artifacts) > 1 else f"{artifact_type} artifact created"
        return ToolResult(
            tool=tool,
            status="success",
            summary=summary,
            evidence=[f"{tool} returned {raw}"],
            artifacts=artifacts,
            raw=raw,
        )

    summary = raw.strip().splitlines()[0][:160] if raw.strip() else "Tool returned empty output"
    warnings = ["Tool returned empty output"] if not raw.strip() else []
    return ToolResult(
        tool=tool,
        status="warning" if warnings else "success",
        summary=summary,
        evidence=[raw[:500]] if raw.strip() else [],
        warnings=warnings,
        raw=raw,
    )


def evaluate_quality(*, answer: str, skill, tool_results: list[ToolResult]) -> QualityReport:
    issues: list[str] = []
    warnings: list[str] = []
    answer_text = answer or ""
    successful_artifacts = [
        artifact
        for result in tool_results
        if result.status == "success"
        for artifact in result.artifacts
    ]

    for artifact_type in getattr(skill, "artifact_types", []) or []:
        if _answer_claims_artifact(answer_text, artifact_type) and not any(
            artifact.get("type") == artifact_type for artifact in successful_artifacts
        ):
            issues.append(f"Missing real {artifact_type} artifact evidence for final answer.")

    if getattr(skill, "tools", None) and not tool_results:
        warnings.append("Skill declared tools but no tool results were captured.")

    if "tbd" in answer_text.lower() or "todo" in answer_text.lower():
        warnings.append("Answer contains unfinished placeholder wording.")

    return QualityReport(
        status="failed" if issues else "passed",
        needs_revision=bool(issues),
        issues=issues,
        warnings=warnings,
    )


def validate_artifact(artifact: dict) -> ArtifactValidationReport:
    if artifact.get("type") == "pdf":
        return validate_pdf_artifact(str(artifact.get("path", "")))
    if artifact.get("type") == "deck":
        return validate_pitch_deck_artifact(str(artifact.get("path", "")))
    if artifact.get("type") == "pptx":
        return validate_pptx_deck_artifact(str(artifact.get("path", "")))
    if artifact.get("type") == "deck_studio":
        return validate_deck_studio_artifact(str(artifact.get("path", "")))
    if artifact.get("type") == "notebook":
        return validate_source_notebook_artifact(str(artifact.get("path", "")))
    if artifact.get("type") == "source_brief":
        return validate_source_brief_artifact(str(artifact.get("path", "")))
    path = str(artifact.get("path", ""))
    warnings = []
    if not path or not Path(path).exists():
        warnings.append("Artifact file does not exist.")
    return ArtifactValidationReport(
        artifact_type=str(artifact.get("type", "artifact")),
        status="failed" if warnings else "passed",
        path=path,
        warnings=warnings,
    )


def validate_deck_studio_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    studio_path = Path(path)
    if not studio_path.exists():
        return ArtifactValidationReport("deck_studio", "failed", path, ["Deck Studio file does not exist."])
    text = studio_path.read_text(encoding="utf-8", errors="replace")
    for marker in ("MiMi Nox Slide Studio", "Choose Output", "Slide Contact Sheet"):
        if marker not in text:
            warnings.append(f"Deck Studio is missing required marker: {marker}.")
    has_pptx_download = "Download PPTX" in text or "Download editable PPTX" in text
    has_pdf_download = "Download PDF" in text or "Open PDF slides" in text
    if not has_pptx_download or not has_pdf_download:
        warnings.append("Deck Studio does not expose selectable PDF/PPTX downloads.")
    if "Open QA Report" not in text:
        warnings.append("Deck Studio does not expose the deterministic QA report.")
    if "Open Claim Manifest" not in text:
        warnings.append("Deck Studio does not expose the claim manifest.")
    linked_paths = _extract_existing_file_links(text)
    linked_suffixes = {path.suffix.lower() for path in linked_paths}
    linked_names = {path.name.lower() for path in linked_paths}
    if len(linked_paths) < 4:
        warnings.append("Deck Studio is missing real local download links.")
    if ".pdf" not in linked_suffixes:
        warnings.append("Deck Studio does not link to a real local PDF export.")
    if ".pptx" not in linked_suffixes:
        warnings.append("Deck Studio does not link to a real local PPTX export.")
    if not any(name.endswith(".qa.json") for name in linked_names):
        warnings.append("Deck Studio does not link to a real local QA report.")
    if not any(name.endswith(".manifest.json") for name in linked_names):
        warnings.append("Deck Studio does not link to a real local claim manifest.")
    return ArtifactValidationReport("deck_studio", "failed" if warnings else "passed", str(studio_path), warnings)


def _extract_existing_file_links(text: str) -> list[Path]:
    paths: list[Path] = []
    for raw_href in re.findall(r'href=["\']file://([^"\']+)["\']', text or ""):
        candidate = Path(html_lib.unescape(raw_href)).expanduser()
        if candidate.exists():
            paths.append(candidate)
    return paths


def validate_source_notebook_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    notebook_path = Path(path)
    if not notebook_path.exists():
        return ArtifactValidationReport("notebook", "failed", path, ["Source notebook file does not exist."])
    try:
        import json

        payload = json.loads(notebook_path.read_text(encoding="utf-8"))
        if int(payload.get("schema_version", 0)) < 1:
            warnings.append("Source notebook schema version is missing.")
        if int(payload.get("source_count", 0)) < 1:
            warnings.append("Source notebook has no indexed sources.")
        if int(payload.get("chunk_count", 0)) < 1:
            warnings.append("Source notebook has no evidence chunks.")
        chunks = payload.get("chunks", [])
        if chunks and not all(chunk.get("chunk_id") and chunk.get("text") for chunk in chunks[:10]):
            warnings.append("Source notebook chunks are missing IDs or text.")
    except Exception as exc:
        warnings.append(f"Source notebook validation failed: {exc}")
    return ArtifactValidationReport("notebook", "failed" if warnings else "passed", str(notebook_path), warnings)


def validate_source_brief_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    brief_path = Path(path)
    if not brief_path.exists():
        return ArtifactValidationReport("source_brief", "failed", path, ["Source brief file does not exist."])
    text = brief_path.read_text(encoding="utf-8", errors="replace")
    for marker in ("Executive Summary", "Evidence Register", "Source Manifest"):
        if marker not in text:
            warnings.append(f"Source brief is missing required section: {marker}.")
    if not re_search_citation(text):
        warnings.append("Source brief does not contain source chunk citations.")
    return ArtifactValidationReport("source_brief", "failed" if warnings else "passed", str(brief_path), warnings)


def validate_pptx_deck_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    pptx_path = Path(path)
    if not pptx_path.exists():
        return ArtifactValidationReport("pptx", "failed", path, ["PPTX deck file does not exist."])
    if pptx_path.suffix.lower() != ".pptx":
        warnings.append("Deck export is not a .pptx file.")
    try:
        with zipfile.ZipFile(pptx_path) as pptx:
            names = set(pptx.namelist())
            required = {"[Content_Types].xml", "_rels/.rels", "ppt/presentation.xml", "ppt/_rels/presentation.xml.rels"}
            missing = sorted(required - names)
            if missing:
                warnings.append(f"PPTX package is missing required parts: {', '.join(missing)}.")
            slide_names = sorted(name for name in names if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
            if len(slide_names) < 8:
                warnings.append("PPTX deck has fewer than 8 slides.")
            text_runs = 0
            for slide_name in slide_names:
                xml = pptx.read(slide_name).decode("utf-8", errors="replace")
                text_runs += xml.count("<a:t>")
                if "Proof Object:" in xml or "Animation Plan" in xml:
                    warnings.append("PPTX deck contains internal presentation markers.")
            if text_runs < max(12, len(slide_names) * 4):
                warnings.append("PPTX deck has too few editable text runs.")
    except Exception as exc:
        warnings.append(f"PPTX validation failed: {exc}")

    warnings.extend(_validate_deck_sidecars(pptx_path))
    qa_path = pptx_path.with_suffix(".qa.json")
    contact_path = pptx_path.with_suffix(".contact-sheet.html")
    if not qa_path.exists():
        warnings.append("PPTX visual QA report is missing.")
    if not contact_path.exists():
        warnings.append("PPTX contact sheet is missing.")
    return ArtifactValidationReport(
        artifact_type="pptx",
        status="failed" if warnings else "passed",
        path=str(pptx_path),
        warnings=warnings,
    )


def _validate_deck_sidecars(path: Path) -> list[str]:
    warnings: list[str] = []
    score_path = path.with_suffix(".scorecard.json")
    if not score_path.exists():
        warnings.append("Deck scorecard is missing.")
    else:
        try:
            import json

            score = json.loads(score_path.read_text(encoding="utf-8"))
            minimum_score = int(score.get("minimum_score", 92 if score.get("enterprise_grade") else 85))
            if int(score.get("quality_score", 0)) < minimum_score:
                warnings.append("Deck scorecard is below the acceptance threshold.")
            if score.get("status") != "passed":
                warnings.append("Deck scorecard status is not acceptable.")
            if score.get("enterprise_grade") and not score.get("checks", {}).get("no_amateur_language"):
                warnings.append("Deck contains amateur language according to scorecard.")
        except Exception as exc:
            warnings.append(f"Deck scorecard validation failed: {exc}")

    manifest_path = path.with_suffix(".manifest.json")
    if not manifest_path.exists():
        warnings.append("Deck claim-spine manifest is missing.")
    render_qa_path = path.with_suffix(".render-qa.json")
    if path.suffix.lower() == ".pdf":
        if not render_qa_path.exists():
            warnings.append("Deck render QA report is missing.")
        else:
            try:
                import json

                render_qa = json.loads(render_qa_path.read_text(encoding="utf-8"))
                if render_qa.get("status") != "passed":
                    warnings.append("Deck render QA status is not acceptable.")
                checks = render_qa.get("checks", {})
                if checks.get("no_text_in_visual_column") is False:
                    warnings.append("Deck render QA detected text entering the visual column.")
                if not checks.get("visuals_bounded"):
                    warnings.append("Deck render QA detected out-of-bounds visual elements.")
            except Exception as exc:
                warnings.append(f"Deck render QA validation failed: {exc}")
    return warnings


def validate_pitch_deck_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    pdf_path = Path(path)
    if not pdf_path.exists():
        return ArtifactValidationReport("deck", "failed", path, ["Pitch deck PDF file does not exist."])
    if pdf_path.suffix.lower() != ".pdf":
        warnings.append("Pitch deck export is not a PDF file.")

    try:
        import pdfplumber

        with pdfplumber.open(str(pdf_path)) as pdf:
            page_count = len(pdf.pages)
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if page_count < 8:
            warnings.append("Pitch deck has fewer than 8 slides.")
        for marker in ("Animation Plan", "Proof Object:", "Evidence: assumptions", "DECK_STUDIO_FILE:"):
            if marker in text:
                warnings.append(f"Pitch deck contains internal marker: {marker}.")
        if not text.strip():
            warnings.append("Pitch deck has no extractable text.")
        if "(cid:" in text:
            warnings.append("Pitch deck text extraction contains broken glyph markers.")
    except Exception as exc:
        warnings.append(f"Pitch deck validation failed: {exc}")

    try:
        import json as _json
        from core.deck_quality import qa_pdf_render

        spec_path = pdf_path.with_suffix(".deck-spec.json")
        spec = _json.loads(spec_path.read_text(encoding="utf-8")) if spec_path.exists() else {"slides": []}
        render_qa = qa_pdf_render(pdf_path, spec)
        pdf_path.with_suffix(".render-qa.json").write_text(
            json.dumps(render_qa, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        warnings.append(f"Pitch deck render QA failed: {exc}")

    warnings.extend(_validate_deck_sidecars(pdf_path))

    render_warning = _pdf_render_contrast_warning(pdf_path)
    if render_warning and "No such file or directory" not in render_warning:
        warnings.append(render_warning)

    return ArtifactValidationReport(
        artifact_type="deck",
        status="failed" if warnings else "passed",
        path=str(pdf_path),
        warnings=warnings,
    )


def validate_pdf_artifact(path: str) -> ArtifactValidationReport:
    warnings: list[str] = []
    pdf_path = Path(path)
    if not pdf_path.exists():
        return ArtifactValidationReport("pdf", "failed", path, ["PDF file does not exist."])
    if pdf_path.suffix.lower() != ".pdf":
        warnings.append("File extension is not .pdf.")

    try:
        import pdfplumber

        with pdfplumber.open(str(pdf_path)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        if not text.strip():
            warnings.append("PDF has no extractable text.")
        if "(cid:" in text:
            warnings.append("PDF text extraction contains broken glyph markers.")
    except Exception as exc:
        warnings.append(f"PDF text validation failed: {exc}")

    render_warning = _pdf_render_contrast_warning(pdf_path)
    if render_warning:
        warnings.append(render_warning)

    return ArtifactValidationReport(
        artifact_type="pdf",
        status="failed" if warnings else "passed",
        path=str(pdf_path),
        warnings=warnings,
    )


def _artifact_from_raw(raw: str) -> dict | None:
    artifacts = _artifacts_from_raw(raw)
    return artifacts[0] if artifacts else None


def _artifacts_from_raw(raw: str) -> list[dict]:
    artifacts: list[dict] = []
    for prefix, artifact_type in (
        ("PITCH_DECK_FILE:", "deck"),
        ("PPTX_DECK_FILE:", "pptx"),
        ("DECK_STUDIO_FILE:", "deck_studio"),
        ("RENDER_QA_FILE:", "render_qa"),
        ("DECK_SPEC_FILE:", "deck_spec"),
        ("VISUAL_QA_FILE:", "visual_qa"),
        ("EVIDENCE_LEDGER_FILE:", "evidence_ledger"),
        ("SOURCE_NOTEBOOK_FILE:", "notebook"),
        ("SOURCE_BRIEF_FILE:", "source_brief"),
        ("PDF_FILE:", "pdf"),
        ("SVG_FILE:", "svg"),
        ("CHART_FILE:", "chart"),
    ):
        for line in str(raw or "").splitlines():
            if line.startswith(prefix):
                path = line[len(prefix):].strip()
                if path:
                    artifact = {"type": artifact_type, "path": path}
                    if artifact not in artifacts:
                        artifacts.append(artifact)
    return artifacts


def re_search_citation(text: str) -> bool:
    import re

    return bool(re.search(r"\[S\d{3}-C\d{3}\]", text or ""))


def _answer_claims_artifact(answer: str, artifact_type: str) -> bool:
    lowered = answer.lower()
    if artifact_type == "pdf":
        return "pdf" in lowered or ".pdf" in lowered
    return artifact_type in lowered


def _pdf_render_contrast_warning(path: Path) -> str | None:
    if not shutil.which("pdftoppm"):
        return None
    try:
        from PIL import Image
    except Exception:
        return None

    with tempfile.TemporaryDirectory() as tmp:
        prefix = Path(tmp) / "page"
        try:
            subprocess.run(
                ["pdftoppm", "-png", "-f", "1", "-l", "1", str(path), str(prefix)],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            image = Image.open(Path(tmp) / "page-1.png").convert("RGB")
        except Exception as exc:
            return f"PDF render validation failed: {exc}"

        width, height = image.size
        crop = image.crop((int(width * 0.08), int(height * 0.14), int(width * 0.92), int(height * 0.55)))
        pixels = crop.tobytes()
        dark_pixels = sum(
            1
            for index in range(0, len(pixels), 3)
            if pixels[index] < 100 and pixels[index + 1] < 100 and pixels[index + 2] < 100
        )
        if dark_pixels < 400:
            return "PDF render has too few dark text pixels for reliable legibility."
    return None

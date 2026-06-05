from pathlib import Path
import asyncio
import json
import zipfile
from unittest.mock import AsyncMock, patch


def test_given_local_sources_when_create_notebook_then_manifest_has_citeable_chunks(tmp_path):
    """
    GIVEN local source files
    WHEN create_source_notebook_index indexes them
    THEN a local manifest with source IDs and citeable chunks is created
    """
    from core.source_notebook import create_source_notebook_index

    source = tmp_path / "market_notes.md"
    source.write_text(
        "# Market Notes\n\nEnterprise buyers require evidence registers, clear ROI, and conservative claims.",
        encoding="utf-8",
    )

    out = create_source_notebook_index(paths=[str(source)], title="Market Notebook")

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert '"source_id": "S001"' in text
    assert '"chunk_id": "S001-C001"' in text
    assert "Enterprise buyers" in text
    assert payload["schema_version"] == 2
    assert payload["coverage"]["indexed_sources"] == 1
    assert payload["claim_ledger"]
    assert payload["chunks"][0]["vector"]
    assert payload["chunks"][0]["ref"]


def test_given_notebook_when_query_then_answer_contains_evidence_citations(tmp_path):
    """
    GIVEN a source notebook
    WHEN query_source_notebook_index asks about a covered topic
    THEN the response is grounded and includes chunk citations
    """
    from core.source_notebook import create_source_notebook_index, query_source_notebook_index

    source = tmp_path / "deck_strategy.md"
    source.write_text(
        "The deck must avoid amateur language. It should include proof objects, source notes, and an evidence register.",
        encoding="utf-8",
    )
    notebook = create_source_notebook_index(paths=str(source), title="Deck Quality")

    result = query_source_notebook_index(
        notebook_path=str(notebook),
        question="What quality controls should the deck include?",
    )

    assert result["status"] == "grounded"
    assert result["evidence"]
    assert "[S001-C001]" in result["answer"]


def test_given_notebook_when_export_brief_then_brief_has_manifest_and_evidence(tmp_path):
    """
    GIVEN a source notebook
    WHEN export_source_brief_file is called
    THEN the Markdown brief contains executive summary, evidence, and source manifest
    """
    from core.source_notebook import create_source_notebook_index, export_source_brief_file

    source = tmp_path / "research.md"
    source.write_text(
        "NotebookLM-style quality depends on source grounding, citations, and local manifests.",
        encoding="utf-8",
    )
    notebook = create_source_notebook_index(paths=[str(source)], title="Research Notebook")

    brief = export_source_brief_file(
        notebook_path=str(notebook),
        question="What does high quality depend on?",
        filename="source_notebook_brief.md",
    )

    content = brief.read_text(encoding="utf-8")
    assert "Executive Summary" in content
    assert "Evidence Register" in content
    assert "Source Manifest" in content
    assert "Source Coverage" in content
    assert "Claim Ledger" in content
    assert "[S001-C001]" in content


def test_given_pptx_source_when_create_notebook_then_office_text_is_indexed(tmp_path):
    """
    GIVEN a local PPTX source
    WHEN Source Notebook v2 indexes it
    THEN slide text is extracted without external services
    """
    from core.source_notebook import create_source_notebook_index

    pptx = tmp_path / "strategy.pptx"
    with zipfile.ZipFile(pptx, "w") as package:
        package.writestr("ppt/slides/slide1.xml", "<p:sld><a:t>AI architecture operating model</a:t><a:t>Evidence-led platform strategy</a:t></p:sld>")

    out = create_source_notebook_index(paths=[str(pptx)], title="PPTX Notebook")
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["sources"][0]["parser"] == "office-xml"
    assert "AI architecture operating model" in payload["chunks"][0]["text"]


def test_given_source_notebook_skill_when_loaded_then_metadata_is_exposed():
    """
    GIVEN built-in source-notebook skill
    WHEN SkillLoader loads built-ins
    THEN /notebook resolves with source-grounded tools and artifacts
    """
    from core.skills import SkillLoader

    skill = SkillLoader().resolve_trigger("/notebook")

    assert skill is not None
    assert skill.name == "source-notebook"
    assert "create_source_notebook" in skill.tools
    assert "query_source_notebook" in skill.tools
    assert "notebook" in skill.artifact_types


def test_given_natural_notebooklm_slides_request_when_resolved_then_source_notebook_skill_is_used():
    """
    GIVEN a natural NotebookLM slide request without slash command
    WHEN the chat route resolves the skill
    THEN /notebook is selected so the deterministic artifact path can run
    """
    from server.routes.chat import _resolve_skill_invocation

    skill, content = _resolve_skill_invocation(
        "erstelle mir ein notebook lm slides für ki architektur mit bilder"
    )

    assert skill is not None
    assert skill.name == "source-notebook"
    assert content.startswith("erstelle mir")


def test_given_tool_schemas_when_loaded_then_source_notebook_tools_exist():
    """
    GIVEN tool schemas
    WHEN get_tool_schemas is called
    THEN source notebook tools are available to the model
    """
    from core.tools import get_tool_schemas

    names = {schema["function"]["name"] for schema in get_tool_schemas()}

    assert {"create_source_notebook", "query_source_notebook", "export_source_brief"} <= names


def test_given_notebook_slides_request_when_fast_path_runs_then_real_deck_files_are_created():
    """
    GIVEN a NotebookLM-style slide deck request
    WHEN the source-notebook fast path handles it
    THEN MiMi creates a Slide Studio with selectable downloads instead of an outline-only answer
    """
    from core.skill_fastpath import run_skill_fast_path

    answer = asyncio.run(
        run_skill_fast_path(
            "source-notebook",
            "/notebook Erstelle mir NotebookLM Slides für KI Architektur mit Bildern",
        )
    )

    assert answer is not None
    assert "DECK_STUDIO_FILE:" in answer
    assert "Studio PPTX:" in answer
    assert "PDF Slides:" in answer
    assert "kann keine" not in answer.lower()
    assert "gliederung" not in answer.lower()


def test_given_notebook_slides_request_when_studio_created_then_qa_and_manifest_downloads_are_visible():
    """
    GIVEN a NotebookLM-style slide deck request
    WHEN MiMi creates the Slide Studio
    THEN the user can open QA and claim-manifest files from the Studio page.
    """
    from core.skill_fastpath import run_skill_fast_path

    answer = asyncio.run(
        run_skill_fast_path(
            "source-notebook",
            "/notebook Erstelle mir NotebookLM Slides für KI Architektur",
        )
    )
    studio_line = next(line for line in answer.splitlines() if line.startswith("DECK_STUDIO_FILE:"))
    studio_path = Path(studio_line.split(":", 1)[1].strip())
    studio_html = studio_path.read_text(encoding="utf-8")

    assert "Open QA Report" in studio_html
    assert "Open Claim Manifest" in studio_html
    assert ".qa.json" in studio_html
    assert ".manifest.json" in studio_html


def test_given_web_notebook_request_when_fast_path_runs_then_real_source_notebook_is_created(monkeypatch, tmp_path):
    """
    GIVEN the user asks for a NotebookLM-style artifact from current web research
    WHEN the source-notebook fast path handles it
    THEN MiMi creates a real source notebook and source brief instead of waiting for model analysis.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    from core.skill_fastpath import run_skill_fast_path

    search_result = "\n\n".join([
        "[1] Official AI News",
        "    URL: https://example.com/ai-news",
        "    Source quality: general",
        "    Current AI news requires evidence and citations.",
    ])

    with patch("core.skill_fastpath.web_search", new=AsyncMock(return_value=search_result)):
        answer = asyncio.run(
            run_skill_fast_path(
                "source-notebook",
                "/notebook aktuelle KI News recherchieren und als Source Brief erstellen",
            )
        )

    assert answer is not None
    assert "Quellen-Notebook aus Web-Recherche erstellt" in answer
    assert "SOURCE_NOTEBOOK_FILE:" in answer
    assert "SOURCE_BRIEF_FILE:" in answer


def test_given_current_news_pdf_request_when_fast_path_runs_then_web_research_is_used(monkeypatch, tmp_path):
    """
    GIVEN a PDF request explicitly asks for current internet news
    WHEN the PDF fast path runs
    THEN it performs web_search before creating the PDF content.
    """
    monkeypatch.setenv("HOME", str(tmp_path))
    from core.skill_fastpath import run_skill_fast_path

    search_result = "\n\n".join([
        "[1] AI News Source",
        "    URL: https://example.com/current-ai",
        "    Source quality: general",
        "    AI market news and model releases are moving quickly.",
    ])

    with patch("core.skill_fastpath.web_search", new=AsyncMock(return_value=search_result)) as search:
        answer = asyncio.run(
            run_skill_fast_path(
                "pdf-creator",
                "/pdf erstelle eine PDF zu aktuellen KI News und suche im Internet danach",
            )
        )

    search.assert_awaited_once()
    assert "PDF_FILE:" in answer
    pdf_path = Path(answer.split("PDF_FILE:", 1)[1].splitlines()[0].strip())
    assert pdf_path.exists()


def test_given_contextualized_followup_when_topic_is_extracted_then_previous_intent_wins():
    """
    GIVEN a vague follow-up was contextualized with the previous user request
    WHEN the deterministic topic extractor runs
    THEN filenames and deck titles use the previous substantive topic, not 'das jetzt richtig'.
    """
    from core.skill_fastpath import _topic_from_text

    topic = _topic_from_text(
        "mach das jetzt richtig\n\nKontext aus vorheriger Anfrage: Erstelle NotebookLM Slides zu KI Architektur 2026 mit Bildern",
        default="Fallback",
    )

    assert topic == "KI Architektur 2026"


def test_given_source_artifacts_when_normalized_then_quality_can_validate(tmp_path):
    """
    GIVEN notebook and brief artifact markers
    WHEN normalize_tool_result and validate_artifact run
    THEN both artifacts validate as real local outputs
    """
    from core.quality import normalize_tool_result, validate_artifact
    from core.source_notebook import create_source_notebook_index, export_source_brief_file

    source = tmp_path / "quality.md"
    source.write_text("Cited source notebooks need chunk IDs and source manifests.", encoding="utf-8")
    notebook = create_source_notebook_index(paths=[str(source)], title="Quality")
    brief = export_source_brief_file(notebook_path=str(notebook), question="What is needed?")

    notebook_result = normalize_tool_result("create_source_notebook", f"SOURCE_NOTEBOOK_FILE:{notebook}")
    brief_result = normalize_tool_result("export_source_brief", f"SOURCE_BRIEF_FILE:{brief}")

    assert notebook_result.artifacts[0]["type"] == "notebook"
    assert brief_result.artifacts[0]["type"] == "source_brief"
    assert validate_artifact(notebook_result.artifacts[0]).status == "passed"
    assert validate_artifact(brief_result.artifacts[0]).status == "passed"

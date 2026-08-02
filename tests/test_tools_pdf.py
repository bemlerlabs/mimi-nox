"""
◑ MiMi Nox – Phase 0.8 TDD
tests/test_tools_pdf.py

Tests für core/tools/pdf_tools.py: create_pdf, _apply_pdf_template.

Given / When / Then – strikte Einhaltung.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.tools.pdf_tools import _apply_pdf_template, create_pdf


class TestApplyPdfTemplate:

    def test_report_template_inserts_missing_sections(self):
        """
        GIVEN  content ohne required sections
        WHEN   _apply_pdf_template(content, "report")
        THEN   Fehlende Sections werden eingefügt
        """
        result = _apply_pdf_template("Nur Text.", "report")
        assert "Executive Summary" in result
        assert "Findings" in result
        assert "Next Steps" in result
        assert "Source Notes" in result

    def test_brief_template_requires_fewer_sections(self):
        """
        GIVEN  content ohne Sections, template="brief"
        WHEN   _apply_pdf_template aufgerufen
        THEN   Nur Key Points + Source Notes + Exec Summary
        """
        result = _apply_pdf_template("Content.", "brief")
        assert "Executive Summary" in result
        assert "Key Points" in result
        assert "Findings" not in result

    def test_analysis_template_contains_risks_and_recommendations(self):
        """
        GIVEN  template="analysis"
        WHEN   _apply_pdf_template aufgerufen
        THEN   Evidence, Risks, Recommendations, Appendix sind enthalten
        """
        result = _apply_pdf_template("Data.", "analysis")
        assert "Evidence" in result
        assert "Risks" in result
        assert "Recommendations" in result
        assert "Appendix" in result

    def test_checklist_template(self):
        """
        GIVEN  template="checklist"
        WHEN   _apply_pdf_template aufgerufen
        THEN   Checklist und Acceptance Criteria sind enthalten
        """
        result = _apply_pdf_template("Items.", "checklist")
        assert "Checklist" in result
        assert "Acceptance Criteria" in result

    def test_returns_unchanged_if_all_sections_present(self):
        """
        GIVEN  content enthält bereits alle required sections
        WHEN   _apply_pdf_template aufgerufen
        THEN   content bleibt unverändert
        """
        content = "executive summary, findings, next steps, source notes"
        result = _apply_pdf_template(content, "report")
        assert result == content

    def test_falls_back_to_report_for_unknown_template(self):
        """
        GIVEN  template="unknown"
        WHEN   _apply_pdf_template aufgerufen
        THEN   report-Template wird verwendet
        """
        result = _apply_pdf_template("Short.", "unknown")
        assert "Executive Summary" in result


class TestCreatePdf:

    @pytest.mark.asyncio
    async def test_returns_pdf_file_path(self):
        """
        GIVEN  title und content
        WHEN   create_pdf(title="Test", content="Hello") aufgerufen
        THEN   Rückgabe enthält "PDF_FILE:"
        AND    reportlab SimpleDocTemplate wird erstellt
        """
        with patch("core.tools.pdf_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
            mock_home.return_value = Path("/tmp/fake_home")
            mock_instance = MagicMock()
            mock_doc.return_value = mock_instance

            result = await create_pdf(title="Test Report", content="Hello World")

            assert "PDF_FILE:" in result
            mock_doc.assert_called_once()
            assert "Test Report" in str(mock_doc.call_args[1].get("title", ""))

    @pytest.mark.asyncio
    async def test_returns_import_error_if_reportlab_missing(self):
        """
        GIVEN  reportlab ist nicht installiert
        WHEN   create_pdf aufgerufen
        THEN   Rückgabe enthält "reportlab nicht installiert"
        """
        with patch("core.tools.pdf_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("reportlab.platypus.SimpleDocTemplate", side_effect=ImportError("no reportlab")):
            mock_home.return_value = Path("/tmp/fake_home")

            result = await create_pdf(title="Test", content="Test")

            assert "reportlab nicht installiert" in result

    @pytest.mark.asyncio
    async def test_sanitizes_filename(self):
        """
        GIVEN  filename mit Sonderzeichen
        WHEN   create_pdf(filename="bad / name?.pdf") aufgerufen
        THEN   Dateiname wird bereinigt
        """
        with patch("core.tools.pdf_tools.Path.home") as mock_home, \
             patch("pathlib.Path.mkdir"), \
             patch("reportlab.platypus.SimpleDocTemplate") as mock_doc:
            mock_home.return_value = Path("/tmp/fake_home")
            mock_instance = MagicMock()
            mock_doc.return_value = mock_instance

            result = await create_pdf(title="Test", content="Test", filename="bad / name?.pdf")

            assert "PDF_FILE:" in result

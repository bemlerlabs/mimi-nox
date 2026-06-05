"""
PDF-Lesen Tests — GWT-Methodik, 3× Tiefe aus verschiedenen Blickwinkeln.

GIVEN: Eine PDF-Datei auf dem Dateisystem
WHEN:  read_file() damit aufgerufen wird
THEN:  Der Text-Inhalt wird korrekt zurückgegeben

GIVEN: Eine korrupte / nicht-PDF Datei mit .pdf Endung
WHEN:  read_file() damit aufgerufen wird
THEN:  Ein informativer Fehlertext wird zurückgegeben (kein Crash)

GIVEN: Das Tool-Schema für read_file
WHEN:  Es auf PDF-Unterstützung geprüft wird
THEN:  Die Beschreibung erwähnt PDF als unterstütztes Format
"""

import os
import struct
import tempfile
import asyncio
from pathlib import Path
import shutil
import subprocess

import pytest


# ── Blickwinkel 1: Unit — read_file mit echter PDF ────────────────────────────

class TestPDFReadUnitPerspective:
    """GIVEN a real minimal PDF, WHEN read_file called, THEN text extracted."""

    def _make_real_pdf(self, dest: Path, content: str = "MiMi PDF Test Content") -> Path:
        """Erstellt eine echte, pdfplumber-lesbare PDF via reportlab oder fpdf2."""
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 10, content)
            pdf.output(str(dest))
            return dest
        except ImportError:
            pass
        # Fallback: nutze pdfplumber + minimal-PDF-bytes (Latin-1 Text)
        import struct
        # Schreibe Minimal-PDF mit Text-Stream (UTF-compatible subset)
        minimal = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
            b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
            b"4 0 obj<</Length 44>>\nstream\nBT /F1 12 Tf 100 700 Td"
            b" (MiMi Test) Tj ET\nendstream\nendobj\n"
            b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
            b"xref\n0 6\n"
            b"0000000000 65535 f \n"
            b"0000000009 00000 n \n"
            b"0000000058 00000 n \n"
            b"0000000115 00000 n \n"
            b"0000000266 00000 n \n"
            b"0000000360 00000 n \n"
            b"trailer<</Size 6/Root 1 0 R>>\nstartxref\n441\n%%EOF\n"
        )
        dest.write_bytes(minimal)
        return dest

    @pytest.mark.asyncio
    async def test_given_pdf_when_read_file_then_returns_text(self):
        """
        GIVEN: Eine .pdf Datei liegt im erlaubten /tmp Pfad
        WHEN:  read_file() aufgerufen wird
        THEN:  Rückgabe ist ein nicht-leerer String (kein Crash)
        """
        from core.tools import read_file
        import tempfile

        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            pdf_path = Path(tmp) / "test.pdf"
            self._make_real_pdf(pdf_path)

            result = await read_file(str(pdf_path))

            # Perspektive 1: Typ-Check
            assert isinstance(result, str), "THEN: result muss ein String sein"
            # Perspektive 2: Nicht leer
            assert len(result.strip()) > 0, "THEN: result darf nicht leer sein"
            # Perspektive 3: Kein roher Binär-Müll
            assert "%PDF" not in result, "THEN: Keine rohen PDF-Bytes im Output"

    @pytest.mark.asyncio
    async def test_given_corrupt_pdf_when_read_file_then_no_crash(self):
        """
        GIVEN: Eine .pdf Datei mit ungültigem Inhalt (Nullbytes)
        WHEN:  read_file() aufgerufen wird
        THEN:  Kein Crash — informativer Fallback-Text als String
        """
        from core.tools import read_file
        import tempfile

        with tempfile.TemporaryDirectory(dir="/tmp") as tmp:
            corrupt_pdf = Path(tmp) / "corrupt.pdf"
            corrupt_pdf.write_bytes(b"\x00" * 100)

            result = await read_file(str(corrupt_pdf))

            # Perspektive 1: Kein Exception-Crash
            assert isinstance(result, str), "THEN: Auch Fehler muss String sein"
            # Perspektive 2: Inhalt erklärt das Problem
            assert len(result) > 0, "THEN: Fehler-String darf nicht leer sein"
            # Perspektive 3: Enthält Dateiname für User-Kontext
            assert "corrupt.pdf" in result or "Could not" in result or "no extractable" in result, (
                f"THEN: Fehler-String soll hilfreich sein, got: {result[:100]}"
            )


# ── Blickwinkel 2: Integration — Tool-Schema dokumentiert PDF-Support ─────────

class TestPDFToolSchemaIntegrationPerspective:
    """GIVEN the tool schema, WHEN inspected, THEN PDF is mentioned."""

    def test_given_tool_schema_when_read_file_checked_then_mentions_pdf(self):
        """
        GIVEN: Das Tool-Schema-System ist geladen
        WHEN:  Die Beschreibung von read_file abgerufen wird
        THEN:  PDF wird als unterstütztes Format erwähnt
        """
        from core.tools import get_tool_schemas
        schemas = get_tool_schemas()
        read_file_schema = next(
            (s for s in schemas if s.get("function", {}).get("name") == "read_file"),
            None
        )
        assert read_file_schema is not None, "THEN: read_file muss im Schema existieren"
        description = read_file_schema.get("function", {}).get("description", "")
        assert "pdf" in description.lower(), (
            f"THEN: Tool-Schema sollte 'pdf' erwähnen, got: {description[:200]}"
        )


# ── Blickwinkel 3: Systemebene — pyproject.toml hat pdfplumber ────────────────

class TestPDFDependencySystemPerspective:
    """GIVEN pyproject.toml, WHEN inspected, THEN pdfplumber is listed."""

    def test_given_pyproject_when_read_then_pdfplumber_in_dependencies(self):
        """
        GIVEN: pyproject.toml existiert
        WHEN:  Dependencies gelesen werden
        THEN:  pdfplumber ist als Abhängigkeit aufgelistet
        """
        import tomllib
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject.exists(), "THEN: pyproject.toml muss existieren"
        data = tomllib.loads(pyproject.read_text())
        deps = data.get("project", {}).get("dependencies", [])
        dep_names = [d.split(">=")[0].split("==")[0].split("[")[0].strip().lower()
                     for d in deps]
        assert "pdfplumber" in dep_names, (
            f"THEN: pdfplumber muss in dependencies sein, found: {dep_names}"
        )

    def test_given_venv_when_import_attempted_then_pdfplumber_importable(self):
        """
        GIVEN: Das virtuelle Environment ist aktiviert
        WHEN:  pdfplumber importiert wird
        THEN:  Import schlägt nicht fehl
        """
        try:
            import pdfplumber
        except ImportError:
            pytest.fail("THEN: pdfplumber muss importierbar sein — führe 'pip install pdfplumber' aus")


class TestPDFCreationPerspective:
    """GIVEN create_pdf writes a user-facing PDF, WHEN text is extracted, THEN glyphs are clean."""

    @pytest.mark.asyncio
    async def test_given_pdf_created_when_text_extracted_then_no_broken_glyphs(self):
        from core.tools import create_pdf
        import pdfplumber

        filename = "mimi_nox_pytest_glyph_check.pdf"
        path = Path.home() / "Downloads" / filename
        if path.exists():
            path.unlink()

        result = await create_pdf(
            title="MiMi Nox PDF Glyph Check",
            content="# Ergebnis\n- Robuste Bullet-Zeile\nNormaler Absatz",
            filename=filename,
        )

        assert result == f"PDF_FILE:{path}"
        assert path.exists()
        with pdfplumber.open(str(path)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        assert "MiMi Nox PDF Glyph Check" in text
        assert "MiMi Nox" in text
        assert "(cid:" not in text
        assert "Erstellt von n MiMi Nox" not in text

    @pytest.mark.asyncio
    async def test_given_high_end_report_when_created_then_sections_footer_and_clean_filename_exist(self):
        """
        GIVEN a user asks for a polished report with an unsafe filename
        WHEN create_pdf writes the file
        THEN the PDF has clean extractable sections and a sanitized local filename.
        """
        from core.tools import create_pdf
        import pdfplumber

        result = await create_pdf(
            title="MiMi Nox Projektanalyse",
            content="# Ist-Zustand\n## Risiken\n- Fehlende Tests\n## Nächste Schritte\n- pytest ausführen",
            filename="../MiMi Nox Projektanalyse 2026!!.pdf",
        )

        assert result.startswith("PDF_FILE:")
        output = Path(result.removeprefix("PDF_FILE:"))
        assert output.parent == Path.home() / "Downloads"
        assert output.name == "MiMi_Nox_Projektanalyse_2026.pdf"
        assert output.exists()

        with pdfplumber.open(str(output)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        assert "MiMi Nox Projektanalyse" in text
        assert "Ist-Zustand" in text
        assert "Risiken" in text
        assert "Nächste Schritte" in text
        assert "Seite 1" in text

    @pytest.mark.asyncio
    async def test_given_pdf_created_with_markdown_and_angle_brackets_then_text_is_clean_and_extractable(self):
        """
        GIVEN a report contains markdown emphasis, numbered actions, and angle brackets
        WHEN create_pdf writes the document
        THEN user content remains extractable and is not interpreted as broken markup.
        """
        from core.tools import create_pdf
        import pdfplumber

        result = await create_pdf(
            title="MiMi Nox Artifact Quality",
            content=(
                "# Executive Summary\n"
                "This PDF must keep **important** details and literal values like <project-id>.\n"
                "1. Validate layout\n"
                "2. Confirm extractable text\n"
                "### Source Notes\n"
                "- Generated from a local user request\n"
            ),
            filename="mimi-nox-artifact-quality.pdf",
        )

        output = Path(result.removeprefix("PDF_FILE:"))
        assert output.exists()

        with pdfplumber.open(str(output)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        assert "Executive Summary" in text
        assert "important" in text
        assert "<project-id>" in text
        assert "1. Validate layout" in text
        assert "2. Confirm extractable text" in text
        assert "Source Notes" in text
        assert "(cid:" not in text

    @pytest.mark.asyncio
    async def test_given_pdf_rendered_when_body_text_is_inspected_then_it_is_legible_on_white_page(self, tmp_path):
        """
        GIVEN a PDF is generated for a user-facing artifact
        WHEN the first page is rendered to a bitmap
        THEN body text is dark enough to be legible on the white page.
        """
        if not shutil.which("pdftoppm"):
            pytest.skip("pdftoppm is required for PDF render inspection")
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("Pillow is required for PDF render inspection")

        from core.tools import create_pdf

        result = await create_pdf(
            title="MiMi Nox Render Contrast",
            content=(
                "# Executive Summary\n"
                "This body line must render as dark, readable text on a white page.\n"
                "## Findings\n"
                "- Contrast is a user-facing artifact quality requirement.\n"
            ),
            filename="mimi-nox-render-contrast.pdf",
        )
        output = Path(result.removeprefix("PDF_FILE:"))
        render_prefix = tmp_path / "rendered"

        subprocess.run(
            ["pdftoppm", "-png", "-f", "1", "-l", "1", str(output), str(render_prefix)],
            check=True,
            capture_output=True,
            text=True,
        )
        image = Image.open(tmp_path / "rendered-1.png").convert("RGB")
        width, height = image.size
        crop = image.crop((int(width * 0.08), int(height * 0.16), int(width * 0.92), int(height * 0.42)))
        pixels = crop.tobytes()
        dark_pixels = sum(
            1
            for index in range(0, len(pixels), 3)
            if pixels[index] < 90 and pixels[index + 1] < 90 and pixels[index + 2] < 90
        )

        assert dark_pixels > 500

    @pytest.mark.asyncio
    async def test_given_pdf_template_brief_when_created_then_required_sections_are_inserted(self):
        """
        GIVEN the PDF tool supports high-end templates
        WHEN a brief is created with sparse content
        THEN the generated PDF includes the expected brief sections.
        """
        from core.tools import create_pdf
        import pdfplumber

        result = await create_pdf(
            title="Local AI Brief",
            content="MiMi Nox should stay strictly local.",
            filename="local-ai-brief-template.pdf",
            template="brief",
        )
        output = Path(result.removeprefix("PDF_FILE:"))

        with pdfplumber.open(str(output)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        assert "Executive Summary" in text
        assert "Key Points" in text
        assert "Source Notes" in text

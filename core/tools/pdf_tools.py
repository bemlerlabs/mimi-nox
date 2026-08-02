"""MiMi Nox – create_pdf tool (reportlab)."""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path


def _apply_pdf_template(content: str, template: str) -> str:
    text = (content or "").strip()
    lowered = text.lower()
    template = (template or "report").lower()
    sections: dict[str, list[str]] = {
        "report": ["# Executive Summary", "## Findings", "## Next Steps", "### Source Notes"],
        "brief": ["# Executive Summary", "## Key Points", "### Source Notes"],
        "analysis": ["# Executive Summary", "## Evidence", "## Risks", "## Recommendations", "### Appendix"],
        "checklist": ["# Executive Summary", "## Checklist", "## Acceptance Criteria", "### Source Notes"],
    }
    required = sections.get(template, sections["report"])
    missing = [section for section in required if section.lstrip("# ").lower() not in lowered]
    if not missing:
        return text
    inserted = [missing[0], text]
    for section in missing[1:]:
        inserted.extend(["", section, "- Not specified in the source input."])
    return "\n".join(inserted).strip()


async def create_pdf(
    title: str,
    content: str,
    filename: str = "nox_dokument.pdf",
    template: str = "report",
) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        from reportlab.lib.enums import TA_LEFT, TA_CENTER

        downloads = Path.home() / "Downloads"
        downloads.mkdir(exist_ok=True)
        safe_name = Path(filename).name
        safe_name = re.sub(r"\s+", "_", safe_name.strip())
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "", safe_name)
        safe_name = re.sub(r"_+", "_", safe_name).strip("._-")
        if not safe_name:
            safe_name = "nox_dokument.pdf"
        if not safe_name.lower().endswith(".pdf"):
            safe_name += ".pdf"
        out = downloads / safe_name

        doc = SimpleDocTemplate(
            str(out), pagesize=A4,
            rightMargin=20 * mm, leftMargin=20 * mm,
            topMargin=24 * mm, bottomMargin=24 * mm,
            title=title,
            author="MiMi Nox",
            subject="MiMi Nox report",
        )

        GREEN = colors.HexColor("#16a34a")
        GREEN_L = colors.HexColor("#22c55e")
        TEXT = colors.HexColor("#111827")
        MUTED = colors.HexColor("#6b7280")

        styles = getSampleStyleSheet()

        def S(name, **kw):
            return ParagraphStyle(name, **kw)

        s_title = S("T", fontSize=22, textColor=GREEN, spaceAfter=10, spaceBefore=0,
                     leading=28, fontName="Helvetica-Bold", alignment=TA_CENTER)
        s_h1 = S("H1", fontSize=15, textColor=GREEN_L, spaceAfter=4, spaceBefore=12,
                 fontName="Helvetica-Bold")
        s_h2 = S("H2", fontSize=12, textColor=GREEN_L, spaceAfter=3, spaceBefore=8,
                 fontName="Helvetica-Bold")
        s_h3 = S("H3", fontSize=10.5, textColor=GREEN_L, spaceAfter=3, spaceBefore=6,
                 fontName="Helvetica-Bold")
        s_body = S("B", fontSize=10, textColor=TEXT, spaceAfter=6, leading=16,
                   fontName="Helvetica")
        s_bullet = S("BL", fontSize=10, textColor=TEXT, spaceAfter=3, leading=15,
                     leftIndent=12, fontName="Helvetica",
                     bulletText="-", bulletIndent=4)
        s_numbered = S("NL", fontSize=10, textColor=TEXT, spaceAfter=3, leading=15,
                       leftIndent=12, fontName="Helvetica")
        s_meta = S("M", fontSize=8, textColor=MUTED, spaceAfter=12, alignment=TA_CENTER,
                   fontName="Helvetica")

        def _inline(text: str) -> str:
            escaped = html.escape(text, quote=False)
            return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", escaped)

        content = _apply_pdf_template(content, template)

        story = []
        story.append(Paragraph(title, s_title))
        story.append(Paragraph(f"Erstellt von MiMi Nox - {datetime.now().strftime('%d.%m.%Y %H:%M')}", s_meta))
        story.append(HRFlowable(width="100%", thickness=0.5, color=GREEN, spaceAfter=10))

        for line in content.splitlines():
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
            elif line.startswith("### "):
                story.append(Paragraph(_inline(line[4:]), s_h3))
            elif line.startswith("## "):
                story.append(Paragraph(_inline(line[3:]), s_h2))
            elif line.startswith("# "):
                story.append(Paragraph(_inline(line[2:]), s_h1))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph(_inline(line[2:]), s_bullet))
            elif re.match(r"^\d+\.\s+", line):
                story.append(Paragraph(_inline(line), s_numbered))
            else:
                story.append(Paragraph(_inline(line), s_body))

        def _footer(canvas, pdf_doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(MUTED)
            canvas.drawString(20 * mm, 12 * mm, "MiMi Nox")
            canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Seite {pdf_doc.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return f"PDF_FILE:{out}"

    except ImportError:
        return "[pdf: reportlab nicht installiert — 'pip install reportlab']"
    except Exception as e:
        return f"[pdf-Fehler: {e}]"

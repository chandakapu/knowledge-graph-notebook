import io
import os
import html as _html
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Register TrueType fonts (full Unicode support) ────────────────────────────
_FONTS_DIR = "C:/Windows/Fonts"

def _reg(alias: str, filename: str):
    path = os.path.join(_FONTS_DIR, filename)
    if os.path.isfile(path):
        pdfmetrics.registerFont(TTFont(alias, path))
        return True
    return False

_reg("Arial",       "arial.ttf")
_reg("Arial-Bold",  "arialbd.ttf")
_reg("Arial-Italic","ariali.ttf")

# Verify we can actually use them; fall back to Helvetica if not registered
def _font(name: str) -> str:
    """Return font name if registered, else a safe built-in fallback."""
    try:
        pdfmetrics.getFont(name)
        return name
    except Exception:
        fallbacks = {
            "Arial":        "Helvetica",
            "Arial-Bold":   "Helvetica-Bold",
            "Arial-Italic": "Helvetica-Oblique",
        }
        return fallbacks.get(name, "Helvetica")

F_REGULAR = _font("Arial")
F_BOLD    = _font("Arial-Bold")
F_ITALIC  = _font("Arial-Italic")


def _esc(value) -> str:
    """Convert to str and escape HTML special chars for use inside Paragraph markup."""
    raw = str(value) if value is not None else ""
    # Replace common Unicode punctuation that Latin-1 fonts can't handle
    raw = (raw
           .replace("\u2019", "'").replace("\u2018", "'")
           .replace("\u201c", '"').replace("\u201d", '"')
           .replace("\u2013", "-").replace("\u2014", "--")
           .replace("\u2026", "...").replace("\u00a0", " "))
    return _html.escape(raw)


def generate_summary_pdf(nodes: list, edges: list, documents: list) -> io.BytesIO:
    """
    Generates a structured, styled PDF summarising the workspace concepts,
    relationships, and analysed documents.
    Returns a BytesIO buffer containing the PDF.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54, leftMargin=54,
        topMargin=54,   bottomMargin=54,
    )

    # ── Colour palette ────────────────────────────────────────────────────────
    primary_color   = colors.HexColor("#8127cf")
    secondary_color = colors.HexColor("#346bf1")
    text_color      = colors.HexColor("#181c22")
    muted_color     = colors.HexColor("#4d4354")
    bg_light        = colors.HexColor("#f0ecf8")
    border_color    = colors.HexColor("#cfc2d6")

    # ── Paragraph styles ──────────────────────────────────────────────────────
    def _style(name, font=F_REGULAR, size=10, leading=14, color=text_color,
               parent_name="Normal", space_before=0, space_after=6, keep_next=False):
        styles = getSampleStyleSheet()
        return ParagraphStyle(
            name,
            parent=styles[parent_name],
            fontName=font,
            fontSize=size,
            leading=leading,
            textColor=color,
            spaceBefore=space_before,
            spaceAfter=space_after,
            keepWithNext=keep_next,
        )

    title_style      = _style("DocTitle",    F_BOLD,   26, 32, primary_color,   "Normal", space_after=12)
    subtitle_style   = _style("DocSubtitle", F_ITALIC, 12, 16, muted_color,     "Normal", space_after=22)
    section_heading  = _style("SecHead",     F_BOLD,   16, 20, secondary_color, "Normal", space_before=14, space_after=8,  keep_next=True)
    category_heading = _style("CatHead",     F_BOLD,   13, 16, primary_color,   "Normal", space_before=10, space_after=5,  keep_next=True)

    header_cell      = _style("HdrCell",     F_BOLD,    9, 12, secondary_color, "Normal", space_after=2)
    plain_cell       = _style("PlnCell",     F_REGULAR, 9, 12, text_color,      "Normal", space_after=2)
    concept_name_c   = _style("CncName",     F_BOLD,   10, 13, primary_color,   "Normal", space_after=2)
    concept_desc_c   = _style("CncDesc",     F_REGULAR, 9, 12, text_color,      "Normal", space_after=2)
    meta_style       = _style("Meta",        F_ITALIC,  8, 10, muted_color,     "Normal", space_after=0)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def p(text, style):
        """Wrap text in a Paragraph with safe HTML escaping."""
        return Paragraph(_esc(text), style)

    def base_ts():
        return TableStyle([
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.5, border_color),
            ("BACKGROUND",    (0, 0), (-1,  0), bg_light),
            ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ])

    # ── Story ─────────────────────────────────────────────────────────────────
    story = []

    story.append(Paragraph("langextract Summary", title_style))
    story.append(Paragraph("Active Workspace Knowledge Base &amp; Concept Synthesis", subtitle_style))
    story.append(Spacer(1, 8))

    # ── Part 1: Source Documents ──────────────────────────────────────────────
    if documents:
        story.append(Paragraph("Source Documents", section_heading))

        doc_rows = [[
            p("Filename",      header_cell),
            p("Timestamp",     header_cell),
            p("Size / Length", header_cell),
        ]]
        for d in documents:
            doc_rows.append([
                p(d.get("filename",  "Unnamed Document"), plain_cell),
                p(d.get("timestamp", "Unknown time"),     plain_cell),
                p(d.get("size",      "N/A"),              plain_cell),
            ])

        tbl = Table(doc_rows, colWidths=[230, 130, 140])
        tbl.setStyle(base_ts())
        story.append(tbl)
        story.append(Spacer(1, 18))

    # ── Part 2: Concepts & Definitions ───────────────────────────────────────
    if nodes:
        story.append(Paragraph("Extracted Concepts &amp; Definitions", section_heading))

        grouped: dict = {}
        for n in nodes:
            ntype = str(n.get("type") or "Concept")
            grouped.setdefault(ntype, []).append(n)

        for ntype, items in grouped.items():
            story.append(Paragraph(f"{_esc(ntype)}s", category_heading))

            rows = [[
                p("Concept / Entity",           header_cell),
                p("AI Synthesis & Description", header_cell),
            ]]
            for item in items:
                rows.append([
                    p(item.get("name") or "",         concept_name_c),
                    p(item.get("description") or "No description available.", concept_desc_c),
                ])

            tbl = Table(rows, colWidths=[150, 350])
            tbl.setStyle(base_ts())
            story.append(KeepTogether([tbl, Spacer(1, 14)]))

    # ── Part 3: Relationships ─────────────────────────────────────────────────
    if edges:
        story.append(Paragraph("Knowledge Graph Connections", section_heading))

        rows = [[
            p("Source Entity", header_cell),
            p("Relationship",  header_cell),
            p("Target Entity", header_cell),
            p("Confidence",    header_cell),
        ]]
        for e in edges:
            try:
                conf = float(e.get("confidence") or 0.5)
            except (TypeError, ValueError):
                conf = 0.5
            rows.append([
                p(e.get("source",   ""),           plain_cell),
                p(e.get("relation", "RELATED_TO"), plain_cell),
                p(e.get("target",   ""),           plain_cell),
                p(f"{int(conf * 100)}%",           plain_cell),
            ])

        tbl = Table(rows, colWidths=[150, 120, 150, 80])
        tbl.setStyle(base_ts())
        story.append(tbl)
        story.append(Spacer(1, 18))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Generated automatically by langextract AI. Private knowledge workspace.",
        meta_style,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer

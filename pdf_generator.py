from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from xml.sax.saxutils import escape
import os


def create_resume_pdf(data, output_path):
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.65*inch,
                            leftMargin=0.65*inch, topMargin=0.55*inch, bottomMargin=0.55*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="PersonName", parent=styles["Title"], fontName="Helvetica-Bold",
                              fontSize=22, leading=26, textColor=colors.HexColor("#172554"),
                              alignment=TA_LEFT, spaceAfter=5))
    styles.add(ParagraphStyle(name="ContactLine", parent=styles["Normal"], fontSize=8.5,
                              leading=12, textColor=colors.HexColor("#475569"), spaceAfter=10))
    styles.add(ParagraphStyle(name="SectionHead", parent=styles["Heading2"], fontSize=10.5,
                              leading=13, textColor=colors.HexColor("#1D4ED8"), spaceBefore=9,
                              spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodyCustom", parent=styles["BodyText"], fontSize=9,
                              leading=12.5, spaceAfter=3, textColor=colors.HexColor("#1F2937")))
    story = []
    name = escape(data.get("name", "Your Name") or "Your Name")
    story.append(Paragraph(name, styles["PersonName"]))
    contact = " &nbsp; | &nbsp; ".join(escape(data.get(k, "").strip()) for k in
        ["email", "phone", "location", "linkedin", "website"] if data.get(k, "").strip())
    if contact:
        story.append(Paragraph(contact, styles["ContactLine"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CBD5E1")))
    sections = [
        ("Professional Summary", "summary"),
        ("Education", "education"),
        ("Experience", "experience"),
        ("Projects", "projects"),
        ("Skills", "skills"),
        ("Certifications", "certifications"),
    ]
    for heading, key in sections:
        content = data.get(key, "").strip()
        if not content:
            continue
        story.append(Paragraph(escape(heading.upper()), styles["SectionHead"]))
        # Keep line breaks from the form; escape user-provided markup.
        for line in content.splitlines():
            line = line.strip()
            if line:
                story.append(Paragraph(escape(line).replace("•", "&#8226;"), styles["BodyCustom"]))
    doc.build(story)

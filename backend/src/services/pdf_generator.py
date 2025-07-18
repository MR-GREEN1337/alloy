import google.generativeai as genai
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime
import io
import json
from loguru import logger
from typing import Optional

from src.db import models
from src.core.settings import get_settings
from src.services.pdf_layouts import (
    get_pdf_styles,
    create_header,
    create_title_section,
    create_key_metrics_table,
    create_corporate_culture_section,
    create_financial_analysis_section,
    create_clashes_table,
    create_growth_table,
    create_brand_archetypes_section
)

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)


def create_report_pdf(
    report: models.Report, 
    llm_summary: dict,
    acquirer_favicon_bytes: Optional[bytes],
    target_favicon_bytes: Optional[bytes]
) -> bytes:
    """
    Assembles the PDF from static templates and LLM-generated content using reportlab.
    """
    logger.info(f"Assembling PDF for report {report.id} using ReportLab.")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer,
                            rightMargin=0.75*inch,
                            leftMargin=0.75*inch,
                            topMargin=0.75*inch,
                            bottomMargin=1.0*inch,
                            title=report.title) # Set the document title metadata
    
    styles = get_pdf_styles()
    story = []

    story.extend(create_header(styles))
    # THE FIX: Pass the favicon bytes to the title section layout function.
    story.extend(create_title_section(report, styles, acquirer_favicon_bytes, target_favicon_bytes))
    story.extend(create_key_metrics_table(report, doc.width, styles))
    
    # --- Main Qualitative Summaries ---
    story.append(Paragraph("Strategic Summary", styles['h2']))
    story.append(Paragraph(llm_summary.get("strategic_summary", "N/A").replace('\n', '<br/>'), styles['default']))
    story.append(Spacer(1, 0.3*inch))
    
    # Add the new sections
    story.extend(create_financial_analysis_section(llm_summary, styles))
    story.extend(create_corporate_culture_section(report, llm_summary, doc.width, styles, acquirer_favicon_bytes, target_favicon_bytes))
    story.extend(create_brand_archetypes_section(report, llm_summary, styles, acquirer_favicon_bytes, target_favicon_bytes))

    # --- Detailed Data Tables ---
    story.extend(create_clashes_table(report, doc.width, styles))
    story.extend(create_growth_table(report, doc.width, styles))
    
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        footer_text = f"Report ID: {report.id} | Confidential & Proprietary © {datetime.now().year} Alloy"
        canvas.drawCentredString(doc.width/2 + doc.leftMargin, 0.5 * inch, footer_text)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    logger.success(f"Successfully assembled PDF for report {report.id}.")
    return pdf_bytes
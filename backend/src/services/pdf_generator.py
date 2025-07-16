import google.generativeai as genai
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from datetime import datetime
import io
import json
from loguru import logger

from src.db import models
from src.core.settings import get_settings
from src.services.pdf_template import (
    get_pdf_styles,
    create_header,
    create_title_section,
    create_key_metrics_table,
    create_clashes_table,
    create_growth_table
)

settings = get_settings()
genai.configure(api_key=settings.GEMINI_API_KEY)

async def generate_qualitative_summary(report_data: dict) -> dict:
    """Uses Gemini to generate the strategic summary and brand archetypes."""
    logger.info("Generating qualitative summaries with Gemini...")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Create a simplified JSON for the LLM prompt, focusing on what it needs
    prompt_data = {
        "acquirer_brand": report_data["acquirer_brand"],
        "target_brand": report_data["target_brand"],
        "affinity_overlap_score": report_data["affinity_overlap_score"],
        "top_culture_clashes": [
            {"topic": c["topic"], "severity": c["severity"]} for c in report_data.get("culture_clashes", [])[:5]
        ],
        "top_growth_opportunities": [
            g["description"] for g in report_data.get("untapped_growths", [])[:5]
        ]
    }
    
    prompt = f"""
    You are an expert M&A analyst from a top-tier investment bank.
    Your task is to write the qualitative sections of a cultural due diligence report based on the provided data points.
    The tone should be professional, insightful, and data-driven.

    **Instructions:**
    1.  Write a "Strategic Summary" that synthesizes the provided data into a concise, executive-level overview. Highlight the key risks (from clashes) and opportunities (from growth areas).
    2.  Write a "Brand Archetype" for both the acquirer and the target. This should be a short, insightful paragraph for each, deducing their brand's 'personality' from the data.
    3.  Return the output as a single, valid JSON object with two keys: "strategic_summary" and "brand_archetypes". The "brand_archetypes" key should contain an object with "acquirer" and "target" keys.

    **Input Data:**
    ```json
    {json.dumps(prompt_data, indent=2)}
    ```

    **JSON Output:**
    """
    
    try:
        response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})
        logger.success("Successfully generated qualitative summary from Gemini.")
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Failed to generate qualitative summary with Gemini: {e}")
        # Fallback to a default summary in case of LLM failure
        return {
            "strategic_summary": "Analysis generated, but AI-powered qualitative summary could not be completed.",
            "brand_archetypes": {
                "acquirer": "Data unavailable.",
                "target": "Data unavailable."
            }
        }

def create_report_pdf(report: models.Report, llm_summary: dict) -> bytes:
    """
    Assembles the PDF from static templates and LLM-generated content using reportlab.
    """
    logger.info(f"Assembling PDF for report {report.id} using ReportLab.")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer,
                            rightMargin=0.75*inch,
                            leftMargin=0.75*inch,
                            topMargin=0.75*inch,
                            bottomMargin=1.0*inch) # Increased bottom margin for footer
    
    styles = get_pdf_styles()
    story = []

    # --- Static Header & Title ---
    story.extend(create_header(styles))
    story.extend(create_title_section(report, styles))
    
    # --- Static Key Metrics Table ---
    story.extend(create_key_metrics_table(report, doc.width, styles))
    
    # --- Dynamic LLM Content ---
    story.append(Paragraph("Strategic Summary", styles['h2']))
    story.append(Paragraph(llm_summary.get("strategic_summary", "N/A").replace('\n', '<br/>'), styles['default']))
    story.append(Spacer(1, 0.3*inch))
    
    story.append(Paragraph("Brand Archetypes", styles['h2']))
    archetypes = llm_summary.get("brand_archetypes", {})
    story.append(Paragraph(report.acquirer_brand, styles['h3']))
    story.append(Paragraph(archetypes.get('acquirer', 'N/A'), styles['default']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(report.target_brand, styles['h3']))
    story.append(Paragraph(archetypes.get('target', 'N/A'), styles['default']))
    story.append(Spacer(1, 0.3*inch))

    # --- Static Tables ---
    story.extend(create_clashes_table(report, doc.width, styles))
    story.extend(create_growth_table(report, doc.width, styles))
    
    # --- Footer ---
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
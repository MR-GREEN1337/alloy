from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, Image, Flowable
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from typing import Optional, List
import io

def get_pdf_styles():
    """Returns a dictionary of styled reportlab ParagraphStyle objects."""
    base_styles = getSampleStyleSheet()
    styles = {
        'default': ParagraphStyle(name='default', fontName='Helvetica', fontSize=10, leading=14),
        'h1': ParagraphStyle(name='h1', fontName='Helvetica-Bold', fontSize=20, alignment=TA_CENTER, spaceAfter=6),
        'h2': ParagraphStyle(name='h2', fontName='Helvetica-Bold', fontSize=14, spaceAfter=12, textColor=colors.HexColor('#0d47a1')),
        'h3': ParagraphStyle(name='h3', fontName='Helvetica-Bold', fontSize=11, spaceAfter=6),
        'center': ParagraphStyle(name='center', parent=base_styles['Normal'], alignment=TA_CENTER),
        'right': ParagraphStyle(name='right', parent=base_styles['Normal'], alignment=TA_RIGHT),
        'small_grey': ParagraphStyle(name='small_grey', fontSize=8, fontName='Helvetica', textColor=colors.grey),
    }
    styles['center_bold'] = ParagraphStyle(name='center_bold', parent=styles['center'], fontName='Helvetica-Bold')
    return styles

def _create_brand_header_flowable(brand_name: str, favicon_bytes: Optional[bytes], style: ParagraphStyle) -> List[Flowable]:
    """Creates a list of Flowables (Image + Text) for a brand header."""
    content = []
    if favicon_bytes:
        try:
            img = Image(io.BytesIO(favicon_bytes), width=12, height=12)
            img.hAlign = 'LEFT'
            content.append(img)
        except Exception: # Handle potential PIL errors for invalid image data
            pass
    content.append(Paragraph(f"<b>{brand_name}</b>", style))
    
    # Use a tiny table to force horizontal alignment
    table = Table([content], colWidths=[14, None])
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 2),
    ]))
    return [table]

def create_header(styles):
    """Creates the header section of the PDF."""
    return [
        Paragraph("Alloy - Cultural Due Diligence Report", styles['right']),
        Spacer(1, 0.1 * inch)
    ]

def create_title_section(report, styles, acquirer_favicon_bytes, target_favicon_bytes):
    """Creates the main title section of the PDF, now with favicons."""
    title_paragraph = Paragraph(report.title, styles['h1'])
    
    acquirer_image = Image(io.BytesIO(acquirer_favicon_bytes), width=24, height=24) if acquirer_favicon_bytes else Spacer(24, 24)
    target_image = Image(io.BytesIO(target_favicon_bytes), width=24, height=24) if target_favicon_bytes else Spacer(24, 24)

    title_data = [[acquirer_image, title_paragraph, target_image]]
    
    title_table = Table(title_data, colWidths=[0.5*inch, None, 0.5*inch])
    title_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
    ]))

    return [
        title_table,
        Paragraph(f"<i>Generated: {report.created_at.strftime('%B %d, %Y')}</i>", styles['center']),
        Spacer(1, 0.3 * inch)
    ]

def create_key_metrics_table(report, doc_width, styles):
    """Creates the top-line metrics table."""
    cultural_score_display = f"<font size=24>{report.analysis.cultural_compatibility_score:.0f}</font>/100" if report.analysis.cultural_compatibility_score > 0 else "<font size=24>--</font>/100"
    affinity_score_display = f"<font size=24>{report.analysis.affinity_overlap_score:.1f}%</font>" if report.analysis.affinity_overlap_score > 0 else "<font size=24>--</font>%"
    
    score_data = [
        [
            Paragraph(cultural_score_display, styles['center']),
            Paragraph(affinity_score_display, styles['center'])
        ],
        [
            Paragraph("<b>Cultural Compatibility Score</b>", styles['center_bold']),
            Paragraph("<b>Audience Affinity Overlap</b>", styles['center_bold'])
        ]
    ]
    table = Table(score_data, colWidths=[doc_width / 2.0, doc_width / 2.0], rowHeights=0.6 * inch)
    table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, colors.darkgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    return [table, Spacer(1, 0.3 * inch)]

def create_corporate_culture_section(report, llm_summary, doc_width, styles, acquirer_favicon_bytes, target_favicon_bytes):
    """Creates the corporate culture analysis section with favicons."""
    corporate_ethos = llm_summary.get("corporate_ethos", {})
    acquirer_ethos_text = corporate_ethos.get('acquirer_ethos', '')
    target_ethos_text = corporate_ethos.get('target_ethos', '')

    if not acquirer_ethos_text and not target_ethos_text:
        return []

    acquirer_ethos = acquirer_ethos_text.replace('\n', '<br/>')
    target_ethos = target_ethos_text.replace('\n', '<br/>')

    story = []
    story.append(Paragraph("Corporate Culture & Ethos", styles['h2']))
    
    ethos_data = [
        [_create_brand_header_flowable(report.acquirer_brand, acquirer_favicon_bytes, styles['h3']),
         _create_brand_header_flowable(report.target_brand, target_favicon_bytes, styles['h3'])],
        [Paragraph(acquirer_ethos, styles['default']), Paragraph(target_ethos, styles['default'])]
    ]
    ethos_table = Table(ethos_data, colWidths=[doc_width / 2.0 - 5, doc_width / 2.0 - 5])
    ethos_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 1, colors.lightgrey),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    return [ethos_table, Spacer(1, 0.3*inch)]

def create_brand_archetypes_section(report, llm_summary, styles, acquirer_favicon_bytes, target_favicon_bytes):
    """Creates the brand archetypes section with favicons."""
    story = []
    archetypes = llm_summary.get("brand_archetypes", {})
    
    story.append(Paragraph("Brand Archetypes", styles['h2']))
    story.extend(_create_brand_header_flowable(report.acquirer_brand, acquirer_favicon_bytes, styles['h3']))
    story.append(Paragraph(archetypes.get('acquirer_archetype', 'N/A'), styles['default']))
    story.append(Spacer(1, 0.1*inch))
    story.extend(_create_brand_header_flowable(report.target_brand, target_favicon_bytes, styles['h3']))
    story.append(Paragraph(archetypes.get('target_archetype', 'N/A'), styles['default']))
    story.append(Spacer(1, 0.3*inch))
    return story

def create_financial_analysis_section(llm_summary, styles):
    """Creates the financial and market analysis summary section."""
    financial_synthesis = llm_summary.get("financial_synthesis", "")
    if not financial_synthesis:
        return []
    
    story = []
    story.append(Paragraph("Financial & Market Analysis", styles['h2']))
    story.append(Paragraph(financial_synthesis.replace('\n', '<br/>'), styles['default']))
    story.append(Spacer(1, 0.3 * inch))
    return story

def create_clashes_table(report, doc_width, styles):
    """Creates the culture clashes table."""
    if not report.culture_clashes:
        return []
        
    header = Paragraph("Potential Culture Clashes", styles['h2'])
    
    data = [['Topic', 'Description', 'Severity']]
    for clash in report.culture_clashes:
        data.append([
            Paragraph(clash.topic, styles['default']),
            Paragraph(clash.description, styles['default']),
            Paragraph(clash.severity, styles['default'])
        ])
        
    table = Table(data, colWidths=[doc_width * 0.2, doc_width * 0.6, doc_width * 0.2])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263238')), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
    ]))
    return [header, table, Spacer(1, 0.3 * inch)]

def create_growth_table(report, doc_width, styles):
    """Creates the untapped growth opportunities table."""
    if not report.untapped_growths:
        return []

    header = Paragraph("Untapped Growth Opportunities", styles['h2'])

    data = [['Opportunity', 'Potential Impact']]
    for growth in report.untapped_growths:
        data.append([
            Paragraph(growth.description, styles['default']),
            Paragraph(f"<b>{growth.potential_impact_score}/10</b>", styles['center'])
        ])

    table = Table(data, colWidths=[doc_width * 0.8, doc_width * 0.2])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004d40')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f5f5f5'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
    ]))
    return [header, table, Spacer(1, 0.3 * inch)]
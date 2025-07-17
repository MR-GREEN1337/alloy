from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

def get_pdf_styles():
    """Returns a dictionary of styled reportlab ParagraphStyle objects."""
    # This is a temporary fix, styles should be defined once and passed around.
    # But for a quick fix, let's redefine it where needed.
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
    # Add center style specifically for key metrics if it's not inheriting correctly
    styles['center_bold'] = ParagraphStyle(name='center_bold', parent=styles['center'], fontName='Helvetica-Bold')

    return styles

def create_header(styles):
    """Creates the header section of the PDF."""
    return [
        Paragraph("Alloy - Cultural Due Diligence Report", styles['right']),
        Spacer(1, 0.1 * inch)
    ]

def create_title_section(report, styles):
    """Creates the main title section of the PDF."""
    return [
        Paragraph(report.title, styles['h1']),
        Paragraph(f"<i>Generated: {report.created_at.strftime('%B %d, %Y')}</i>", styles['center']),
        Spacer(1, 0.3 * inch)
    ]

def create_key_metrics_table(report, doc_width, styles):
    """Creates the top-line metrics table."""
    # CORE FIX: Use the passed-in styles dictionary correctly.
    score_data = [
        [
            Paragraph(f"<font size=24>{report.analysis.cultural_compatibility_score:.0f}</font>/100", styles['center']),
            Paragraph(f"<font size=24>{report.analysis.affinity_overlap_score:.1f}%</font>", styles['center'])
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
            Paragraph(clash.severity.value, styles['default'])
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
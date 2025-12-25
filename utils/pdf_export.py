import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def generer_pdf(donnees_plan):
    """
    Version simplifiée du PDF avec logo en français
    """
    buffer = io.BytesIO()
    
    # Configuration du document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    elements = []
    
    # ==================== STYLES ====================
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#2C3E50'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#3498DB'),
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=6
    )
    elements.append(Paragraph(
        '<font color="#3498DB" size="16"><b>✈ Safer fi dark</b></font><br/>' +
        '<font size="10">Votre assistant de planification de voyages</font>',
        ParagraphStyle('LogoStyle', alignment=TA_CENTER, spaceAfter=20)
    ))
    
    elements.append(Paragraph(
        f"<b>Plan de voyage : {donnees_plan.get('destination', 'Destination')}</b>",
        title_style
    ))
    
    elements.append(Paragraph('<hr/>', styles['Normal']))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Informations du voyage", subtitle_style))
    
    infos = [
        ['Destination', donnees_plan.get('destination', 'Non spécifiée')],
        ['Dates', f"{donnees_plan.get('depart_date', 'N/A')} → {donnees_plan.get('return_date', 'N/A')}"],
        ['Durée', f"{donnees_plan.get('duration_days', 'N/A')} jours"],
        ['Budget estimé', f"{donnees_plan.get('estimated_budget', {}).get('total', 'N/A'):,.0f} €".replace(',', ' ')],
        ['Origine', donnees_plan.get('origin', 'Non spécifiée')],
    ]
    
    info_table = Table(infos, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 30))
    
    # ==================== BUDGET ====================
    if donnees_plan.get('estimated_budget'):
        elements.append(Paragraph("Détail du budget", subtitle_style))
        
        budget = donnees_plan['estimated_budget']
        budget_items = [
            ['Vols', f"{budget.get('flight', 0):,.0f} €"],
            ['Hébergement', f"{budget.get('accommodation', 0):,.0f} €"],
            ['Nourriture', f"{budget.get('food', 0):,.0f} €"],
            ['Activités', f"{budget.get('activities', 0):,.0f} €"],
            ['Transport', f"{budget.get('transport', 0):,.0f} €"],
            ['Total', f"<b>{budget.get('total', 0):,.0f} €</b>"],
        ]
        
        budget_table = Table(budget_items, colWidths=[3*inch, 2*inch])
        budget_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -2), 0.25, colors.lightgrey),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#3498DB')),
            ('FONTNAME', (-1, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        elements.append(budget_table)
        elements.append(Spacer(1, 30))
    
    # ==================== ITINÉRAIRE ====================
    if donnees_plan.get('itinerary'):
        elements.append(PageBreak())
        elements.append(Paragraph("Itinéraire quotidien", subtitle_style))
        elements.append(Spacer(1, 10))
        
        for jour in donnees_plan['itinerary']:
            jour_text = f"<b>Jour {jour.get('day', '?')}: {jour.get('theme', 'Visite')}</b>"
            elements.append(Paragraph(jour_text, normal_style))
            
            activites = []
            if jour.get('morning'):
                activites.append(f"<b>Matin:</b> {', '.join(jour['morning'][:2])}")
            if jour.get('afternoon'):
                activites.append(f"<b>Après-midi:</b> {', '.join(jour['afternoon'][:2])}")
            if jour.get('evening'):
                activites.append(f"<b>Soir:</b> {', '.join(jour['evening'][:1])}")
            
            if activites:
                elements.append(Paragraph("<br/>".join(activites), normal_style))
            
            if jour.get('estimated_cost'):
                elements.append(Paragraph(f"<i>Coût estimé: {jour['estimated_cost']} €</i>", normal_style))
            
            elements.append(Spacer(1, 15))
    
    # ==================== RECOMMANDATIONS ====================
    if donnees_plan.get('recommendations'):
        elements.append(Paragraph("Recommandations", subtitle_style))
        
        for i, rec in enumerate(donnees_plan['recommendations'][:5], 1):
            elements.append(Paragraph(f"{i}. {rec}", normal_style))
            elements.append(Spacer(1, 4))
        
        elements.append(Spacer(1, 20))
    
    # ==================== CONSEILS ====================
    if donnees_plan.get('travel_tips'):
        elements.append(Paragraph("Conseils pratiques", subtitle_style))
        
        for tip in donnees_plan['travel_tips'][:3]:
            elements.append(Paragraph(f"• {tip}", normal_style))
            elements.append(Spacer(1, 2))
    
    # ==================== PIED DE PAGE ====================
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.grey)
        
        # Texte de pied de page
        footer_text = f"Généré par VOYAGE PLUS le {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        canvas.drawCentredString(A4[0]/2, 30, footer_text)
        
        # Numéro de page
        page_num = f"Page {canvas.getPageNumber()}"
        canvas.drawRightString(A4[0] - 72, 30, page_num)
        
        canvas.restoreState()
    
    # ==================== GÉNÉRATION ====================
    try:
        doc.build(
            elements,
            onFirstPage=add_footer,
            onLaterPages=add_footer
        )
    except Exception as e:
        # Fallback ultra simple
        print(f"Erreur PDF: {e}")
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica", 12)
        c.drawString(100, 750, "VOYAGE PLUS - Plan de Voyage")
        c.drawString(100, 730, f"Destination: {donnees_plan.get('destination', 'N/A')}")
        c.drawString(100, 710, f"Dates: {donnees_plan.get('depart_date', 'N/A')} → {donnees_plan.get('return_date', 'N/A')}")
        c.save()
    
    buffer.seek(0)
    return buffer


# ==================== FONCTION D'EXPORT SIMPLE ====================

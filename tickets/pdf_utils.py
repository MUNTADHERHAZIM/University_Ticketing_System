"""
حل بديل لتصدير PDF باستخدام ReportLab (أبسط من WeasyPrint)
Alternative PDF export solution using ReportLab (simpler than WeasyPrint)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import logging

logger = logging.getLogger('tickets')


@login_required
def export_ticket_pdf_reportlab(request, pk):
    """
    تصدير الطلب إلى PDF باستخدام ReportLab
    Export ticket to PDF using ReportLab
    """
    from tickets.models import Ticket
    
    ticket = get_object_or_404(Ticket, pk=pk)
    actions = ticket.actions.all().order_by('-created_at')
    
    # التحقق من الصلاحيات
    can_view = (
        ticket.created_by == request.user or
        ticket.assigned_to == request.user or
        request.user.role in ['admin', 'president', 'dean', 'head']
    )
    
    if not can_view:
        messages.error(request, 'ليس لديك صلاحية لتصدير هذا الطلب')
        return redirect('ticket_detail', pk=pk)
    
    # إنشاء PDF في الذاكرة
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    # قائمة العناصر
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#4c7eea'),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#333333'),
        spaceAfter=12,
    )
    
    normal_style = styles['Normal']
    
    # العنوان الرئيسي
    elements.append(Paragraph("تقرير الطلب", title_style))
    elements.append(Paragraph(f"رقم الطلب: #{ticket.id}", styles['Normal']))
    elements.append(Paragraph(f"تاريخ الطباعة: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # تحذير إذا كان الطلب متأخر
    if ticket.is_overdue:
        warning_style = ParagraphStyle(
            'Warning',
            parent=styles['Normal'],
            textColor=colors.red,
            fontSize=14,
            fontName='Helvetica-Bold',
        )
        elements.append(Paragraph(
            f"⚠️ تحذير: هذا الطلب متأخر بمقدار {ticket.hours_delayed:.1f} ساعة!",
            warning_style
        ))
        elements.append(Spacer(1, 12))
    
    # معلومات عامة
    elements.append(Paragraph("معلومات عامة", heading_style))
    
    info_data = [
        ['العنوان:', ticket.title],
        ['الحالة:', ticket.get_status_display()],
        ['الأولوية:', ticket.get_priority_display()],
        ['مستوى التصعيد:', ticket.get_escalation_level_display()],
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # الوصف
    elements.append(Paragraph("تفاصيل الطلب", heading_style))
    elements.append(Paragraph(ticket.description.replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 20))
    
    # معلومات الأطراف
    elements.append(Paragraph("معلومات الأطراف", heading_style))
    
    parties_data = [
        ['منشئ الطلب:', ticket.created_by.get_full_name()],
    ]
    
    if ticket.assigned_to:
        parties_data.append(['المعين له:', ticket.assigned_to.get_full_name()])
    
    if ticket.department:
        parties_data.append(['القسم:', ticket.department.name])
    
    parties_table = Table(parties_data, colWidths=[2*inch, 4*inch])
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 20))
    
    # التواريخ
    elements.append(Paragraph("التواريخ والمهل", heading_style))
    
    dates_data = [
        ['تاريخ الإنشاء:', ticket.created_at.strftime('%Y-%m-%d %H:%M')],
        ['الموعد النهائي (SLA):', ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')],
    ]
    
    if ticket.acknowledged_at:
        dates_data.append(['تاريخ التأكيد:', ticket.acknowledged_at.strftime('%Y-%m-%d %H:%M')])
    
    if ticket.resolved_at:
        dates_data.append(['تاريخ الحل:', ticket.resolved_at.strftime('%Y-%m-%d %H:%M')])
    
    if ticket.closed_at:
        dates_data.append(['تاريخ الإغلاق:', ticket.closed_at.strftime('%Y-%m-%d %H:%M')])
    
    dates_table = Table(dates_data, colWidths=[2*inch, 4*inch])
    dates_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 20))
    
    # ملاحظات الإغلاق
    if ticket.close_notes:
        elements.append(Paragraph("ملاحظات الإغلاق", heading_style))
        elements.append(Paragraph(ticket.close_notes.replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 20))
    
    # سجل الإجراءات
    elements.append(Paragraph("سجل الإجراءات", heading_style))
    
    if actions:
        actions_data = [['النوع', 'المستخدم', 'التاريخ']]
        for action in actions:
            actions_data.append([
                action.get_action_type_display(),
                action.user.get_full_name() if action.user else 'النظام',
                action.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        actions_table = Table(actions_data, colWidths=[2*inch, 2*inch, 2*inch])
        actions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4c7eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(actions_table)
    else:
        elements.append(Paragraph("لا توجد إجراءات مسجلة", normal_style))
    
    # التذييل
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1
    )
    elements.append(Paragraph("نظام إدارة الطلبات - قسم الحاسبة الإلكترونية", footer_style))
    elements.append(Paragraph(f"تم إنشاء هذا التقرير في {timezone.now().strftime('%Y-%m-%d %H:%M')}", footer_style))
    
    # بناء PDF
    doc.build(elements)
    
    # إعداد الاستجابة
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    logger.info(f'PDF (ReportLab) exported for ticket {ticket.id} by user {request.user.id}')
    
    return response

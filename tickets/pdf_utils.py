"""
PDF Export with Full Arabic Support using ReportLab
تصدير PDF مع دعم كامل للغة العربية باستخدام ReportLab
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
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import logging

logger = logging.getLogger('tickets')


def arabic_text(text):
    """
    تحويل النص العربي لتنسيق صحيح في PDF
    Convert Arabic text to proper PDF format
    """
    if not text:
        return ""
    reshaped_text = reshape(text)
    bidi_text = get_display(reshaped_text)
    return bidi_text


def register_arabic_fonts():
    """
    تسجيل الخطوط العربية
    Register Arabic fonts
    """
    import os
    font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'fonts', 'NotoNaskhArabic-Regular.ttf')
    try:
        pdfmetrics.registerFont(TTFont('Arabic', font_path))
        # إذا كان لديك خط بولد أضفه هنا بنفس الطريقة
        # pdfmetrics.registerFont(TTFont('Arabic-Bold', bold_font_path))
        return True
    except Exception as e:
        logger.warning(f"Could not register Arabic font: {e}. Using default fonts.")
        return False


@login_required
def export_ticket_pdf_reportlab(request, pk):
    """
    تصدير الطلب إلى PDF باستخدام ReportLab مع دعم العربية
    Export ticket to PDF using ReportLab with Arabic support
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
    
    # تسجيل الخطوط العربية
    has_arabic_font = register_arabic_fonts()
    font_name = 'Arabic' if has_arabic_font else 'Helvetica'
    font_name_bold = font_name  # استخدم نفس الخط العربي لجميع الأنماط
    
    # إنشاء PDF في الذاكرة
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=30
    )
    
    # قائمة العناصر
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # نمط العنوان الرئيسي
    title_style = ParagraphStyle(
        'ArabicTitle',
        fontName=font_name_bold,
        fontSize=22,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=20,
        alignment=TA_CENTER,
        leading=28
    )
    
    # نمط العناوين الفرعية
    heading_style = ParagraphStyle(
        'ArabicHeading',
        fontName=font_name_bold,
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=5,
        alignment=TA_RIGHT,
        leading=18,
        borderWidth=0,
        borderColor=colors.HexColor('#3498db'),
        borderPadding=5,
        backColor=colors.HexColor('#ecf0f1')
    )
    
    # نمط النص العادي
    normal_style = ParagraphStyle(
        'ArabicNormal',
        fontName=font_name,
        fontSize=11,
        textColor=colors.black,
        alignment=TA_RIGHT,
        leading=16,
        spaceAfter=8
    )
    
    # نمط التحذير
    warning_style = ParagraphStyle(
        'ArabicWarning',
        fontName=font_name_bold,
        fontSize=12,
        textColor=colors.HexColor('#e74c3c'),
        alignment=TA_CENTER,
        leading=16,
        backColor=colors.HexColor('#fadbd8'),
        borderWidth=1,
        borderColor=colors.HexColor('#e74c3c'),
        borderPadding=8
    )
    
    # نمط التذييل
    footer_style = ParagraphStyle(
        'ArabicFooter',
        fontName=font_name,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
        leading=12
    )
    
    # ==================== بناء المحتوى ====================
    
    # العنوان الرئيسي
    elements.append(Paragraph(arabic_text("تقرير الطلب"), title_style))
    elements.append(Spacer(1, 10))
    
    # معلومات الطلب الأساسية
    info_text = f"{arabic_text('رقم الطلب:')} #{ticket.id}"
    elements.append(Paragraph(info_text, normal_style))
    
    date_text = f"{arabic_text('تاريخ الطباعة:')} {timezone.now().strftime('%Y-%m-%d %H:%M')}"
    elements.append(Paragraph(date_text, normal_style))
    elements.append(Spacer(1, 15))
    
    # خط فاصل
    elements.append(Spacer(1, 5))
    
    # تحذير إذا كان الطلب متأخر
    if ticket.is_overdue:
        warning_text = arabic_text(f"⚠ تحذير: هذا الطلب متأخر بمقدار {ticket.hours_delayed:.1f} ساعة!")
        elements.append(Paragraph(warning_text, warning_style))
        elements.append(Spacer(1, 15))
    
    # ==================== معلومات عامة ====================
    elements.append(Paragraph(arabic_text("معلومات عامة"), heading_style))
    elements.append(Spacer(1, 8))
    
    info_data = [
        [arabic_text('العنوان:'), arabic_text(ticket.title)],
        [arabic_text('الحالة:'), arabic_text(ticket.get_status_display())],
        [arabic_text('الأولوية:'), arabic_text(ticket.get_priority_display())],
        [arabic_text('مستوى التصعيد:'), arabic_text(ticket.get_escalation_level_display())],
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 4.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#bdc3c7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), font_name_bold),
        ('FONTNAME', (1, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    
    # ==================== تفاصيل الطلب ====================
    elements.append(Paragraph(arabic_text("تفاصيل الطلب"), heading_style))
    elements.append(Spacer(1, 8))
    
    description_text = arabic_text(ticket.description.replace('\n', '<br/>'))
    elements.append(Paragraph(description_text, normal_style))
    elements.append(Spacer(1, 15))
    
    # ==================== معلومات الأطراف ====================
    elements.append(Paragraph(arabic_text("معلومات الأطراف"), heading_style))
    elements.append(Spacer(1, 8))
    
    parties_data = [
        [arabic_text('منشئ الطلب:'), arabic_text(ticket.created_by.get_full_name())],
    ]
    
    if ticket.assigned_to:
        parties_data.append([
            arabic_text('المعين له:'),
            arabic_text(ticket.assigned_to.get_full_name())
        ])
    
    if ticket.department:
        parties_data.append([
            arabic_text('القسم:'),
            arabic_text(ticket.department.name)
        ])
    
    parties_table = Table(parties_data, colWidths=[1.5*inch, 4.5*inch])
    parties_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#bdc3c7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), font_name_bold),
        ('FONTNAME', (1, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 15))
    
    # ==================== التواريخ والمهل ====================
    elements.append(Paragraph(arabic_text("التواريخ والمهل"), heading_style))
    elements.append(Spacer(1, 8))
    
    dates_data = [
        [arabic_text('تاريخ الإنشاء:'), ticket.created_at.strftime('%Y-%m-%d %H:%M')],
        [arabic_text('الموعد النهائي (SLA):'), ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')],
    ]
    
    if ticket.acknowledged_at:
        dates_data.append([
            arabic_text('تاريخ التأكيد:'),
            ticket.acknowledged_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    if ticket.resolved_at:
        dates_data.append([
            arabic_text('تاريخ الحل:'),
            ticket.resolved_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    if ticket.closed_at:
        dates_data.append([
            arabic_text('تاريخ الإغلاق:'),
            ticket.closed_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    dates_table = Table(dates_data, colWidths=[1.5*inch, 4.5*inch])
    dates_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#bdc3c7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -1), font_name_bold),
        ('FONTNAME', (1, 0), (1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 15))
    
    # ==================== ملاحظات الإغلاق ====================
    if ticket.close_notes:
        elements.append(Paragraph(arabic_text("ملاحظات الإغلاق"), heading_style))
        elements.append(Spacer(1, 8))
        close_notes_text = arabic_text(ticket.close_notes.replace('\n', '<br/>'))
        elements.append(Paragraph(close_notes_text, normal_style))
        elements.append(Spacer(1, 15))
    
    # ==================== سجل الإجراءات ====================
    elements.append(Paragraph(arabic_text("سجل الإجراءات"), heading_style))
    elements.append(Spacer(1, 8))
    
    if actions:
        actions_data = [[
            arabic_text('التاريخ'),
            arabic_text('المستخدم'),
            arabic_text('النوع')
        ]]
        
        for action in actions:
            user_name = action.user.get_full_name() if action.user else 'النظام'
            actions_data.append([
                action.created_at.strftime('%Y-%m-%d %H:%M'),
                arabic_text(user_name),
                arabic_text(action.get_action_type_display())
            ])
        
        actions_table = Table(actions_data, colWidths=[1.8*inch, 2.2*inch, 2*inch])
        actions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(actions_table)
    else:
        no_actions_text = arabic_text("لا توجد إجراءات مسجلة")
        elements.append(Paragraph(no_actions_text, normal_style))
    
    # ==================== التذييل ====================
    elements.append(Spacer(1, 30))
    
    footer_text1 = arabic_text("نظام إدارة الطلبات - قسم الحاسبة الإلكترونية")
    elements.append(Paragraph(footer_text1, footer_style))
    

    # ==================== بناء PDF ====================
    try:
        doc.build(elements)
    except Exception as e:
        logger.error(f'Error building PDF for ticket {ticket.id}: {str(e)}')
        messages.error(request, 'حدث خطأ أثناء إنشاء ملف PDF')
        return redirect('ticket_detail', pk=pk)
    
    # ==================== إعداد الاستجابة ====================
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'ticket_{ticket.id}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    logger.info(f'PDF exported successfully for ticket {ticket.id} by user {request.user.username}')
    
    return response

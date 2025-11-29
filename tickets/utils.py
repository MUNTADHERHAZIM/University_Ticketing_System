"""
وظائف مساعدة لنظام الطلبات
Utility functions for the ticketing system
"""
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger('tickets')


def send_ticket_update_email(ticket, action_type, user=None):
    """
    إرسال بريد إلكتروني عند تحديث الطلب
    Send email notification when ticket is updated
    
    Args:
        ticket: كائن الطلب (Ticket object)
        action_type: نوع الإجراء (Action type)
        user: المستخدم الذي قام بالإجراء (User who performed the action)
    """
    try:
        # تحديد المستلمين
        recipients = []
        
        # إضافة منشئ الطلب
        if ticket.created_by.email:
            recipients.append(ticket.created_by.email)
        
        # إضافة المعينين للطلب
        if ticket.assigned_to and ticket.assigned_to.email:
            if ticket.assigned_to.email not in recipients:
                recipients.append(ticket.assigned_to.email)
        
        # إضافة المعينين المتعددين
        for assigned_user in ticket.assigned_to_users.all():
            if assigned_user.email and assigned_user.email not in recipients:
                recipients.append(assigned_user.email)
        
        if not recipients:
            logger.warning(f"No recipients found for ticket {ticket.id}")
            return
        
        # إنشاء سياق القالب
        context = {
            'ticket': ticket,
            'action_type': action_type,
            'user': user,
            'site_url': 'http://localhost:8000',  # يجب تغييره في الإنتاج
        }
        
        # رندر قالب HTML
        html_message = render_to_string('emails/ticket_update.html', context)
        plain_message = strip_tags(html_message)
        
        # تحديد الموضوع بناءً على نوع الإجراء
        subject_map = {
            'created': f'طلب جديد: {ticket.title}',
            'assigned': f'تم تعيين طلب لك: {ticket.title}',
            'acknowledged': f'تم تأكيد الطلب: {ticket.title}',
            'escalated': f'تم تصعيد الطلب: {ticket.title}',
            'resolved': f'تم حل الطلب: {ticket.title}',
            'closed': f'تم إغلاق الطلب: {ticket.title}',
            'commented': f'تعليق جديد على الطلب: {ticket.title}',
        }
        
        subject = subject_map.get(action_type, f'تحديث على الطلب: {ticket.title}')
        
        # إرسال البريد
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"Email sent for ticket {ticket.id} - action: {action_type}")
        
    except Exception as e:
        logger.error(f"Error sending email for ticket {ticket.id}: {str(e)}")


def send_ticket_assigned_email(ticket, assigned_to):
    """
    إرسال بريد عند تعيين الطلب لمستخدم
    Send email when ticket is assigned to a user
    """
    send_ticket_update_email(ticket, 'assigned', assigned_to)


def send_ticket_closed_email(ticket, closed_by):
    """
    إرسال بريد عند إغلاق الطلب
    Send email when ticket is closed
    """
    send_ticket_update_email(ticket, 'closed', closed_by)

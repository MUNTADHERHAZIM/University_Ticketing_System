"""
إشارات نظام الطلبات - لإرسال الإشعارات والبريد الإلكتروني
Signals for ticket system - to send notifications and emails
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Ticket, TicketAction
from .utils import send_ticket_update_email
import logging

logger = logging.getLogger('tickets')


@receiver(post_save, sender=Ticket)
def ticket_saved(sender, instance, created, **kwargs):
    """
    يتم تشغيلها عند حفظ طلب (إنشاء أو تحديث)
    Triggered when a ticket is saved (created or updated)
    """
    if created:
        # طلب جديد
        send_ticket_update_email(instance, 'created', instance.created_by)
        logger.info(f"New ticket created: {instance.id}")
    else:
        # تحديث طلب موجود
        # سيتم إرسال البريد من خلال TicketAction
        pass


@receiver(post_save, sender=TicketAction)
def ticket_action_created(sender, instance, created, **kwargs):
    """
    يتم تشغيلها عند إنشاء إجراء جديد على الطلب
    Triggered when a new action is created on a ticket
    """
    if created:
        # إرسال بريد حسب نوع الإجراء
        send_ticket_update_email(
            instance.ticket,
            instance.action_type,
            instance.user
        )
        logger.info(f"Ticket action created: {instance.action_type} for ticket {instance.ticket.id}")

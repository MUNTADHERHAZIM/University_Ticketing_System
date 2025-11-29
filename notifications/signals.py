from django.db.models.signals import post_save
from django.dispatch import receiver
from tickets.models import Ticket, TicketAction
from .models import Notification
import logging

logger = logging.getLogger('tickets')


@receiver(post_save, sender=Ticket)
def ticket_created_notification(sender, instance, created, **kwargs):
    """
    إشعار عند إنشاء طلب جديد
    """
    if created:
        # إشعار للمعين له
        if instance.assigned_to:
            Notification.create_notification(
                user=instance.assigned_to,
                notification_type='new_ticket',
                title='طلب جديد تم تعيينه لك',
                message=f'تم تعيين الطلب "{instance.title}" لك من قبل {instance.created_by.get_full_name()}',
                ticket=instance
            )
            logger.info(f'Notification sent to {instance.assigned_to} for new ticket #{instance.id}')


@receiver(post_save, sender=TicketAction)
def ticket_action_notification(sender, instance, created, **kwargs):
    """
    إشعار عند حدوث إجراء على الطلب
    """
    if not created:
        return
    
    ticket = instance.ticket
    action_type = instance.action_type
    
    # إشعار حسب نوع الإجراء
    if action_type == 'commented':
        # إشعار لمالك الطلب والمعين له
        recipients = set()
        if ticket.created_by:
            recipients.add(ticket.created_by)
        if ticket.assigned_to:
            recipients.add(ticket.assigned_to)
        
        # إزالة الشخص الذي أضاف التعليق
        if instance.user in recipients:
            recipients.remove(instance.user)
        
        for user in recipients:
            Notification.create_notification(
                user=user,
                notification_type='ticket_commented',
                title='تعليق جديد على الطلب',
                message=f'{instance.user.get_full_name()} علّق على الطلب "{ticket.title}"',
                ticket=ticket
            )
    
    elif action_type == 'escalated':
        # إشعار للمستوى الأعلى
        if ticket.escalation_level == 'head' and ticket.department:
            # إشعار لرئيس القسم
            heads = ticket.department.customuser_set.filter(role='head')
            for head in heads:
                Notification.create_notification(
                    user=head,
                    notification_type='ticket_escalated',
                    title='طلب تم تصعيده',
                    message=f'تم تصعيد الطلب "{ticket.title}" إليك بسبب التأخير',
                    ticket=ticket
                )
        elif ticket.escalation_level in ['dean', 'president']:
            # إشعار للعميد أو رئيس الجامعة
            from accounts.models import CustomUser
            role = ticket.escalation_level
            users = CustomUser.objects.filter(role=role)
            for user in users:
                Notification.create_notification(
                    user=user,
                    notification_type='ticket_escalated',
                    title='⚠️ تصعيد عاجل',
                    message=f'تم تصعيد الطلب الحرج "{ticket.title}" إليك - تأخير {ticket.hours_delayed:.1f} ساعة',
                    ticket=ticket
                )
    
    elif action_type == 'closed':
        # إشعار لمنشئ الطلب
        if ticket.created_by:
            Notification.create_notification(
                user=ticket.created_by,
                notification_type='ticket_closed',
                title='✅ تم إغلاق الطلب',
                message=f'تم إغلاق الطلب "{ticket.title}" من قبل {instance.user.get_full_name() if instance.user else "النظام"}',
                ticket=ticket
            )

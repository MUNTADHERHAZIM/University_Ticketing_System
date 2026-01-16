from django.db.models.signals import post_save
from django.dispatch import receiver
from tickets.models import Ticket, TicketAction, TicketAcknowledgment
from .models import Notification
from accounts.models import CustomUser
import logging

logger = logging.getLogger('tickets')


def get_all_assigned_users(ticket):
    """
    الحصول على جميع المستخدمين المعينين للطلب
    يشمل: المعين المباشر، المعينين المتعددين، أعضاء الأقسام المعنية
    """
    users = set()
    
    # 1. المعين المباشر
    if ticket.assigned_to:
        users.add(ticket.assigned_to)
    
    # 2. المعينين المتعددين
    for user in ticket.assigned_to_users.all():
        users.add(user)
    
    # 3. أعضاء الأقسام المعنية (الموظفين ورؤساء الأقسام)
    for dept in ticket.departments.all():
        dept_users = CustomUser.objects.filter(
            department=dept,
            role__in=['employee', 'head']
        )
        for user in dept_users:
            users.add(user)
    
    return users


def get_upper_management_users():
    """
    الحصول على جميع مستخدمي الإدارة العليا
    """
    return CustomUser.objects.filter(
        role__in=['admin', 'president', 'admin_assistant', 'academic_assistant']
    )


@receiver(post_save, sender=Ticket)
def ticket_created_notification(sender, instance, created, **kwargs):
    """
    إشعار شامل عند إنشاء طلب جديد
    يُرسل لجميع المعينين والأقسام المعنية
    """
    if created:
        assigned_users = get_all_assigned_users(instance)
        
        for user in assigned_users:
            # لا نرسل إشعار لمنشئ الطلب
            if user == instance.created_by:
                continue
                
            Notification.create_notification(
                user=user,
                notification_type='new_ticket',
                title='📋 طلب جديد تم تعيينه لك',
                message=f'تم تعيين الطلب "{instance.title}" لك من قبل {instance.created_by.get_full_name()}. الأولوية: {instance.get_priority_display()}',
                ticket=instance
            )
            logger.info(f'Notification sent to {user} for new ticket #{instance.id}')
        
        # إشعار الإدارة العليا للطلبات الحرجة
        if instance.priority == 'critical':
            for admin_user in get_upper_management_users():
                if admin_user != instance.created_by:
                    Notification.create_notification(
                        user=admin_user,
                        notification_type='new_ticket',
                        title='🚨 طلب حرج جديد',
                        message=f'تم إنشاء طلب حرج: "{instance.title}" - يتطلب متابعة فورية',
                        ticket=instance
                    )


@receiver(post_save, sender=TicketAction)
def ticket_action_notification(sender, instance, created, **kwargs):
    """
    إشعار شامل عند حدوث إجراء على الطلب
    """
    if not created:
        return
    
    ticket = instance.ticket
    action_type = instance.action_type
    
    # إشعار حسب نوع الإجراء
    if action_type == 'commented':
        # إشعار لمالك الطلب وجميع المعينين
        recipients = set()
        if ticket.created_by:
            recipients.add(ticket.created_by)
        
        assigned_users = get_all_assigned_users(ticket)
        recipients.update(assigned_users)
        
        # إزالة الشخص الذي أضاف التعليق
        if instance.user in recipients:
            recipients.remove(instance.user)
        
        for user in recipients:
            Notification.create_notification(
                user=user,
                notification_type='ticket_commented',
                title='💬 تعليق جديد على الطلب',
                message=f'{instance.user.get_full_name()} علّق على الطلب "{ticket.title}"',
                ticket=ticket
            )
    
    elif action_type == 'escalated':
        # إشعار للمستوى الأعلى
        if ticket.escalation_level == 'head' and ticket.department:
            # إشعار لرئيس القسم
            heads = ticket.department.users.filter(role='head')
            for head in heads:
                Notification.create_notification(
                    user=head,
                    notification_type='ticket_escalated',
                    title='⬆️ طلب تم تصعيده',
                    message=f'تم تصعيد الطلب "{ticket.title}" إليك بسبب التأخير',
                    ticket=ticket
                )
        elif ticket.escalation_level in ['dean', 'president']:
            # إشعار للعميد أو رئيس الجامعة
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
        
        # إشعار الإدارة العليا دائماً عند التصعيد
        for admin_user in get_upper_management_users():
            Notification.create_notification(
                user=admin_user,
                notification_type='ticket_escalated',
                title='📊 تصعيد طلب',
                message=f'تم تصعيد الطلب "{ticket.title}" إلى مستوى: {ticket.get_escalation_level_display()}',
                ticket=ticket
            )
    
    elif action_type == 'closed':
        # إشعار لمنشئ الطلب وجميع المعينين
        recipients = set()
        if ticket.created_by:
            recipients.add(ticket.created_by)
        
        assigned_users = get_all_assigned_users(ticket)
        recipients.update(assigned_users)
        
        if instance.user in recipients:
            recipients.remove(instance.user)
        
        for user in recipients:
            Notification.create_notification(
                user=user,
                notification_type='ticket_closed',
                title='✅ تم إغلاق الطلب',
                message=f'تم إغلاق الطلب "{ticket.title}" من قبل {instance.user.get_full_name() if instance.user else "النظام"}',
                ticket=ticket
            )
    
    elif action_type == 'resolved':
        # إشعار عند حل الطلب
        if ticket.created_by and ticket.created_by != instance.user:
            Notification.create_notification(
                user=ticket.created_by,
                notification_type='ticket_closed',
                title='🎉 تم حل الطلب',
                message=f'تم حل الطلب "{ticket.title}" - يرجى مراجعته وتأكيد الإغلاق',
                ticket=ticket
            )


@receiver(post_save, sender=TicketAcknowledgment)
def acknowledgment_notification(sender, instance, created, **kwargs):
    """
    إشعار عند إقرار استلام الطلب
    يُرسل لمنشئ الطلب والمعينين الآخرين والإدارة العليا
    """
    if created:
        ticket = instance.ticket
        acknowledger = instance.user
        
        # إشعار لمنشئ الطلب
        if ticket.created_by and ticket.created_by != acknowledger:
            Notification.create_notification(
                user=ticket.created_by,
                notification_type='ticket_acknowledged',
                title='✔️ تم استلام طلبك',
                message=f'قام {acknowledger.get_full_name()} بتأكيد استلام الطلب "{ticket.title}"',
                ticket=ticket
            )
        
        # إشعار للمعينين الآخرين الذين لم يقروا بعد
        assigned_users = get_all_assigned_users(ticket)
        acknowledged_users = set(ticket.acknowledgments.values_list('user_id', flat=True))
        
        pending_users = [u for u in assigned_users if u.id not in acknowledged_users and u != acknowledger]
        
        for user in pending_users:
            Notification.create_notification(
                user=user,
                notification_type='ticket_acknowledged',
                title='📝 إقرار استلام من زميل',
                message=f'قام {acknowledger.get_full_name()} بالإقرار باستلام الطلب "{ticket.title}" - في انتظار إقرارك',
                ticket=ticket
            )
        
        # إحصاء الإقرارات
        total_assigned = len(assigned_users)
        total_acknowledged = ticket.acknowledgments.count()
        
        logger.info(f'Acknowledgment recorded: {acknowledger} for ticket #{ticket.id} ({total_acknowledged}/{total_assigned})')

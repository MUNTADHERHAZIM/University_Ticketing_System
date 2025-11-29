from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q, Count
from datetime import timedelta
from .models import Ticket, TicketAction
from accounts.models import CustomUser, PenaltyPoints, Department
import logging

# Initialize logger
logger = logging.getLogger('celery')


@shared_task
def check_sla_violations():
    """
    مهمة تعمل كل 10 دقائق للتحقق من انتهاكات SLA
    """
    logger.info('Starting SLA violations check')
    now = timezone.now()
    
    # البحث عن جميع التذاكر التي تجاوزت الموعد النهائي وليست محلولة
    violated_tickets = Ticket.objects.filter(
        Q(status__in=['new', 'pending_ack', 'in_progress']) &
        Q(sla_deadline__lt=now)
    ).exclude(status='violated')
    
    count = violated_tickets.count()
    logger.info(f'Found {count} tickets violating SLA')
    
    for ticket in violated_tickets:
        # تحديث الحالة إلى مخالف
        ticket.status = 'violated'
        ticket.save()
        
        # تسجيل الإجراء
        TicketAction.objects.create(
            ticket=ticket,
            action_type='escalated',
            notes=f'تم التصعيد تلقائياً بسبب تجاوز المهلة. تأخير: {ticket.hours_delayed:.1f} ساعة'
        )
        
        # إضافة نقاط جزائية للقسم المسؤول
        PenaltyPoints.objects.create(
            department=ticket.department,
            user=ticket.assigned_to,
            points=1,
            reason=f'تجاوز مهلة الطلب: {ticket.title}'
        )
        
        logger.warning(f'Ticket #{ticket.id} violated SLA - {ticket.hours_delayed:.1f}h delay')
        
        # التصعيد التلقائي
        escalate_ticket(ticket)
    
    logger.info(f'Completed SLA check - processed {count} violations')
    return f'تم معالجة {count} تذكرة مخالفة'



def escalate_ticket(ticket):
    """
    تصعيد التذكرة للمستوى الأعلى
    """
    escalation_map = {
        'none': 'head',
        'head': 'dean',
        'dean': 'president',
    }
    
    current_level = ticket.escalation_level
    next_level = escalation_map.get(current_level)
    
    if next_level:
        ticket.escalation_level = next_level
        ticket.save()
        
        # إرسال إشعار للمستوى الأعلى
        notify_escalation(ticket, next_level)


def notify_escalation(ticket, level):
    """
    إرسال إشعار بالتصعيد
    """
    # البحث عن المستخدمين في المستوى المستهدف
    role_map = {
        'head': 'head',
        'dean': 'dean',
        'president': 'president',
    }
    
    target_role = role_map.get(level)
    if not target_role:
        return
    
    # إيجاد المستخدمين المناسبين
    if target_role == 'head':
        recipients = CustomUser.objects.filter(
            department=ticket.department,
            role='head'
        )
    else:
        recipients = CustomUser.objects.filter(role=target_role)
    
    # إرسال بريد إلكتروني
    for recipient in recipients:
        if recipient.email:
            send_mail(
                subject=f'تنبيه: تصعيد طلب - {ticket.title}',
                message=f'''
تم تصعيد الطلب التالي إلى مستواك:

العنوان: {ticket.title}
القسم: {ticket.department.name}
الأولوية: {ticket.get_priority_display()}
تأخير: {ticket.hours_delayed:.1f} ساعة

الرجاء اتخاذ الإجراء اللازم فوراً.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@university.edu',
                recipient_list=[recipient.email],
                fail_silently=True,
            )


@shared_task
def auto_reassign_tickets():
    """
    إعادة تعيين التذاكر التي تأخرت أكثر من المدة المحددة
    """
    threshold_hours = settings.AUTO_REASSIGN_AFTER_HOURS
    threshold_time = timezone.now() - timedelta(hours=threshold_hours)
    
    # البحث عن التذاكر المتأخرة جداً
    overdue_tickets = Ticket.objects.filter(
        status__in=['new', 'pending_ack', 'in_progress'],
        created_at__lt=threshold_time,
        assigned_to__isnull=False
    )
    
    reassigned_count = 0
    
    for ticket in overdue_tickets:
        # البحث عن موظف بديل في نفس القسم
        current_assignee = ticket.assigned_to
        
        alternative_users = CustomUser.objects.filter(
            department=ticket.department,
            role__in=['employee', 'head'],
            is_active=True
        ).exclude(id=current_assignee.id if current_assignee else None)
        
        if alternative_users.exists():
            # اختيار الموظف الذي لديه أقل عدد من التذاكر النشطة
            new_assignee = alternative_users.annotate(
                active_tickets_count=Count(
                    'assigned_tickets',
                    filter=Q(assigned_tickets__status__in=['new', 'pending_ack', 'in_progress'])
                )
            ).order_by('active_tickets_count').first()
            
            old_assignee = ticket.assigned_to
            ticket.assigned_to = new_assignee
            ticket.save()
            
            # تسجيل الإجراء
            TicketAction.objects.create(
                ticket=ticket,
                action_type='reassigned',
                user=new_assignee,
                notes=f'تم إعادة التعيين تلقائياً من {old_assignee} بسبب التأخير الزائد'
            )
            
            reassigned_count += 1
    
    return f'تم إعادة تعيين {reassigned_count} تذكرة'


@shared_task
def send_daily_report():
    """
    إرسال تقرير يومي للإدارة العليا
    """
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    
    # إحصائيات عامة
    total_tickets = Ticket.objects.count()
    new_tickets_today = Ticket.objects.filter(created_at__gte=yesterday).count()
    violated_tickets = Ticket.objects.filter(status='violated').count()
    pending_tickets = Ticket.objects.filter(status__in=['new', 'pending_ack', 'in_progress']).count()
    
    # أسوأ الأقسام أداءً
    departments_performance = Department.objects.annotate(
        violated_count=Count('tickets', filter=Q(tickets__status='violated')),
        pending_count=Count('tickets', filter=Q(tickets__status__in=['new', 'pending_ack', 'in_progress']))
    ).order_by('-violated_count')[:5]
    
    # الموظفون الأقل استجابة
    worst_employees = CustomUser.objects.annotate(
        violated_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='violated'))
    ).filter(violated_count__gt=0).order_by('-violated_count')[:5]
    
    # بناء التقرير
    report = f'''
تقرير أداء نظام الطلبات اليومي
التاريخ: {now.strftime('%Y-%m-%d')}

=== الإحصائيات العامة ===
إجمالي الطلبات: {total_tickets}
طلبات جديدة اليوم: {new_tickets_today}
طلبات مخالفة (تجاوزت المهلة): {violated_tickets}
طلبات معلقة: {pending_tickets}

=== الأقسام الأكثر تأخيراً ===
'''
    
    for dept in departments_performance:
        report += f'- {dept.name}: {dept.violated_count} طلب مخالف, {dept.pending_count} طلب معلق\n'
    
    report += '\n=== الموظفون الأقل استجابة ===\n'
    for emp in worst_employees:
        report += f'- {emp.get_full_name()} ({emp.department}): {emp.violated_count} طلب مخالف\n'
    
    # إرسال التقرير للإدارة العليا
    admins = CustomUser.objects.filter(role__in=['president', 'dean', 'admin'])
    
    for admin in admins:
        if admin.email:
            send_mail(
                subject=f'تقرير أداء نظام الطلبات - {now.strftime("%Y-%m-%d")}',
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@university.edu',
                recipient_list=[admin.email],
                fail_silently=True,
            )
    
    return 'تم إرسال التقرير اليومي'

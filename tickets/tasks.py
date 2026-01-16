from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q, Count, Avg, F
from datetime import timedelta
from .models import Ticket, TicketAction, TicketAcknowledgment
from accounts.models import CustomUser, PenaltyPoints, Department
import logging

# Initialize logger
logger = logging.getLogger('celery')


@shared_task
def check_sla_violations():
    """
    مهمة تعمل كل 5 دقائق للتحقق من انتهاكات SLA
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
        
        # إضافة نقاط جزائية حسب مدة التأخير
        delay_hours = ticket.hours_delayed
        penalty_points = calculate_penalty_points(delay_hours)
        
        PenaltyPoints.objects.create(
            department=ticket.department,
            user=ticket.assigned_to,
            points=penalty_points,
            reason=f'تجاوز مهلة الطلب: {ticket.title} - تأخير {delay_hours:.1f} ساعة'
        )
        
        logger.warning(f'Ticket #{ticket.id} violated SLA - {ticket.hours_delayed:.1f}h delay - {penalty_points} penalty points')
        
        # التصعيد التلقائي
        escalate_ticket(ticket)
    
    logger.info(f'Completed SLA check - processed {count} violations')
    return f'تم معالجة {count} تذكرة مخالفة'


def calculate_penalty_points(delay_hours):
    """
    حساب النقاط الجزائية حسب مدة التأخير
    """
    if delay_hours < 4:
        return 1
    elif delay_hours < 8:
        return 3
    elif delay_hours < 24:
        return 5
    else:
        return 10


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
                subject=f'⚠️ تنبيه: تصعيد طلب - {ticket.title}',
                message=f'''
تم تصعيد الطلب التالي إلى مستواك:

العنوان: {ticket.title}
القسم: {ticket.department.name if ticket.department else 'غير محدد'}
الأولوية: {ticket.get_priority_display()}
تأخير: {ticket.hours_delayed:.1f} ساعة

الرجاء اتخاذ الإجراء اللازم فوراً.
                ''',
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@university.edu',
                recipient_list=[recipient.email],
                fail_silently=True,
            )


@shared_task
def send_deadline_warnings():
    """
    إرسال تحذيرات قبل انتهاء المهلة
    """
    now = timezone.now()
    
    # تحذير قبل ساعتين
    two_hours_ahead = now + timedelta(hours=2)
    tickets_2h = Ticket.objects.filter(
        status__in=['new', 'pending_ack', 'in_progress'],
        sla_deadline__lte=two_hours_ahead,
        sla_deadline__gt=now
    )
    
    for ticket in tickets_2h:
        time_left = ticket.sla_deadline - now
        hours_left = time_left.total_seconds() / 3600
        
        if 1.5 <= hours_left <= 2.5:  # تحذير في نطاق ساعتين
            send_warning_email(ticket, 'warning', hours_left)
    
    # تحذير نهائي قبل 30 دقيقة
    thirty_min_ahead = now + timedelta(minutes=30)
    tickets_30m = Ticket.objects.filter(
        status__in=['new', 'pending_ack', 'in_progress'],
        sla_deadline__lte=thirty_min_ahead,
        sla_deadline__gt=now
    )
    
    for ticket in tickets_30m:
        time_left = ticket.sla_deadline - now
        minutes_left = time_left.total_seconds() / 60
        
        if 20 <= minutes_left <= 40:  # تحذير في نطاق 30 دقيقة
            send_warning_email(ticket, 'urgent', minutes_left / 60)
    
    return f'تم إرسال تحذيرات لـ {tickets_2h.count() + tickets_30m.count()} طلب'


def send_warning_email(ticket, urgency, hours_left):
    """
    إرسال بريد تحذيري
    """
    if urgency == 'urgent':
        subject = f'🚨 تحذير عاجل: الطلب #{ticket.id} على وشك تجاوز المهلة'
        message = f'''
تحذير عاجل!

الطلب التالي على وشك تجاوز المهلة خلال {hours_left * 60:.0f} دقيقة:

العنوان: {ticket.title}
الأولوية: {ticket.get_priority_display()}
الموعد النهائي: {ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')}

يرجى اتخاذ الإجراء فوراً!
        '''
    else:
        subject = f'⏰ تذكير: الطلب #{ticket.id} يقترب من المهلة'
        message = f'''
تذكير بالمهلة

الطلب التالي يقترب من الموعد النهائي خلال {hours_left:.1f} ساعة:

العنوان: {ticket.title}
الأولوية: {ticket.get_priority_display()}
الموعد النهائي: {ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')}

يرجى العمل على حل الطلب في أقرب وقت.
        '''
    
    # إرسال للموظف المعين
    recipients = []
    if ticket.assigned_to and ticket.assigned_to.email:
        recipients.append(ticket.assigned_to.email)
    
    # إرسال لجميع المعينين
    for user in ticket.assigned_to_users.all():
        if user.email and user.email not in recipients:
            recipients.append(user.email)
    
    if recipients:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@university.edu',
            recipient_list=recipients,
            fail_silently=True,
        )


@shared_task
def calculate_daily_penalties():
    """
    حساب النقاط الجزائية اليومية
    """
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # الطلبات التي تأخرت اليوم
    violated_today = Ticket.objects.filter(
        status='violated',
        updated_at__gte=today_start
    )
    
    total_penalties = 0
    
    for ticket in violated_today:
        # التحقق من عدم وجود نقاط جزائية مكررة لهذا الطلب اليوم
        existing_penalty = PenaltyPoints.objects.filter(
            user=ticket.assigned_to,
            department=ticket.department,
            reason__icontains=ticket.title,
            created_at__gte=today_start
        ).exists()
        
        if existing_penalty:
            continue
        
        delay_hours = ticket.hours_delayed
        penalty_points = calculate_penalty_points(delay_hours)
        
        PenaltyPoints.objects.create(
            department=ticket.department,
            user=ticket.assigned_to,
            points=penalty_points,
            reason=f'تأخير يومي - {ticket.title}'
        )
        
        total_penalties += penalty_points
    
    return f'تم احتساب {total_penalties} نقطة جزائية'


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
    resolved_today = Ticket.objects.filter(resolved_at__gte=yesterday).count()
    
    # أسوأ الأقسام أداءً
    departments_performance = Department.objects.annotate(
        violated_count=Count('tickets', filter=Q(tickets__status='violated')),
        pending_count=Count('tickets', filter=Q(tickets__status__in=['new', 'pending_ack', 'in_progress']))
    ).order_by('-violated_count')[:5]
    
    # الموظفون الأقل استجابة
    worst_employees = CustomUser.objects.annotate(
        violated_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='violated'))
    ).filter(violated_count__gt=0).order_by('-violated_count')[:5]
    
    # أفضل الموظفين أداءً
    best_employees = CustomUser.objects.annotate(
        resolved_count=Count('assigned_tickets', filter=Q(assigned_tickets__status__in=['resolved', 'closed'])),
        total_assigned=Count('assigned_tickets')
    ).filter(total_assigned__gte=5).order_by('-resolved_count')[:5]
    
    # بناء التقرير
    report = f'''
📊 تقرير أداء نظام الطلبات اليومي
التاريخ: {now.strftime('%Y-%m-%d')}

=== الإحصائيات العامة ===
📌 إجمالي الطلبات: {total_tickets}
🆕 طلبات جديدة اليوم: {new_tickets_today}
✅ طلبات محلولة اليوم: {resolved_today}
⚠️ طلبات مخالفة (تجاوزت المهلة): {violated_tickets}
⏳ طلبات معلقة: {pending_tickets}

=== الأقسام الأكثر تأخيراً ===
'''
    
    for dept in departments_performance:
        report += f'🔴 {dept.name}: {dept.violated_count} طلب مخالف, {dept.pending_count} طلب معلق\n'
    
    report += '\n=== الموظفون الأقل استجابة ===\n'
    for emp in worst_employees:
        report += f'⚠️ {emp.get_full_name()} ({emp.department}): {emp.violated_count} طلب مخالف\n'
    
    report += '\n=== الموظفون المتميزون ===\n'
    for emp in best_employees:
        report += f'⭐ {emp.get_full_name()} ({emp.department}): {emp.resolved_count} طلب محلول\n'
    
    # إرسال التقرير للإدارة العليا
    admins = CustomUser.objects.filter(
        role__in=['president', 'dean', 'admin', 'admin_assistant', 'academic_assistant']
    )
    
    for admin in admins:
        if admin.email:
            send_mail(
                subject=f'📊 تقرير أداء نظام الطلبات - {now.strftime("%Y-%m-%d")}',
                message=report,
                from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@university.edu',
                recipient_list=[admin.email],
                fail_silently=True,
            )
    
    return 'تم إرسال التقرير اليومي'


@shared_task
def generate_performance_metrics():
    """
    إنشاء مقاييس الأداء اليومية
    """
    now = timezone.now()
    
    # حساب متوسط وقت الاستجابة
    avg_response_time = Ticket.objects.filter(
        acknowledged_at__isnull=False
    ).annotate(
        response_time=F('acknowledged_at') - F('created_at')
    ).aggregate(avg=Avg('response_time'))
    
    # حساب متوسط وقت الحل
    avg_resolution_time = Ticket.objects.filter(
        resolved_at__isnull=False
    ).annotate(
        resolution_time=F('resolved_at') - F('created_at')
    ).aggregate(avg=Avg('resolution_time'))
    
    # نسبة الالتزام بالمهلة
    total_resolved = Ticket.objects.filter(status__in=['resolved', 'closed']).count()
    on_time_resolved = Ticket.objects.filter(
        status__in=['resolved', 'closed'],
        resolved_at__lte=F('sla_deadline')
    ).count()
    
    compliance_rate = (on_time_resolved / total_resolved * 100) if total_resolved > 0 else 0
    
    logger.info(f'Performance Metrics - Response: {avg_response_time}, Resolution: {avg_resolution_time}, Compliance: {compliance_rate:.1f}%')
    
    return f'تم حساب مقاييس الأداء - نسبة الالتزام: {compliance_rate:.1f}%'

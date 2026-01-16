"""
وظائف إدارية متقدمة لنظام التذاكر
Advanced administrative views for ticket system
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Ticket, TicketAction, TicketAcknowledgment
from accounts.models import CustomUser, Department, PenaltyPoints
from .forms import CloseTicketForm, AddPenaltyForm
import logging

logger = logging.getLogger('tickets')


@login_required
def completed_tickets(request):
    """
    عرض الطلبات المكتملة
    Display completed tickets
    """
    # التحقق من الصلاحيات
    if not request.user.is_upper_management and request.user.role not in ['head', 'dean']:
        messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة')
        return redirect('dashboard')
    
    # الحصول على الطلبات المكتملة
    tickets = Ticket.objects.filter(
        status__in=['resolved', 'closed']
    ).select_related(
        'created_by', 'assigned_to', 'department'
    ).order_by('-resolved_at')
    
    # فلترة حسب القسم إذا لم يكن من الإدارة العليا
    if not request.user.is_upper_management:
        if request.user.department:
            tickets = tickets.filter(
                Q(department=request.user.department) | 
                Q(departments=request.user.department)
            ).distinct()
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tickets/completed_tickets.html', {
        'page_obj': page_obj,
        'search_query': search_query,
    })


@login_required
def acknowledge_status(request, pk):
    """
    عرض حالة الإقرارات لطلب معين
    Display acknowledgment status for a ticket
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من الصلاحيات
    can_view = (
        ticket.created_by == request.user or
        ticket.assigned_to == request.user or
        ticket.assigned_to_users.filter(id=request.user.id).exists() or
        request.user.is_upper_management or
        (ticket.department == request.user.department and request.user.role in ['head', 'dean']) or
        (ticket.departments.filter(id=request.user.department.id).exists() if request.user.department else False)
    )
    
    if not can_view:
        messages.error(request, 'ليس لديك صلاحية لعرض هذه المعلومات')
        return redirect('dashboard')
    
    # جمع معلومات الإقرارات
    acknowledgments = ticket.acknowledgments.all().select_related('user')
    
    # قائمة المعينين المطلوب إقرارهم
    required_users = []
    
    # المعين المفرد
    if ticket.assigned_to:
        has_acked = acknowledgments.filter(user=ticket.assigned_to).exists()
        required_users.append({
            'user': ticket.assigned_to,
            'acknowledged': has_acked,
            'ack_time': acknowledgments.filter(user=ticket.assigned_to).first().acknowledged_at if has_acked else None
        })
    
    # المعينين المتعددين
    for user in ticket.assigned_to_users.all():
        has_acked = acknowledgments.filter(user=user).exists()
        required_users.append({
            'user': user,
            'acknowledged': has_acked,
            'ack_time': acknowledgments.filter(user=user).first().acknowledged_at if has_acked else None
        })
    
    # حساب نسبة الإقرارات
    total_required = len(required_users)
    total_acknowledged = sum(1 for u in required_users if u['acknowledged'])
    ack_percentage = (total_acknowledged / total_required * 100) if total_required > 0 else 0
    
    return render(request, 'tickets/acknowledge_status.html', {
        'ticket': ticket,
        'required_users': required_users,
        'total_required': total_required,
        'total_acknowledged': total_acknowledged,
        'ack_percentage': ack_percentage,
    })


@login_required
def admin_close_ticket(request, pk):
    """
    إغلاق إداري للطلب - للإدارة العليا فقط
    Administrative ticket closure - upper management only
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من الصلاحيات - فقط الإدارة العليا
    if not request.user.is_upper_management:
        messages.error(request, 'ليس لديك صلاحية لإغلاق الطلبات إدارياً')
        return redirect('ticket_detail', pk=pk)
    
    if request.method == 'POST':
        form = CloseTicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket.close_notes = form.cleaned_data['close_notes']
            ticket.close_attachments = form.cleaned_data.get('close_attachments')
            ticket.status = 'closed'
            ticket.closed_at = timezone.now()
            ticket.resolved_at = timezone.now()
            ticket.save()
            
            # تسجيل الإجراء
            TicketAction.objects.create(
                ticket=ticket,
                action_type='closed',
                user=request.user,
                notes=f'إغلاق إداري: {form.cleaned_data["close_notes"]}'
            )
            
            messages.success(request, 'تم إغلاق الطلب إدارياً بنجاح')
            logger.info(f'Admin closure by {request.user.username} for ticket #{ticket.id}')
            return redirect('ticket_detail', pk=pk)
    else:
        form = CloseTicketForm()
    
    return render(request, 'tickets/admin_close_ticket.html', {
        'ticket': ticket,
        'form': form,
    })


@login_required
def reassign_ticket(request, pk):
    """
    إعادة تعيين الطلب - للإدارة والرؤساء
    Reassign ticket - for management and heads
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من الصلاحيات
    can_reassign = (
        request.user.is_upper_management or
        (ticket.department == request.user.department and request.user.role in ['head', 'dean']) or
        (ticket.departments.filter(id=request.user.department.id).exists() if request.user.department and request.user.role in ['head', 'dean'] else False)
    )
    
    if not can_reassign:
        messages.error(request, 'ليس لديك صلاحية لإعادة تعيين هذا الطلب')
        return redirect('ticket_detail', pk=pk)
    
    if request.method == 'POST':
        new_assignee_id = request.POST.get('new_assignee')
        reassign_reason = request.POST.get('reassign_reason', '')
        
        if new_assignee_id:
            try:
                new_assignee = CustomUser.objects.get(id=new_assignee_id)
                old_assignee = ticket.assigned_to
                
                # تحديث التعيين
                ticket.assigned_to = new_assignee
                ticket.status = 'pending_ack'  # إعادة إلى حالة انتظار الإقرار
                ticket.save()
                
                # تسجيل الإجراء
                TicketAction.objects.create(
                    ticket=ticket,
                    action_type='reassigned',
                    user=request.user,
                    notes=f'إعادة تعيين من {old_assignee} إلى {new_assignee}. السبب: {reassign_reason}'
                )
                
                messages.success(request, f'تم إعادة تعيين الطلب إلى {new_assignee.get_full_name()}')
                logger.info(f'Ticket #{ticket.id} reassigned by {request.user.username} to {new_assignee.username}')
                return redirect('ticket_detail', pk=pk)
            except CustomUser.DoesNotExist:
                messages.error(request, 'المستخدم المحدد غير موجود')
        else:
            messages.error(request, 'يجب تحديد موظف لإعادة التعيين')
    
    # الحصول على قائمة الموظفين المتاحين
    if request.user.is_upper_management:
        available_users = CustomUser.objects.filter(
            role='employee', 
            is_active=True
        ).order_by('first_name', 'last_name')
    else:
        # رؤساء الأقسام يرون فقط موظفي قسمهم
        available_users = CustomUser.objects.filter(
            department=request.user.department,
            role='employee',
            is_active=True
        ).order_by('first_name', 'last_name')
    
    return render(request, 'tickets/reassign_ticket.html', {
        'ticket': ticket,
        'available_users': available_users,
    })


@login_required
def get_notifications_enhanced(request):
    """
    API محسّن للإشعارات مع معلومات تفصيلية
    Enhanced notifications API with detailed information
    """
    user = request.user
    
    # الطلبات التي تحتاج إقرار
    ack_filter = Q(assigned_to=user) | Q(assigned_to_users=user)
    if user.department:
        ack_filter |= Q(departments=user.department)
    
    pending_ack = Ticket.objects.filter(
        ack_filter,
        status='pending_ack'
    ).exclude(
        acknowledgments__user=user
    ).distinct().count()
    
    # الطلبات الجديدة المعينة
    user_tickets_filter = Q(assigned_to=user) | Q(assigned_to_users=user)
    if user.department:
        user_tickets_filter |= Q(departments=user.department)
    
    new_tickets = Ticket.objects.filter(
        user_tickets_filter,
        status='new'
    ).distinct().count()
    
    # الطلبات المتأخرة
    overdue_tickets = Ticket.objects.filter(
        user_tickets_filter,
        status__in=['new', 'pending_ack', 'in_progress'],
        sla_deadline__lt=timezone.now()
    ).distinct().count()
    
    # الطلبات الحرجة
    critical_tickets = Ticket.objects.filter(
        user_tickets_filter,
        priority='critical',
        status__in=['new', 'pending_ack', 'in_progress']
    ).distinct().count()
    
    # الطلبات التي تحتاج متابعة (قريبة من المهلة)
    from datetime import timedelta
    near_deadline = Ticket.objects.filter(
        user_tickets_filter,
        status__in=['new', 'pending_ack', 'in_progress'],
        sla_deadline__lte=timezone.now() + timedelta(hours=2),
        sla_deadline__gt=timezone.now()
    ).distinct().count()
    
    return JsonResponse({
        'pending_acknowledgment': pending_ack,
        'new_tickets': new_tickets,
        'overdue_tickets': overdue_tickets,
        'critical_tickets': critical_tickets,
        'near_deadline': near_deadline,
        'total': pending_ack + new_tickets + overdue_tickets + critical_tickets + near_deadline,
        'timestamp': timezone.now().isoformat()
    })


@login_required
def violations_report(request):
    """
    تقرير المخالفات الشامل - سجل التأخيرات والمخالفات 📋
    Comprehensive violations report - The Wall of Shame
    """
    # التحقق من الصلاحيات
    if not request.user.is_upper_management and request.user.role not in ['head', 'dean']:
        messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة')
        return redirect('dashboard')
    
    from datetime import timedelta
    from django.db.models import Avg, Max, Min
    from django.core.paginator import Paginator
    
    now = timezone.now()
    
    # الحصول على الفترة من المعاملات
    period_days = int(request.GET.get('period', 30))
    start_date = now - timedelta(days=period_days)
    
    from django.db.models import F
    
    # الحصول على جميع الطلبات المخالفة أو المتأخرة
    # نعرض:
    # 1. التذاكر التي حالتها violated
    # 2. التذاكر الحالية التي تجاوزت المهلة ولم تُغلق/تُحل بعد
    # 3. التذاكر المغلقة/المحلولة التي تم حلها بعد الموعد النهائي (تأخير تاريخي)
    violated_tickets = Ticket.objects.filter(
        Q(status='violated') | 
        (Q(sla_deadline__lt=now) & ~Q(status__in=['resolved', 'closed'])) |
        (Q(status__in=['resolved', 'closed']) & Q(resolved_at__gt=F('sla_deadline')))
    ).select_related(
        'created_by', 'assigned_to', 'department'
    ).prefetch_related(
        'created_by', 'assigned_to', 'department'
    ).prefetch_related(
        'departments', 'assigned_to_users'
    ).order_by('-created_at')
    
    # فلترة حسب الفترة إذا تم تحديدها
    if request.GET.get('period'):
        violated_tickets = violated_tickets.filter(created_at__gte=start_date)
    
    # فلترة حسب القسم
    if not request.user.is_upper_management:
        if request.user.department:
            violated_tickets = violated_tickets.filter(
                Q(department=request.user.department) | 
                Q(departments=request.user.department)
            ).distinct()
    
    department_filter = request.GET.get('department')
    if department_filter:
        violated_tickets = violated_tickets.filter(
            Q(department_id=department_filter) | 
            Q(departments__id=department_filter)
        ).distinct()
    
    # فلترة حسب الموظف
    employee_filter = request.GET.get('employee')
    if employee_filter:
        violated_tickets = violated_tickets.filter(
            Q(assigned_to_id=employee_filter) | 
            Q(assigned_to_users__id=employee_filter)
        ).distinct()
    
    # فلترة حسب الأولوية
    priority_filter = request.GET.get('priority')
    if priority_filter:
        violated_tickets = violated_tickets.filter(priority=priority_filter)
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        violated_tickets = violated_tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # إحصائيات عامة
    total_violations = violated_tickets.count()
    
    # متوسط ساعات التأخير
    violations_with_delay = [t for t in violated_tickets if t.hours_delayed > 0]
    avg_delay_hours = sum(t.hours_delayed for t in violations_with_delay) / len(violations_with_delay) if violations_with_delay else 0
    
    # أكبر تأخير
    max_delay_hours = max((t.hours_delayed for t in violated_tickets), default=0)
    
    # توزيع المخالفات حسب الأولوية
    critical_violations = violated_tickets.filter(priority='critical').count()
    urgent_violations = violated_tickets.filter(priority='urgent').count()
    normal_violations = violated_tickets.filter(priority='normal').count()
    
    # الأقسام الأكثر مخالفة
    # الأقسام الأكثر مخالفة (تشمل المخالفات الصريحة والمتأخرة والتأخير التاريخي)
    violation_filter_base = Q(status='violated') | \
                            (Q(sla_deadline__lt=now) & ~Q(status__in=['resolved', 'closed'])) | \
                            (Q(status__in=['resolved', 'closed']) & Q(resolved_at__gt=F('sla_deadline')))
    
    violation_filter_dept = Q(tickets__status='violated') | \
                            (Q(tickets__sla_deadline__lt=now) & ~Q(tickets__status__in=['resolved', 'closed'])) | \
                            (Q(tickets__status__in=['resolved', 'closed']) & Q(tickets__resolved_at__gt=F('tickets__sla_deadline')))

    departments_violations = Department.objects.annotate(
        violations_count=Count('tickets', filter=violation_filter_dept)
    ).filter(violations_count__gt=0).order_by('-violations_count')[:10]
    
    # الموظفون الأكثر مخالفة
    violation_filter_user = Q(assigned_tickets__status='violated') | \
                            (Q(assigned_tickets__sla_deadline__lt=now) & ~Q(assigned_tickets__status__in=['resolved', 'closed'])) | \
                            (Q(assigned_tickets__status__in=['resolved', 'closed']) & Q(assigned_tickets__resolved_at__gt=F('assigned_tickets__sla_deadline')))
    
    employees_violations = CustomUser.objects.filter(
        role__in=['employee', 'head']
    ).annotate(
        violations_count=Count('assigned_tickets', filter=violation_filter_user)
    ).filter(violations_count__gt=0).order_by('-violations_count')[:10]
    
    # Pagination
    paginator = Paginator(violated_tickets, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # جمع البيانات للرسم البياني
    import json
    chart_data = {
        'priority': {
            'critical': critical_violations,
            'urgent': urgent_violations,
            'normal': normal_violations
        },
        'departments': [
            {'name': d.name, 'count': d.violations_count}
            for d in departments_violations[:5]
        ]
    }
    
    context = {
        'page_obj': page_obj,
        'total_violations': total_violations,
        'avg_delay_hours': round(avg_delay_hours, 1),
        'max_delay_hours': round(max_delay_hours, 1),
        'critical_violations': critical_violations,
        'urgent_violations': urgent_violations,
        'normal_violations': normal_violations,
        'departments_violations': departments_violations,
        'employees_violations': employees_violations,
        'chart_data': json.dumps(chart_data),
        'period_days': period_days,
        'search_query': search_query,
        'departments': Department.objects.all().order_by('name'),
        'employees': CustomUser.objects.filter(
            role__in=['employee', 'head']
        ).order_by('first_name', 'last_name'),
    }
    
    return render(request, 'tickets/violations_report.html', context)


@login_required
def export_violations_csv(request):
    """
    تصدير تقرير المخالفات إلى CSV
    Export violations report to CSV
    """
    # التحقق من الصلاحيات
    if not request.user.is_upper_management and request.user.role not in ['head', 'dean']:
        messages.error(request, 'ليس لديك صلاحية لتصدير البيانات')
        return redirect('dashboard')
    
    import csv
    from django.utils.encoding import smart_str
    from datetime import timedelta
    
    now = timezone.now()
    period_days = int(request.GET.get('period', 30))
    start_date = now - timedelta(days=period_days)
    
    # الحصول على المخالفات (المخالفة صراحة أو المتأخرة حالياً أو المتأخرة تاريخياً)
    violated_tickets = Ticket.objects.filter(
        Q(status='violated') | 
        (Q(sla_deadline__lt=now) & ~Q(status__in=['resolved', 'closed'])) |
        (Q(status__in=['resolved', 'closed']) & Q(resolved_at__gt=F('sla_deadline')))
    ).select_related(
        'created_by', 'assigned_to', 'department'
    ).order_by('-created_at')
    
    if request.GET.get('period'):
        violated_tickets = violated_tickets.filter(created_at__gte=start_date)
    
    # إنشاء Response
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="violations_report_{now.strftime("%Y%m%d_%H%M")}.csv"'
    response.write('\ufeff')  # BOM for Excel UTF-8
    
    writer = csv.writer(response)
    
    # العناوين
    writer.writerow([
        smart_str('رقم الطلب'),
        smart_str('العنوان'),
        smart_str('القسم'),
        smart_str('المعين له'),
        smart_str('الأولوية'),
        smart_str('تاريخ الإنشاء'),
        smart_str('الموعد النهائي'),
        smart_str('ساعات التأخير'),
        smart_str('منشئ الطلب'),
    ])
    
    # البيانات
    for ticket in violated_tickets:
        # تجميع الأقسام
        departments = ', '.join([d.name for d in ticket.departments.all()]) if ticket.departments.exists() else (ticket.department.name if ticket.department else '-')
        
        # تجميع المعينين
        if ticket.assigned_to:
            assigned = ticket.assigned_to.get_full_name() or ticket.assigned_to.username
        elif ticket.assigned_to_users.exists():
            assigned = ', '.join([u.get_full_name() or u.username for u in ticket.assigned_to_users.all()])
        else:
            assigned = '-'
        
        writer.writerow([
            ticket.id,
            smart_str(ticket.title),
            smart_str(departments),
            smart_str(assigned),
            smart_str(ticket.get_priority_display()),
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ticket.sla_deadline.strftime('%Y-%m-%d %H:%M'),
            round(ticket.hours_delayed, 1),
            smart_str(ticket.created_by.get_full_name() or ticket.created_by.username),
        ])
    
    logger.info(f'Violations CSV exported by {request.user.username}')
    return response


@login_required
def mark_as_violation(request, pk):
    """
    تسجيل مخالفة يدوياً على التذكرة - للإدارة العليا فقط
    Manually mark ticket as violated
    """
    # التحقق من الصلاحيات - فقط الأدمن ورئيس الجامعة
    if request.user.role not in ['admin', 'president']:
        messages.error(request, 'ليس لديك صلاحية لتسجيل مخالفات. هذه الميزة متاحة فقط للأدمن ورئيس الجامعة')
        return redirect('ticket_detail', pk=pk)
    
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('violation_reason', 'تم تسجيل المخالفة يدوياً من قبل الإدارة')
        
        # تحديث حالة التذكرة
        old_status = ticket.status
        ticket.status = 'violated'
        ticket.save()
        
        # تسجيل نقاط جزائية على المعين له (إذا وجد)
        if ticket.assigned_to:
            current_points = ticket.assigned_to.penalties.aggregate(total=Sum('points'))['total'] or 0
            PenaltyPoints.objects.create(
                user=ticket.assigned_to,
                points=10,  # 10 نقاط للمخالفة اليدوية
                reason=f"مخالفة يدوية للتذكرة #{ticket.id}: {reason}"
            )
        
        # تسجيل الإجراء
        TicketAction.objects.create(
            ticket=ticket,
            action_type='violation',
            user=request.user,
            notes=f'تم تحويلها لمخالفة يدوياً. السبب: {reason}'
        )
        
        messages.success(request, 'تم تسجيل المخالفة بنجاح وإضافة نقاط جزائية')
        logger.info(f'Ticket #{ticket.id} marked as violation by {request.user.username}')
        
    return redirect('ticket_detail', pk=pk)


@login_required
def add_manual_penalty(request):
    """
    إضافة نقاط جزائية يدوياً لموظف أو قسم
    Add manual penalty points
    """
    if not request.user.is_upper_management:
        messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AddPenaltyForm(request.POST)
        if form.is_valid():
            target_type = form.cleaned_data['target_type']
            points = form.cleaned_data['points']
            reason = form.cleaned_data['reason']
            
            if target_type == 'user':
                user = form.cleaned_data['user']
                PenaltyPoints.objects.create(
                    user=user,
                    points=points,
                    reason=reason
                )
                target_name = user.get_full_name()
            else:
                department = form.cleaned_data['department']
                PenaltyPoints.objects.create(
                    department=department,
                    points=points,
                    reason=reason
                )
                target_name = department.name
            
            messages.success(request, f'تم إضافة {points} نقطة جزائية إلى {target_name} بنجاح')
            logger.info(f'Manual penalty added by {request.user.username} to {target_name}')
            return redirect('penalty_points_report')
    else:
        form = AddPenaltyForm()
        
    return render(request, 'tickets/add_penalty.html', {'form': form})

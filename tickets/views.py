from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django_ratelimit.decorators import ratelimit
from datetime import timedelta
from .models import Ticket, TicketAction, TicketAcknowledgment
from notifications.models import GlobalMail
from .forms import CreateTicketForm, CloseTicketForm, AcknowledgeTicketForm, CommentForm, ReturnTicketForm
from .decorators import can_view_reports, can_export_data  # نظام الصلاحيات الجديد
from accounts.models import Department, CustomUser
import json
import logging

# Initialize logger
logger = logging.getLogger('tickets')




@login_required
def dashboard(request):
    """
    لوحة التحكم الرئيسية - تعرض إحصائيات مختلفة حسب دور المستخدم
    Optimized with caching and select_related
    """
    user = request.user
    cache_key = f'dashboard_stats_{user.id}_{user.role}'
    
    # Try to get from cache first
    context = cache.get(cache_key)
    
    if not context:
        logger.info(f'Dashboard cache miss for user {user.id}')
        context = {'user': user}
        # إضافة البريد العام
        context['global_mails'] = GlobalMail.objects.all()[:5]
        
        # التحقق من أن المستخدم من الإدارة العليا
        is_upper_management = user.is_upper_management
        
        if is_upper_management:
            # لوحة الإدارة العليا - عرض كل شيء
            now = timezone.now()
            
            # إحصائيات عامة - optimized queries
            context.update({
                'total_tickets': Ticket.objects.count(),
                'pending_tickets': Ticket.objects.filter(status__in=['new', 'pending_ack', 'in_progress']).count(),
                'violated_tickets': Ticket.objects.filter(status='violated').count(),
                'resolved_today': Ticket.objects.filter(resolved_at__date=now.date()).count(),
                'worst_departments': Department.objects.annotate(
                    violated_count=Count('tickets', filter=Q(tickets__status='violated'))
                ).filter(violated_count__gt=0).order_by('-violated_count')[:5],  # فقط الأقسام ذات الانتهاكات
                'critical_tickets': Ticket.objects.select_related(
                    'department', 'assigned_to', 'created_by'
                ).filter(
                    priority='critical',
                    status__in=['new', 'pending_ack', 'in_progress']
                ).order_by('sla_deadline')[:10],
                'is_upper_management': True,
            })
            
            # بيانات الرسم البياني - آخر 7 أيام
            chart_data = []
            for i in range(6, -1, -1):
                day = now - timedelta(days=i)
                chart_data.append({
                    'date': day.strftime('%Y-%m-%d'),
                    'created': Ticket.objects.filter(created_at__date=day.date()).count(),
                    'resolved': Ticket.objects.filter(resolved_at__date=day.date()).count(),
                    'violated': Ticket.objects.filter(
                        status='violated',
                        created_at__date=day.date()
                    ).count(),
                })
            
            context['chart_data'] = json.dumps(chart_data)
            
            # توزيع الأولويات
            priority_data = {
                'critical': Ticket.objects.filter(priority='critical').count(),
                'urgent': Ticket.objects.filter(priority='urgent').count(),
                'normal': Ticket.objects.filter(priority='normal').count(),
            }
            context['priority_data'] = json.dumps(priority_data)
            
        elif user.role == 'dean' or user.role == 'head':
            # لوحة العميد أو رئيس القسم
            # الفلتر يشمل:
            # 1. التذاكر المسندة للقسم المفرد (department)
            # 2. التذاكر المسندة للأقسام المتعددة (departments)
            # 3. التذاكر المسندة شخصياً
            dept_filter = Q(department=user.department) | Q(departments=user.department) if user.department else Q()
            personal_filter = Q(assigned_to=user) | Q(assigned_to_users=user) | Q(created_by=user)
            combined_filter = dept_filter | personal_filter
            
            context.update({
                'my_dept_tickets': Ticket.objects.filter(combined_filter).distinct().count(),
                'my_dept_pending': Ticket.objects.filter(combined_filter, status__in=['new', 'pending_ack', 'in_progress']).distinct().count(),
                'my_dept_violated': Ticket.objects.filter(combined_filter, status='violated').distinct().count(),
                'recent_tickets': Ticket.objects.select_related(
                    'department', 'assigned_to', 'created_by'
                ).filter(combined_filter).distinct().order_by('-created_at')[:10],
            })
            
            # متوسط وقت الحل
            resolved_tickets = Ticket.objects.filter(combined_filter, status__in=['resolved', 'closed']).distinct()
            if resolved_tickets.exists():
                avg_time = sum([
                    (t.resolved_at - t.created_at).total_seconds() / 3600 
                    for t in resolved_tickets if t.resolved_at
                ]) / resolved_tickets.count()
                context['avg_resolution_time'] = round(avg_time, 1)
            else:
                context['avg_resolution_time'] = 0
        
        else:
            # لوحة الموظف - تحديث لتشمل التعيين المتعدد
            # الفلتر يشمل:
            # 1. التعيين المباشر (assigned_to)
            # 2. التعيين المتعدد (assigned_to_users)
            # 3. التعيين للقسم (departments)
            # 4. التذاكر التي أنشأها المستخدم (created_by)
            
            user_tickets_filter = Q(assigned_to=user) | Q(assigned_to_users=user) | Q(created_by=user)
            if user.department:
                user_tickets_filter |= Q(departments=user.department)

            context.update({
                'my_tickets': Ticket.objects.filter(user_tickets_filter).distinct().count(),
                'my_pending': Ticket.objects.filter(
                    user_tickets_filter,
                    status__in=['new', 'pending_ack', 'in_progress']
                ).distinct().count(),
                'my_overdue': Ticket.objects.filter(
                    user_tickets_filter,
                    status__in=['new', 'pending_ack', 'in_progress'],
                    sla_deadline__lt=timezone.now()
                ).distinct().count(),
                'assigned_to_me': Ticket.objects.select_related(
                    'department', 'created_by'
                ).filter(user_tickets_filter).distinct().order_by('-created_at')[:10],
            })
            
            # معدل الإنجاز
            total = Ticket.objects.filter(user_tickets_filter).distinct().count()
            resolved = Ticket.objects.filter(
                user_tickets_filter, 
                status__in=['resolved', 'closed']
            ).distinct().count()
            context['completion_rate'] = round((resolved / total * 100) if total > 0 else 0, 1)
        
        # Cache for 5 minutes
        cache.set(cache_key, context, 300)
        logger.info(f'Dashboard cached for user {user.id}')
    
    return render(request, 'tickets/dashboard.html', context)


@login_required
def acknowledge_tickets(request):
    """
    صفحة تأكيد استلام الطلبات - إجبارية مع إقرار رسمي
    """
    # الحصول على الطلبات التي لم يتم الإقرار بها
    # يشمل:
    # 1. التعيين المباشر (assigned_to)
    # 2. التعيين المتعدد (assigned_to_users)
    # 3. التعيين للقسم (departments)
    
    ack_filter = Q(assigned_to=request.user) | Q(assigned_to_users=request.user)
    if request.user.department:
        ack_filter |= Q(departments=request.user.department)
        
    unacknowledged = Ticket.objects.filter(
        ack_filter,
        status='pending_ack'
    ).exclude(
        acknowledgments__user=request.user
    ).distinct()
    
    if request.method == 'POST':
        ticket_ids = request.POST.getlist('ticket_ids')
        notes = request.POST.get('notes', '')
        
        # الحصول على IP Address
        def get_client_ip(request):
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return ip
        
        ip_address = get_client_ip(request)
        
        # تأكيد جميع التذاكر المحددة
        # نسمح بالإقرار إذا كان المستخدم معيناً (مفرداً أو متعدداً) أو ضمن الأقسام المعنية
        ack_perm_filter = Q(assigned_to=request.user) | Q(assigned_to_users=request.user)
        if request.user.department:
            ack_perm_filter |= Q(departments=request.user.department)

        acknowledged_tickets = Ticket.objects.filter(
            id__in=ticket_ids
        ).filter(ack_perm_filter).distinct()
        
        count = 0
        for ticket in acknowledged_tickets:
            # إنشاء إقرار رسمي
            ack, created = TicketAcknowledgment.objects.get_or_create(
                ticket=ticket,
                user=request.user,
                defaults={
                    'notes': notes,
                    'ip_address': ip_address
                }
            )
            
            if created:
                count += 1
                
                # التحقق من اكتمال الإقرارات المطلوبة لتغيير الحالة
                # يتطلب إقراراً من:
                # 1. المعين المفرد (إذا وجد)
                # 2. جميع المعينين المتعددين (إذا وجدوا)
                # 3. ممثل واحد على الأقل من كل قسم (إذا كان التعيين للأقسام)
                
                required_acks_met = True
                
                # 1. المعين المفرد
                if ticket.assigned_to and not ticket.acknowledgments.filter(user=ticket.assigned_to).exists():
                    required_acks_met = False
                
                # 2. المعينين المتعددين
                if ticket.assigned_to_users.exists():
                    users_ids = ticket.assigned_to_users.values_list('id', flat=True)
                    acked_users = ticket.acknowledgments.values_list('user_id', flat=True)
                    # هل كل مستخدم معين موجود في قائمة المقرين؟
                    if not all(uid in acked_users for uid in users_ids):
                        required_acks_met = False
                
                # 3. الأقسام (نتجاوز هذا الشرط مؤقتاً إذا كان هناك تعيين لأشخاص، أو نطبقه بصرامة)
                # المنطق هنا: إذا لم يكن هناك تعيين لأشخاص، ننتظر إقرار أي شخص من القسم
                if not ticket.assigned_to and not ticket.assigned_to_users.exists() and ticket.departments.exists():
                    # نحتاج إقراراً واحداً على الأقل من عضو ينتمي لأي من الأقسام المعنية
                    # لكن هذا قد يكون معقداً، لذا سنكتفي حالياً بالتحقق من وجود إقرار واحد على الأقل للطلب
                    if not ticket.acknowledgments.exists():
                        required_acks_met = False

                # تحديث الحالة فقط إذا اكتملت الشروط
                if required_acks_met:
                    ticket.acknowledged_at = timezone.now()
                    ticket.status = 'in_progress'
                    ticket.save()
                    
                    TicketAction.objects.create(
                        ticket=ticket,
                        action_type='acknowledged',
                        user=request.user,
                        notes=f'تم اكتمال الإقرارات وبدء المعالجة - {notes}' if notes else 'تم اكتمال الإقرارات'
                    )
                else:
                     TicketAction.objects.create(
                        ticket=ticket,
                        action_type='acknowledged',
                        user=request.user,
                        notes=f'تم تسجيل إقرار فردي - {notes}' if notes else 'تم تسجيل إقرار فردي'
                    )
        
        messages.success(request, f'تم تسجيل إقرارك لـ {count} طلب')
        return redirect('dashboard')
    
    return render(request, 'tickets/acknowledge.html', {
        'unacknowledged_tickets': unacknowledged
    })


@login_required
def create_ticket(request):
    """
    إنشاء طلب جديد
    """
    if request.method == 'POST':
        form = CreateTicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.status = 'pending_ack'
            
            # تعيين مستوى التصعيد الابتدائي إن وُجد
            if form.cleaned_data.get('escalation_level'):
                ticket.escalation_level = form.cleaned_data['escalation_level']
            
            # تعيين المستخدم المفرد (Primary) من قائمة المستخدمين إذا وجد
            assigned_users = form.cleaned_data.get('assigned_to_users')
            if assigned_users and assigned_users.exists():
                ticket.assigned_to = assigned_users.first()
                
            ticket.save()
            form.save_m2m()  # حفظ ManyToMany relationships (departments and assigned_to_users)
            
            # تسجيل الإجراء
            TicketAction.objects.create(
                ticket=ticket,
                action_type='created',
                user=request.user,
                notes='تم إنشاء الطلب'
            )
            
            messages.success(request, 'تم إنشاء الطلب بنجاح')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = CreateTicketForm()
    
    return render(request, 'tickets/create_ticket.html', {'form': form})


@login_required
def acknowledge_ticket_single(request, pk):
    """
    إقرار استلام لطلب واحد
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    if request.method == 'POST':
        # التحقق من أن المستخدم معين للطلب
        is_assigned = (
            ticket.assigned_to == request.user or 
            ticket.assigned_to_users.filter(id=request.user.id).exists() or
            (ticket.department == request.user.department and not ticket.assigned_to and not ticket.assigned_to_users.exists()) or
            (ticket.departments.filter(id=request.user.department.id if request.user.department else None).exists() and not ticket.assigned_to and not ticket.assigned_to_users.exists())
        )
        
        if not is_assigned:
            messages.error(request, 'ليس لديك صلاحية للإقرار باستلام هذا الطلب')
            return redirect('ticket_detail', pk=pk)
            
        # التحقق من عدم الإقرار مسبقاً
        if ticket.acknowledgments.filter(user=request.user).exists():
            messages.warning(request, 'لقد قمت بالإقرار باستلام هذا الطلب مسبقاً')
            return redirect('ticket_detail', pk=pk)
            
        # تسجيل الإقرار
        ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')).split(',')[0]
        
        TicketAcknowledgment.objects.create(
            ticket=ticket,
            user=request.user,
            notes='تم الإقرار من صفحة التفاصيل',
            ip_address=ip_address
        )
        
        # التحقق من اكتمال الإقرارات المطلوبة لتغيير الحالة
        required_acks_met = True
        
        # 1. المعين المفرد
        if ticket.assigned_to and not ticket.acknowledgments.filter(user=ticket.assigned_to).exists():
            required_acks_met = False
        
        # 2. المعينين المتعددين
        if ticket.assigned_to_users.exists():
            users_ids = ticket.assigned_to_users.values_list('id', flat=True)
            acked_users = ticket.acknowledgments.values_list('user_id', flat=True)
            if not all(uid in acked_users for uid in users_ids):
                required_acks_met = False

        # 3. الأقسام (إذا لم يكن هناك تعيين لأشخاص)
        if not ticket.assigned_to and not ticket.assigned_to_users.exists() and ticket.departments.exists():
            if not ticket.acknowledgments.exists():
                required_acks_met = False

        if required_acks_met:
            ticket.acknowledged_at = timezone.now()
            ticket.status = 'in_progress'
            ticket.save()
            
            TicketAction.objects.create(
                ticket=ticket,
                action_type='acknowledged',
                user=request.user,
                notes='تم اكتمال الإقرارات وبدء المعالجة'
            )
        else:
            TicketAction.objects.create(
                ticket=ticket,
                action_type='acknowledged',
                user=request.user,
                notes='تم تسجيل إقرار فردي (بانتظار بقية المعنيين)'
            )
            
        messages.success(request, 'تم تأكيد استلام الطلب بنجاح')
        return redirect('ticket_detail', pk=pk)
        
    return redirect('ticket_detail', pk=pk)


@login_required
def ticket_detail(request, pk):
    """
    تفاصيل الطلب مع إمكانية التعليق
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من صلاحية المستخدم لعرض هذه التذكرة
    # يمكن للمستخدم رؤية التذكرة إذا كان:
    # 1. من الإدارة العليا
    # 2. منشئ التذكرة
    # 3. معين له (مباشرة أو ضمن مجموعة)
    # 4. من قسم معين للتذكرة
    # 5. رئيس قسم أو عميد للقسم المعني
    
    can_view = False
    
    if request.user.is_upper_management:
        can_view = True
    elif ticket.created_by == request.user:
        can_view = True
    elif ticket.assigned_to == request.user:
        can_view = True
    elif ticket.assigned_to_users.filter(id=request.user.id).exists():
        can_view = True
    elif ticket.department == request.user.department:
        can_view = True
    elif ticket.departments.filter(id=request.user.department.id if request.user.department else None).exists():
        can_view = True
    
    if not can_view:
        messages.error(request, 'ليس لديك صلاحية لعرض هذا الطلب')
        return redirect('dashboard')
    
    actions = ticket.actions.all().order_by('-created_at')
    
    # التحقق مما إذا كان المستخدم يحتاج للإقرار
    needs_acknowledgment = False
    if ticket.status in ['new', 'pending_ack']:
        is_assigned = (
            ticket.assigned_to == request.user or 
            ticket.assigned_to_users.filter(id=request.user.id).exists() or
            (ticket.department == request.user.department and not ticket.assigned_to and not ticket.assigned_to_users.exists()) or
            (ticket.departments.filter(id=request.user.department.id if request.user.department else None).exists() and not ticket.assigned_to and not ticket.assigned_to_users.exists())
        )
        
        if is_assigned and not ticket.acknowledgments.filter(user=request.user).exists():
            needs_acknowledgment = True
    
    # نموذج التعليق
    if request.method == 'POST':
        if needs_acknowledgment:
            messages.error(request, 'يجب عليك الإقرار باستلام الطلب قبل إضافة تعليق')
            return redirect('ticket_detail', pk=pk)
            
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            TicketAction.objects.create(
                ticket=ticket,
                action_type='commented',
                user=request.user,
                notes=comment_form.cleaned_data['comment']
            )
            messages.success(request, 'تم إضافة التعليق')
            return redirect('ticket_detail', pk=pk)
    else:
        comment_form = CommentForm()
    
    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'actions': actions,
        'comment_form': comment_form,
        'needs_acknowledgment': needs_acknowledgment,
    })


@login_required
def close_ticket(request, pk):
    """
    إغلاق الطلب - يتطلب معلومات إلزامية
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من الصلاحيات - يمكن للمعين له (مفرد أو متعدد) أو الإدارة العليا إغلاق الطلب
    can_close = (
        ticket.assigned_to == request.user or 
        ticket.assigned_to_users.filter(id=request.user.id).exists() or
        request.user.role in ['head', 'dean', 'president', 'admin']
    )
    
    if not can_close:
        messages.error(request, 'ليس لديك صلاحية لإغلاق هذا الطلب')
        return redirect('ticket_detail', pk=pk)
    
    # التحقق من أن المستخدم قد أكد الاستلام إذا كان معيناً
    is_assigned = (
        ticket.assigned_to == request.user or 
        ticket.assigned_to_users.filter(id=request.user.id).exists()
    )
    
    if is_assigned and not ticket.acknowledgments.filter(user=request.user).exists():
        messages.error(request, 'يجب عليك تأكيد استلام الطلب قبل إغلاقه')
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
            
            # تسجيل الإجراء مع الوقت المستغرق
            execution_time = form.cleaned_data.get('execution_time', '')
            notes_with_time = f"{form.cleaned_data['close_notes']}\n\nالوقت المستغرق: {execution_time}"
            
            TicketAction.objects.create(
                ticket=ticket,
                action_type='closed',
                user=request.user,
                notes=notes_with_time
            )
            
            messages.success(request, 'تم إغلاق الطلب بنجاح')
            return redirect('ticket_detail', pk=pk)
    else:
        form = CloseTicketForm()
    
    return render(request, 'tickets/close_ticket.html', {
        'ticket': ticket,
        'form': form,
    })


@login_required
def ticket_list(request):
    """
    قائمة الطلبات مع فلترة وبحث وترقيم صفحات
    """
    tickets = Ticket.objects.all()
    
    # الفلترة حسب الدور
    if request.user.is_upper_management:
        # الإدارة العليا ترى جميع الطلبات
        pass  # لا حاجة لفلترة
    elif request.user.role == 'employee':
        # الموظف يرى:
        # 1. التذاكر المسندة إليه مباشرة
        # 2. التذاكر المسندة إليه ضمن مجموعة
        # 3. التذاكر المسندة لقسمه (كمجموعة)
        # 4. التذاكر التي أنشأها
        
        employee_filter = Q(assigned_to=request.user) | \
                         Q(assigned_to_users=request.user) | \
                         Q(created_by=request.user)
        
        if request.user.department:
            employee_filter |= Q(departments=request.user.department)
            
        tickets = tickets.filter(employee_filter).distinct()

    elif request.user.role in ['head', 'dean']:
        # رئيس القسم/العميد يرى:
        # 1. جميع تذاكر قسمه (المباشرة والمتعددة)
        # 2. التذاكر المسندة إليه شخصياً (حتى لو من قسم آخر)
        
        head_filter = Q(department=request.user.department) | \
                     Q(departments=request.user.department) | \
                     Q(assigned_to=request.user) | \
                     Q(assigned_to_users=request.user)
                     
        tickets = tickets.filter(head_filter).distinct()
    
    # البحث
    search_query = request.GET.get('search', '')
    if search_query:
        tickets = tickets.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # فلترة إضافية
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    priority = request.GET.get('priority')
    if priority:
        tickets = tickets.filter(priority=priority)
    
    department = request.GET.get('department')
    if department:
        tickets = tickets.filter(department_id=department)
    
    tickets = tickets.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(tickets, 20)  # 20 طلب في الصفحة
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'tickets/ticket_list.html', {
        'page_obj': page_obj,
        'departments': Department.objects.all(),
        'search_query': search_query,
    })


@login_required
@can_view_reports
def reports_dashboard(request):
    """
    لوحة التقارير والإحصائيات - سجل المخالفات
    """
    # الأقسام الأكثر تأخيراً
    departments_stats = Department.objects.annotate(
        total_tickets=Count('tickets'),
        violated_tickets=Count('tickets', filter=Q(tickets__status='violated')),
        pending_tickets=Count('tickets', filter=Q(tickets__status__in=['new', 'pending_ack', 'in_progress']))
    ).order_by('-violated_tickets')
    
    # الموظفون الأقل استجابة
    employees_stats = CustomUser.objects.filter(role='employee').annotate(
        total_assigned=Count('assigned_tickets'),
        violated_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='violated'))
    ).filter(violated_count__gt=0).order_by('-violated_count')[:10]
    
    # إحصائيات عامة
    total_tickets = Ticket.objects.count()
    pending = Ticket.objects.filter(status__in=['new', 'pending_ack', 'in_progress']).count()
    violated = Ticket.objects.filter(status='violated').count()
    resolved = Ticket.objects.filter(status__in=['resolved', 'closed']).count()
    
    # بيانات الرسم البياني للأقسام
    dept_chart_data = []
    for dept in departments_stats[:10]:
        dept_chart_data.append({
            'name': dept.name,
            'total': dept.total_tickets,
            'violated': dept.violated_tickets,
            'pending': dept.pending_tickets
        })
    
    from notifications.models import GlobalMail
    context = {
        'departments_stats': departments_stats,
        'employees_stats': employees_stats,
        'total_tickets': total_tickets,
        'pending': pending,
        'violated': violated,
        'resolved': resolved,
        'violation_rate': (violated / total_tickets * 100) if total_tickets > 0 else 0,
        'dept_chart_data': json.dumps(dept_chart_data),
        'global_mails': GlobalMail.objects.all()[:5],
    }
    
    return render(request, 'tickets/reports_dashboard.html', context)


@login_required
@can_export_data
def export_report(request):
    """
    تصدير التقرير إلى CSV
    """
    import csv
    from django.utils.encoding import smart_str
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="report_{timezone.now().strftime("%Y%m%d")}.csv"'
    response.write('\ufeff')  # BOM for Excel UTF-8
    
    writer = csv.writer(response)
    writer.writerow([
        smart_str('العنوان'),
        smart_str('القسم'),
        smart_str('الأولوية'),
        smart_str('الحالة'),
        smart_str('المعين له'),
        smart_str('تاريخ الإنشاء'),
        smart_str('الموعد النهائي'),
        smart_str('متأخر؟')
    ])
    
    tickets = Ticket.objects.all()
    
    # تطبيق الفلاتر - نفس منطق ticket_list
    if request.user.is_upper_management:
        # الإدارة العليا ترى جميع الطلبات
        pass
    elif request.user.role == 'employee':
        employee_filter = Q(assigned_to=request.user) | \
                         Q(assigned_to_users=request.user) | \
                         Q(created_by=request.user)
        
        if request.user.department:
            employee_filter |= Q(departments=request.user.department)
            
        tickets = tickets.filter(employee_filter).distinct()
    elif request.user.role in ['head', 'dean']:
        head_filter = Q(department=request.user.department) | \
                     Q(departments=request.user.department) | \
                     Q(assigned_to=request.user) | \
                     Q(assigned_to_users=request.user)
                     
        tickets = tickets.filter(head_filter).distinct()
    
    for ticket in tickets:
        dept_name = ticket.department.name if ticket.department else 'غير محدد'
        writer.writerow([
            smart_str(ticket.title),
            smart_str(dept_name),
            smart_str(ticket.get_priority_display()),
            smart_str(ticket.get_status_display()),
            smart_str(ticket.assigned_to) if ticket.assigned_to else '',
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ticket.sla_deadline.strftime('%Y-%m-%d %H:%M'),
            smart_str('نعم' if ticket.is_overdue else 'لا')
        ])
    
    return response


@login_required
def get_notifications(request):
    """
    API للحصول على الإشعارات الجديدة
    """
    user = request.user
    
    # بناء الفلتر الشامل - يشمل التعيين المباشر والمتعدد والأقسام
    user_filter = Q(assigned_to=user) | Q(assigned_to_users=user)
    if user.department:
        user_filter |= Q(departments=user.department)
    
    # الطلبات الجديدة المعينة للمستخدم
    new_tickets = Ticket.objects.filter(
        user_filter,
        status='pending_ack'
    ).distinct().count()
    
    # الطلبات المتأخرة
    overdue_tickets = Ticket.objects.filter(
        user_filter,
        status__in=['new', 'pending_ack', 'in_progress'],
        sla_deadline__lt=timezone.now()
    ).distinct().count()
    
    return JsonResponse({
        'new_tickets': new_tickets,
        'overdue_tickets': overdue_tickets,
        'total': new_tickets + overdue_tickets
    })


@login_required
def export_ticket_pdf(request, pk):
    """تصدير الطلب إلى PDF مع دعم كامل للغة العربية"""
    from django.conf import settings
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    from io import BytesIO
    import arabic_reshaper
    from bidi.algorithm import get_display
    import os
    
    def format_arabic(text):
        """تنسيق النص العربي للعرض الصحيح"""
        if not text:
            return ""
        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    
    ticket = get_object_or_404(Ticket, pk=pk)
    actions = ticket.actions.all().order_by('-created_at')[:10]
    
    # التحقق من الصلاحيات - استخدام نفس منطق ticket_detail
    can_view = False
    
    if request.user.is_upper_management:
        can_view = True
    elif ticket.created_by == request.user:
        can_view = True
    elif ticket.assigned_to == request.user:
        can_view = True
    elif ticket.assigned_to_users.filter(id=request.user.id).exists():
        can_view = True
    elif ticket.department == request.user.department:
        can_view = True
    elif ticket.departments.filter(id=request.user.department.id if request.user.department else None).exists():
        can_view = True
    
    if not can_view:
        messages.error(request, 'ليس لديك صلاحية لتصدير هذا الطلب')
        return redirect('dashboard')
    
    # تسجيل الخط العربي
    font_name = 'Helvetica'  # افتراضي
    try:
        font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'NotoNaskhArabic-Regular.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            font_name = 'ArabicFont'
    except Exception as e:
        logger.warning(f'Could not load Arabic font: {e}')
    
    # إنشاء PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # أنماط مخصصة
    title_style = ParagraphStyle(
        'ArabicTitle',
        parent=styles['Heading1'],
        fontName=font_name,
        fontSize=20,
        textColor=colors.HexColor('#4c7eea'),
        alignment=TA_CENTER,
        spaceAfter=20,
    )
    
    heading_style = ParagraphStyle(
        'ArabicHeading',
        parent=styles['Heading2'],
        fontName=font_name,
        fontSize=14,
        alignment=TA_RIGHT,
        spaceAfter=10,
        textColor=colors.HexColor('#333333'),
        wordWrap='RTL',  # دعم RTL
        rightIndent=0,
    )
    
    normal_style = ParagraphStyle(
        'ArabicNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        alignment=TA_RIGHT,
        leading=16,
        wordWrap='RTL',  # دعم RTL
        rightIndent=0,
        leftIndent=0,
    )

    english_style = ParagraphStyle(
        'EnglishNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        alignment=TA_RIGHT,
        leading=16,
    )
    
    # العنوان الرئيسي
    elements.append(Paragraph(format_arabic("تقرير الطلب"), title_style))
    elements.append(Paragraph(f"Ticket #{ticket.id}", english_style))
    elements.append(Spacer(1, 15))
    
    # تحذير إذا متأخر
    if ticket.is_overdue:
        warning_style = ParagraphStyle(
            'Warning',
            parent=normal_style,
            textColor=colors.red,
            fontSize=12,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(format_arabic(f"⚠ تحذير: الطلب متأخر {ticket.hours_delayed:.1f} ساعة"), warning_style))
        elements.append(Spacer(1, 10))
    
    # معلومات الطلب
    elements.append(Paragraph(format_arabic("معلومات الطلب"), heading_style))
    
    # عكس ترتيب الأعمدة للقراءة من اليمين لليسار
    info_data = [
        [Paragraph(format_arabic(ticket.title), normal_style), Paragraph(format_arabic('العنوان:'), normal_style)],
        [Paragraph(format_arabic(ticket.get_status_display()), normal_style), Paragraph(format_arabic('الحالة:'), normal_style)],
        [Paragraph(format_arabic(ticket.get_priority_display()), normal_style), Paragraph(format_arabic('الأولوية:'), normal_style)],
        [Paragraph(format_arabic(ticket.created_by.get_full_name()), normal_style), Paragraph(format_arabic('المنشئ:'), normal_style)],
        [Paragraph(format_arabic(ticket.created_at.strftime('%Y-%m-%d %H:%M')), normal_style), Paragraph(format_arabic('تاريخ الإنشاء:'), normal_style)],
        [Paragraph(format_arabic(ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')), normal_style), Paragraph(format_arabic('الموعد النهائي:'), normal_style)],
    ]
    
    if ticket.assigned_to:
        info_data.append([
            Paragraph(format_arabic(ticket.assigned_to.get_full_name()), normal_style),
            Paragraph(format_arabic('المعين له:'), normal_style)
        ])
    
    if ticket.department:
        info_data.append([
            Paragraph(format_arabic(ticket.department.name), normal_style),
            Paragraph(format_arabic('القسم:'), normal_style)
        ])
    
    info_table = Table(info_data, colWidths=[4.5*inch, 1.5*inch], hAlign='RIGHT')
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))
    
    # الوصف
    elements.append(Paragraph(format_arabic("الوصف"), heading_style))
    desc_text = ticket.description[:300] + "..." if len(ticket.description) > 300 else ticket.description
    elements.append(Paragraph(format_arabic(desc_text), normal_style))
    elements.append(Spacer(1, 15))
    
    # التواريخ  
    elements.append(Paragraph(format_arabic("التواريخ"), heading_style))
    dates_data = [
        [Paragraph(format_arabic(ticket.created_at.strftime('%Y-%m-%d %H:%M')), normal_style), Paragraph(format_arabic('تاريخ الإنشاء:'), normal_style)],
        [Paragraph(format_arabic(ticket.sla_deadline.strftime('%Y-%m-%d %H:%M')), normal_style), Paragraph(format_arabic('الموعد النهائي:'), normal_style)],
    ]

    if ticket.resolved_at:
        dates_data.append([
            Paragraph(format_arabic(ticket.resolved_at.strftime('%Y-%m-%d %H:%M')), normal_style),
            Paragraph(format_arabic('تاريخ الحل:'), normal_style)
        ])

    dates_table = Table(dates_data, colWidths=[4.5*inch, 1.5*inch], hAlign='RIGHT')
    dates_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#f0f0f0')),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(dates_table)
    elements.append(Spacer(1, 15))
    
    # سجل الإجراءات
    if actions.exists():
        elements.append(Paragraph(format_arabic("آخر الإجراءات"), heading_style))
        
        # عكس ترتيب الأعمدة: التاريخ - المستخدم - النوع (من اليمين لليسار)
        actions_data = [[
            Paragraph(format_arabic('التاريخ'), normal_style),
            Paragraph(format_arabic('المستخدم'), normal_style),
            Paragraph(format_arabic('النوع'), normal_style),
        ]]
        for action in actions:
            actions_data.append([
                Paragraph(format_arabic(action.created_at.strftime('%Y-%m-%d %H:%M')), normal_style),
                Paragraph(format_arabic(action.user.get_full_name() if action.user else 'النظام'), normal_style),
                Paragraph(format_arabic(action.get_action_type_display()), normal_style),
            ])
        actions_table = Table(actions_data, colWidths=[2*inch, 2*inch, 2*inch], hAlign='RIGHT')
        actions_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4c7eea')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(actions_table)
    
    # التذييل
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle(
        'Footer',
        parent=normal_style,
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    elements.append(Paragraph(format_arabic("نظام إدارة الطلبات - قسم الحاسبة الإلكترونية"), footer_style))
    elements.append(Paragraph(f"تاريخ الطباعة: {timezone.now().strftime('%Y-%m-%d %H:%M')}", footer_style))
    
    # بناء PDF
    try:
        doc.build(elements)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}.pdf"'
        
        logger.info(f'PDF exported successfully for ticket {ticket.id}')
        return response
        
    except Exception as e:
        logger.error(f'Error generating PDF: {e}')
        messages.error(request, f'خطأ في تصدير PDF: {str(e)}')
        return redirect('ticket_detail', pk=pk)


@login_required
def return_ticket(request, pk):
    """
    إعادة/رفض الطلب من قبل القسم أو الموظف المعين
    """
    ticket = get_object_or_404(Ticket, pk=pk)
    
    # التحقق من الصلاحيات: فقط المعين له أو عضو في القسم المعين يمكنه إرجاع الطلب
    can_return = False
    
    if request.user.role in ['admin', 'president']: # الإدارة العليا يمكنها دائماً
        can_return = True
    elif ticket.assigned_to == request.user:
        can_return = True
    elif ticket.assigned_to_users.filter(id=request.user.id).exists():
        can_return = True
    elif request.user.department:
        # رئيس القسم أو العميد في القسم المعين
        if ticket.department == request.user.department and request.user.role in ['head', 'dean']:
            can_return = True
        # إذا كان القسم ضمن الأقسام المعنية والمستخدم رئيس/عميد
        elif ticket.departments.filter(id=request.user.department.id).exists() and request.user.role in ['head', 'dean']:
            can_return = True
            
    if not can_return:
        messages.error(request, 'ليس لديك صلاحية لإرجاع هذا الطلب')
        return redirect('ticket_detail', pk=pk)
        
    # لا يمكن إرجاع طلب مغلق أو محلول
    if ticket.status in ['resolved', 'closed', 'returned']:
        messages.error(request, 'لا يمكن إرجاع طلب منتهي أو معاد مسبقاً')
        return redirect('ticket_detail', pk=pk)
        
    if request.method == 'POST':
        form = ReturnTicketForm(request.POST)
        if form.is_valid():
            reason = form.cleaned_data['reason']
            
            # تحديث حالة الطلب
            ticket.status = 'returned'
            ticket.save()
            
            # تسجيل الإجراء
            TicketAction.objects.create(
                ticket=ticket,
                action_type='returned',
                user=request.user,
                notes=f"سبب الإرجاع: {reason}"
            )
            
            messages.success(request, 'تم إرجاع الطلب بنجاح')
            logger.info(f'Ticket #{ticket.id} returned by {request.user.username}')
            return redirect('ticket_list')
    else:
        form = ReturnTicketForm()
        
    return render(request, 'tickets/return_ticket.html', {
        'ticket': ticket,
        'form': form
    })

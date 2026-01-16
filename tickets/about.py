from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Ticket
from accounts.models import CustomUser, Department


@login_required
def about_system(request):
    """
    صفحة عن النظام - معلومات شاملة
    """
    # إحصائيات عامة
    total_tickets = Ticket.objects.count()
    total_users = CustomUser.objects.count()
    total_departments = Department.objects.count()
    resolved_tickets = Ticket.objects.filter(status__in=['resolved', 'closed']).count()
    
    # حساب نسبة الحل
    resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
    
    # معلومات النظام
    system_info = {
        'name': 'نظام ادارة جامعة الكنوز',
        'version': '2.0',
        'release_date': '2025-12-03',
        'developer': 'MUNTADHER HAZIM',
        'university': 'جامعة الكنوز',
        'department': 'قسم الحاسبة الإلكترونية',
    }
    
    # الميزات الرئيسية
    features = [
        {
            'icon': 'bi-lightning-charge-fill',
            'title': 'تصعيد تلقائي ذكي',
            'description': '4 مستويات تصعيد مع تحذيرات استباقية قبل انتهاء المهلة',
            'color': 'primary'
        },
        {
            'icon': 'bi-graph-up-arrow',
            'title': 'نظام النقاط الجزائية',
            'description': 'احتساب تلقائي للنقاط (1-10) حسب مدة التأخير',
            'color': 'danger'
        },
        {
            'icon': 'bi-radar',
            'title': 'مراقبة مباشرة',
            'description': 'لوحة تحكم real-time مع مؤشرات KPI متقدمة',
            'color': 'success'
        },
        {
            'icon': 'bi-file-earmark-bar-graph',
            'title': 'تقارير متقدمة',
            'description': 'تقارير شاملة مع تصدير Excel وPDF',
            'color': 'info'
        },
        {
            'icon': 'bi-shield-check',
            'title': 'نظام صلاحيات متقدم',
            'description': 'تحكم دقيق في الوصول حسب الدور والمستوى',
            'color': 'warning'
        },
        {
            'icon': 'bi-clock-history',
            'title': 'تتبع شامل',
            'description': 'تسجيل كامل لكل عملية دخول ونشاط',
            'color': 'secondary'
        },
    ]
    
    # التقنيات المستخدمة
    technologies = [
        {'name': 'Django', 'version': '5.1', 'icon': 'bi-code-square'},
        {'name': 'SQLite (dev) / PostgreSQL (prod)', 'version': '', 'icon': 'bi-database'},
        {'name': 'Celery', 'version': '5.4', 'icon': 'bi-gear-wide-connected'},
        {'name': 'Redis', 'version': '5.2', 'icon': 'bi-lightning'},
        {'name': 'Bootstrap', 'version': '5.3', 'icon': 'bi-palette'},
        {'name': 'Chart.js', 'version': '4.4', 'icon': 'bi-bar-chart'},
    ]
    
    context = {
        'system_info': system_info,
        'features': features,
        'technologies': technologies,
        'total_tickets': total_tickets,
        'total_users': total_users,
        'total_departments': total_departments,
        'resolution_rate': round(resolution_rate, 1),
    }
    
    return render(request, 'tickets/about_system.html', context)

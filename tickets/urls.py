from django.urls import path
from . import views
from . import reports
from . import about
from . import admin_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('acknowledge/', views.acknowledge_tickets, name='acknowledge_tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/acknowledge/', views.acknowledge_ticket_single, name='acknowledge_ticket_single'),
    path('tickets/<int:pk>/return/', views.return_ticket, name='return_ticket'),
    path('tickets/<int:pk>/close/', views.close_ticket, name='close_ticket'),
    path('tickets/<int:pk>/pdf/', views.export_ticket_pdf, name='export_ticket_pdf'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/export/', views.export_report, name='export_report'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    
    # نظام المراقبة المتقدم
    path('monitoring/', reports.monitoring_dashboard, name='monitoring_dashboard'),
    path('monitoring/api/', reports.monitoring_api, name='monitoring_api'),
    
    # التقارير المتقدمة
    path('reports/performance/', reports.performance_report, name='performance_report'),
    path('reports/performance/export/', reports.export_performance_excel, name='export_performance_excel'),
    path('reports/penalties/', reports.penalty_points_report, name='penalty_points_report'),
    
    # عن النظام
    path('about/', about.about_system, name='about_system'),
    
    # === الوظائف الجديدة ===
    
    # الطلبات المكتملة
    path('completed/', admin_views.completed_tickets, name='completed_tickets'),
    
    # حالة الإقرارات
    path('tickets/<int:pk>/ack-status/', admin_views.acknowledge_status, name='acknowledge_status'),
    
    # الإغلاق الإداري
    path('tickets/<int:pk>/admin-close/', admin_views.admin_close_ticket, name='admin_close_ticket'),
    
    # إعادة التعيين
    path('tickets/<int:pk>/reassign/', admin_views.reassign_ticket, name='reassign_ticket'),
    
    # API الإشعارات المحسّن
    path('api/notifications/enhanced/', admin_views.get_notifications_enhanced, name='get_notifications_enhanced'),
    
    # === تقرير المخالفات ===
    path('violations/', admin_views.violations_report, name='violations_report'),
    path('violations/export/', admin_views.export_violations_csv, name='export_violations_csv'),
    path('tickets/<int:pk>/mark-violation/', admin_views.mark_as_violation, name='mark_as_violation'),
    path('penalties/add/', admin_views.add_manual_penalty, name='add_manual_penalty'),
]

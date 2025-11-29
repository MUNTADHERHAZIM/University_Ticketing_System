from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('acknowledge/', views.acknowledge_tickets, name='acknowledge_tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/close/', views.close_ticket, name='close_ticket'),
    path('tickets/<int:pk>/pdf/', views.export_ticket_pdf, name='export_ticket_pdf'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/export/', views.export_report, name='export_report'),
    path('api/notifications/', views.get_notifications, name='get_notifications'),
]

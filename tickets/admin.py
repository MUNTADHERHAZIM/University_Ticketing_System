from django.contrib import admin
from .models import Ticket, TicketAction
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule, SolarSchedule, ClockedSchedule
from django_celery_beat.admin import PeriodicTaskAdmin

# Unregister the default PeriodicTask admin to override it
admin.site.unregister(PeriodicTask)

@admin.register(PeriodicTask)
class CustomPeriodicTaskAdmin(PeriodicTaskAdmin):
    fieldsets = (
        (None, {
            'fields': ('name', 'regtask', 'task', 'enabled', 'description',),
            'classes': ('extrapretty', 'wide'),
        }),
        ('الجدولة (Schedule)', {
            'fields': ('interval', 'crontab', 'solar', 'clocked', 'start_time', 'last_run_at', 'one_off'),
            'classes': ('extrapretty', 'wide'),
        }),
        ('المعاملات (Arguments)', {
            'fields': ('args', 'kwargs'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
        ('خيارات التنفيذ (Execution Options)', {
            'fields': ('expires', 'queue', 'exchange', 'routing_key', 'priority', 'headers'),
            'classes': ('extrapretty', 'wide', 'collapse', 'in'),
        }),
    )

class TicketActionInline(admin.TabularInline):
    model = TicketAction
    extra = 0
    readonly_fields = ['action_type', 'user', 'notes', 'created_at']
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = [
        'title', 
        'department', 
        'priority', 
        'status', 
        'assigned_to',
        'created_at',
        'sla_deadline',
        'is_overdue'
    ]
    list_filter = ['status', 'priority', 'department', 'escalation_level', 'created_at']
    search_fields = ['title', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at', 'sla_deadline', 'is_overdue', 'hours_delayed']
    inlines = [TicketActionInline]
    
    fieldsets = (
        ('معلومات أساسية', {
            'fields': ('title', 'description', 'priority')
        }),
        ('التعيين', {
            'fields': ('department', 'assigned_to', 'created_by')
        }),
        ('الحالة والتصعيد', {
            'fields': ('status', 'escalation_level')
        }),
        ('التواريخ', {
            'fields': ('created_at', 'updated_at', 'acknowledged_at', 'resolved_at', 'closed_at', 'sla_deadline')
        }),
        ('معلومات الإغلاق', {
            'fields': ('close_notes', 'close_attachments')
        }),
        ('تحليل SLA', {
            'fields': ('is_overdue', 'hours_delayed')
        }),
    )


@admin.register(TicketAction)
class TicketActionAdmin(admin.ModelAdmin):
    list_display = ['ticket', 'action_type', 'user', 'created_at']
    list_filter = ['action_type', 'created_at']
    search_fields = ['ticket__title', 'notes']
    readonly_fields = ['created_at']

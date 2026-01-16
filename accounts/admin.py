from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, PenaltyPoints, LoginHistory


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name', 'description']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'role', 'department', 'login_count', 'last_login_at']
    list_filter = ['role', 'department', 'is_active', 'is_staff']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    fieldsets = UserAdmin.fieldsets + (
        ('معلومات إضافية', {
            'fields': ('department', 'role', 'phone')
        }),
        ('معلومات تتبع الدخول', {
            'fields': ('first_login_at', 'last_login_at', 'last_activity_at', 'login_count'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['first_login_at', 'last_login_at', 'last_activity_at', 'login_count']


@admin.register(PenaltyPoints)
class PenaltyPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'points', 'reason', 'created_at']
    list_filter = ['created_at', 'department']
    search_fields = ['user__username', 'department__name', 'reason']
    date_hierarchy = 'created_at'


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'login_at', 'logout_at', 'ip_address', 'session_duration_display']
    list_filter = ['login_at', 'user']
    search_fields = ['user__username', 'ip_address']
    date_hierarchy = 'login_at'
    readonly_fields = ['user', 'login_at', 'logout_at', 'ip_address', 'user_agent', 'session_key']
    
    def session_duration_display(self, obj):
        """عرض مدة الجلسة بشكل مقروء"""
        duration = obj.session_duration
        if duration:
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            return f"{int(hours)}س {int(minutes)}د"
        return "نشط"
    session_duration_display.short_description = "مدة الجلسة"
    
    def has_add_permission(self, request):
        """منع إضافة سجلات يدوياً"""
        return False

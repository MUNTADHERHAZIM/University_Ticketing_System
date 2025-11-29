from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Department, CustomUser, PenaltyPoints


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'department', 'role', 'is_staff']
    list_filter = ['role', 'department', 'is_staff', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    
    fieldsets = UserAdmin.fieldsets + (
        ('معلومات إضافية', {'fields': ('department', 'role', 'phone')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('معلومات إضافية', {'fields': ('department', 'role', 'phone')}),
    )


@admin.register(PenaltyPoints)
class PenaltyPointsAdmin(admin.ModelAdmin):
    list_display = ['get_target', 'points', 'reason', 'created_at']
    list_filter = ['created_at']
    search_fields = ['reason', 'user__username', 'department__name']
    
    def get_target(self, obj):
        return obj.user if obj.user else obj.department
    get_target.short_description = 'الهدف'

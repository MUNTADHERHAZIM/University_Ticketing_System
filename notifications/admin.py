
from django.contrib import admin
from .models import GlobalMail, GlobalMailAttachment, Notification
class GlobalMailAttachmentInline(admin.TabularInline):
    model = GlobalMailAttachment
    extra = 1
    fields = ('file', 'uploaded_at')
    readonly_fields = ('uploaded_at',)


@admin.register(GlobalMail)
class GlobalMailAdmin(admin.ModelAdmin):
    list_display = ('title', 'mail_type', 'created_at', 'created_by', 'external_link')
    search_fields = ('title', 'message')
    list_filter = ('created_at', 'mail_type')
    inlines = [GlobalMailAttachmentInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'message', 'mail_type', 'external_link', 'created_by')
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('title', 'message', 'user__username', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'ticket')

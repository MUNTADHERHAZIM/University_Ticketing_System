from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

class GlobalMail(models.Model):
    MAIL_TYPES = [
        ('announcement', 'منشور'),
        ('alert', 'تنبيه'),
        ('event', 'فعالية'),
        ('info', 'معلومة'),
        ('other', 'أخرى'),
    ]
    title = models.CharField(max_length=200, verbose_name='عنوان البريد')
    message = models.TextField(verbose_name='محتوى البريد')
    mail_type = models.CharField(max_length=20, choices=MAIL_TYPES, default='announcement', verbose_name='نوع البريد')
    external_link = models.URLField(null=True, blank=True, verbose_name='رابط خارجي')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = 'بريد عام'
        verbose_name_plural = 'البريد العام'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class GlobalMailAttachment(models.Model):
    mail = models.ForeignKey(GlobalMail, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='global_mail_attachments/', verbose_name='مرفق (صورة أو PDF أو فيديو)')
    uploaded_at = models.DateTimeField(auto_now_add=True)




class Notification(models.Model):
    """
    نموذج الإشعارات الداخلية
    """
    NOTIFICATION_TYPES = [
        ('new_ticket', 'طلب جديد'),
        ('ticket_assigned', 'تم التعيين'),
        ('ticket_acknowledged', 'تم التأكيد'),
        ('ticket_escalated', 'تم التصعيد'),
        ('deadline_approaching', 'اقتراب الموعد'),
        ('ticket_commented', 'تعليق جديد'),
        ('ticket_closed', 'تم الإغلاق'),
        ('ticket_violated', 'تجاوز المهلة'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='المستخدم'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        verbose_name='نوع الإشعار'
    )
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='الرسالة')
    ticket = models.ForeignKey(
        'tickets.Ticket',  # تحديد اسم التطبيق بشكل صريح
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الطلب'
    )
    is_read = models.BooleanField(default=False, verbose_name='مقروء')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    
    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.title} - {self.user.get_full_name()}'
    
    @classmethod
    def create_notification(cls, user, notification_type, title, message, ticket=None):
        """
        إنشاء إشعار جديد
        """
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            ticket=ticket
        )
    
    @classmethod
    def mark_as_read(cls, user, notification_ids=None):
        """
        تحديد الإشعارات كمقروءة
        """
        notifications = cls.objects.filter(user=user, is_read=False)
        if notification_ids:
            notifications = notifications.filter(id__in=notification_ids)
        return notifications.update(is_read=True)
    
    @classmethod
    def get_unread_count(cls, user):
        """
        عدد الإشعارات غير المقروءة
        """
        return cls.objects.filter(user=user, is_read=False).count()

from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Ticket(models.Model):
    """
    نموذج الطلب/التذكرة
    """
    STATUS_CHOICES = [
        ('new', 'جديد'),
        ('pending_ack', 'بانتظار التأكيد'),
        ('in_progress', 'قيد المعالجة'),
        ('resolved', 'تم الحل'),
        ('closed', 'مغلق'),
        ('violated', 'مخالف (تجاوز المهلة)'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'عادي'),
        ('urgent', 'عاجل'),
        ('critical', 'حرج'),
    ]
    
    ESCALATION_CHOICES = [
        ('none', 'لا يوجد'),
        ('head', 'رئيس القسم'),
        ('dean', 'العميد'),
        ('president', 'رئيس الجامعة'),
    ]
    
    # معلومات أساسية
    title = models.CharField(max_length=200, verbose_name="العنوان")
    description = models.TextField(verbose_name="الوصف")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal', verbose_name="الأولوية")
    
    # العلاقات
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_tickets',
        verbose_name="المنشئ"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name="المعين له"
    )
    assigned_to_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='multi_assigned_tickets',
        verbose_name="المعينون لهم",
        blank=True
    )
    department = models.ForeignKey(
        'accounts.Department',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name="القسم المعني",
        null=True,
        blank=True
    )
    departments = models.ManyToManyField(
        'accounts.Department',
        related_name='multi_tickets',
        verbose_name="الأقسام المعنية",
        blank=True
    )
    
    # الحالة والتتبع
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name="الحالة")
    escalation_level = models.CharField(
        max_length=20,
        choices=ESCALATION_CHOICES,
        default='none',
        verbose_name="مستوى التصعيد"
    )
    
    # التواريخ والمهل
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاريخ التحديث")
    acknowledged_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ التأكيد")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الحل")
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name="تاريخ الإغلاق")
    sla_deadline = models.DateTimeField(verbose_name="الموعد النهائي (SLA)")
    
    # المرفقات (جديد)
    attachment = models.FileField(
        upload_to='ticket_attachments/',
        null=True,
        blank=True,
        verbose_name="مرفق مع الطلب"
    )
    
    # معلومات الإغلاق
    close_notes = models.TextField(blank=True, verbose_name="ملاحظات الإغلاق")
    close_attachments = models.FileField(
        upload_to='ticket_closures/',
        null=True,
        blank=True,
        verbose_name="مرفقات الإغلاق"
    )
    
    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'sla_deadline']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['assigned_to', 'status']),  # New: للبحث السريع عن طلبات الموظف
            models.Index(fields=['created_at', 'department']),  # New: للتقارير
            models.Index(fields=['priority', 'escalation_level']),  # New: للطلبات الحرجة
            models.Index(fields=['created_by', 'created_at']),  # New: لطلبات المستخدم
        ]
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        # حساب SLA deadline تلقائياً إذا لم يتم تعيينه
        if not self.pk and not self.sla_deadline:
            hours = settings.SLA_DEADLINES.get(self.priority, 24)
            self.sla_deadline = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """هل تجاوز الطلب المهلة؟"""
        if not self.sla_deadline:
            return False
        return timezone.now() > self.sla_deadline and self.status not in ['resolved', 'closed']
    
    @property
    def time_until_deadline(self):
        """الوقت المتبقي حتى المهلة"""
        if self.status in ['resolved', 'closed']:
            return None
        delta = self.sla_deadline - timezone.now()
        return delta if delta.total_seconds() > 0 else timedelta(0)
    
    @property
    def hours_delayed(self):
        """عدد ساعات التأخير"""
        if not self.is_overdue:
            return 0
        delta = timezone.now() - self.sla_deadline
        return delta.total_seconds() / 3600


class TicketAction(models.Model):
    """
    سجل الإجراءات على التذكرة
    """
    ACTION_TYPES = [
        ('created', 'تم الإنشاء'),
        ('assigned', 'تم التعيين'),
        ('acknowledged', 'تم التأكيد'),
        ('escalated', 'تم التصعيد'),
        ('reassigned', 'تم إعادة التعيين'),
        ('resolved', 'تم الحل'),
        ('closed', 'تم الإغلاق'),
        ('commented', 'تم التعليق'),
    ]
    
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name="الطلب"
    )
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, verbose_name="نوع الإجراء")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="المستخدم"
    )
    notes = models.TextField(blank=True, verbose_name="الملاحظات")
    attachment = models.FileField(
        upload_to='action_attachments/',
        null=True,
        blank=True,
        verbose_name="مرفق"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ")
    
    class Meta:
        verbose_name = "إجراء"
        verbose_name_plural = "الإجراءات"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.ticket.title} - {self.get_action_type_display()}"

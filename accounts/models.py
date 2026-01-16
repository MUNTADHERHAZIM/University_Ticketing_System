from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.Model):
    """
    يمثل قسم في الجامعة (المالية، التسجيل، العمادة، إلخ)
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="اسم القسم")
    description = models.TextField(blank=True, verbose_name="الوصف")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "قسم"
        verbose_name_plural = "الأقسام"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """
    نموذج المستخدم المخصص مع دعم الأقسام والأدوار
    """
    ROLE_CHOICES = [
        ('employee', 'موظف'),
        ('head', 'رئيس قسم'),
        ('dean', 'عميد'),
        ('president', 'رئيس جامعة'),
        ('admin', 'مدير نظام'),
        ('admin_assistant', 'مساعد إداري'),
        ('academic_assistant', 'مساعد علمي'),
    ]
    
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='users',
        verbose_name="القسم"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee', verbose_name="الدور")
    phone = models.CharField(max_length=20, blank=True, verbose_name="الهاتف")
    
    # حقول تتبع الدخول
    first_login_at = models.DateTimeField(null=True, blank=True, verbose_name="أول دخول")
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name="آخر دخول")
    last_activity_at = models.DateTimeField(null=True, blank=True, verbose_name="آخر نشاط")
    login_count = models.IntegerField(default=0, verbose_name="عدد مرات الدخول")
    
    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
        # Index for performance
        indexes = [
            models.Index(fields=['role'], name='user_role_idx'),
            models.Index(fields=['department'], name='user_dept_idx'),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    @property
    def is_head(self):
        return self.role == 'head'
    
    @property
    def is_dean(self):
        return self.role == 'dean'
    
    @property
    def is_president(self):
        return self.role == 'president'
    
    @property
    def is_admin_assistant(self):
        return self.role == 'admin_assistant'
    
    @property
    def is_academic_assistant(self):
        return self.role == 'academic_assistant'
    
    @property
    def is_upper_management(self):
        """التحقق من أن المستخدم من الإدارة العليا (يرى جميع الطلبات)"""
        return self.role in ['admin', 'president', 'admin_assistant', 'academic_assistant'] or self.is_superuser


class PenaltyPoints(models.Model):
    """
    سجل النقاط السلبية للموظف أو القسم
    """
    user = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='penalties',
        verbose_name="المستخدم"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='penalties',
        verbose_name="القسم"
    )
    points = models.IntegerField(default=0, verbose_name="النقاط السلبية")
    reason = models.TextField(verbose_name="السبب")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        verbose_name = "نقطة جزائية"
        verbose_name_plural = "النقاط الجزائية"
        ordering = ['-created_at']
    
    def __str__(self):
        target = self.user if self.user else self.department
        return f"{target} - {self.points} نقطة"


class LoginHistory(models.Model):
    """
    سجل تفصيلي لعمليات دخول المستخدمين
    """
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='login_history',
        verbose_name="المستخدم"
    )
    login_at = models.DateTimeField(auto_now_add=True, verbose_name="وقت الدخول")
    logout_at = models.DateTimeField(null=True, blank=True, verbose_name="وقت الخروج")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    user_agent = models.TextField(blank=True, verbose_name="معلومات المتصفح")
    session_key = models.CharField(max_length=40, blank=True, verbose_name="مفتاح الجلسة")
    
    class Meta:
        verbose_name = "سجل دخول"
        verbose_name_plural = "سجلات الدخول"
        ordering = ['-login_at']
        indexes = [
            models.Index(fields=['user', '-login_at']),
            models.Index(fields=['ip_address', '-login_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.login_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def session_duration(self):
        """مدة الجلسة"""
        if self.logout_at:
            return self.logout_at - self.login_at
        return None


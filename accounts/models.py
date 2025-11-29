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
    
    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"
    
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

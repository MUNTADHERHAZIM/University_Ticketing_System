from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
from .models import LoginHistory


def get_client_ip(request):
    """الحصول على عنوان IP الحقيقي للمستخدم"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class LoginTrackingMiddleware(MiddlewareMixin):
    """
    Middleware لتتبع دخول المستخدمين وآخر نشاط
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # تحديث آخر نشاط
            request.user.last_activity_at = timezone.now()
            request.user.save(update_fields=['last_activity_at'])
            
            # التحقق من أول دخول
            if not request.user.first_login_at:
                request.user.first_login_at = timezone.now()
                request.user.save(update_fields=['first_login_at'])
            
            # تسجيل الدخول الجديد إذا لم يكن هناك سجل حديث
            session_key = request.session.session_key
            if session_key:
                # التحقق من وجود سجل دخول نشط لهذه الجلسة
                recent_login = LoginHistory.objects.filter(
                    user=request.user,
                    session_key=session_key,
                    logout_at__isnull=True
                ).first()
                
                if not recent_login:
                    # إنشاء سجل دخول جديد
                    LoginHistory.objects.create(
                        user=request.user,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                        session_key=session_key
                    )
                    
                    # تحديث معلومات الدخول في نموذج المستخدم
                    request.user.last_login_at = timezone.now()
                    request.user.login_count += 1
                    request.user.save(update_fields=['last_login_at', 'login_count'])
        
        return None

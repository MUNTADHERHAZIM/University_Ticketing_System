from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from tickets.models import Ticket


class ForceAcknowledgmentMiddleware:
    """
    Middleware يمنع المستخدم من الوصول لأي صفحة
    حتى يؤكد استلام الطلبات المعينة له
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # قائمة الصفحات المستثناة من الفحص
        self.exempt_urls = [
            '/acknowledge/',
            '/logout/',
            '/admin/',
            '/static/',
            '/media/',
        ]
    
    def __call__(self, request):
        # تجاهل المستخدمين غير المسجلين
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # تجاهل الصفحات المستثناة
        if any(request.path.startswith(url) for url in self.exempt_urls):
            return self.get_response(request)
        
        # التحقق من وجود طلبات غير مؤكدة
        unacknowledged_tickets = Ticket.objects.filter(
            assigned_to=request.user,
            status='pending_ack',
            acknowledged_at__isnull=True
        ).exists()
        
        if unacknowledged_tickets:
            # إعادة التوجيه الإجباري لصفحة التأكيد
            return redirect('acknowledge_tickets')
        
        return self.get_response(request)

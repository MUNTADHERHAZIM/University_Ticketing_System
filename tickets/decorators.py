from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    ديكوريتر للتحقق من دور المستخدم
    
    الاستخدام:
    @role_required('president', 'admin')
    def my_view(request):
        ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if request.user.role not in roles:
                messages.error(request, 'ليس لديك صلاحية للوصول لهذه الصفحة')
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def admin_or_president_required(view_func):
    """
    ديكوريتر للتحقق من أن المستخدم إداري أو رئيس جامعة
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role not in ['president', 'admin']:
            messages.error(request, 'هذه الصفحة محصورة للمدراء فقط')
            raise PermissionDenied
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_view_reports(view_func):
    """
    ديكوريتر للتحقق من صلاحية عرض التقارير
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role not in ['president', 'admin', 'dean', 'head']:
            messages.error(request, 'ليس لديك صلاحية لعرض التقارير')
            raise PermissionDenied
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def can_export_data(view_func):
    """
    ديكوريتر للتحقق من صلاحية تصدير البيانات
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.role not in ['president', 'admin', 'dean', 'head']:
            messages.error(request, 'ليس لديك صلاحية لتصدير البيانات')
            raise PermissionDenied
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

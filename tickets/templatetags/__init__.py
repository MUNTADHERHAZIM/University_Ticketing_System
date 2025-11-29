from django import template

register = template.Library()


@register.filter(name='has_role')
def has_role(user, roles):
    """
    فلتر للتحقق من دور المستخدم
    الاستخدام: {% if user|has_role:"president,admin,dean" %}
    """
    if not user or not user.is_authenticated:
        return False
    
    role_list = [r.strip() for r in roles.split(',')]
    return user.role in role_list


@register.filter(name='can_view_reports')
def can_view_reports(user):
    """
    يمكنه عرض التقارير؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin', 'dean', 'head']


@register.filter(name='can_export')
def can_export(user):
    """
    يمكنه تصدير البيانات؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin', 'dean', 'head']


@register.filter(name='can_manage_users')
def can_manage_users(user):
    """
    يمكنه إدارة المستخدمين؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin']


@register.filter(name='is_admin_or_president')
def is_admin_or_president(user):
    """
    هل هو إداري أو رئيس؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin']

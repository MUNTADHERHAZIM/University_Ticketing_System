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


@register.filter(name='can_export_data')
def can_export_data(user):
    """
    يمكنه تصدير البيانات؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin', 'dean', 'head', 'employee']


@register.filter(name='is_admin_or_president')
def is_admin_or_president(user):
    """
    هل هو إداري أو رئيس؟
    """
    if not user or not user.is_authenticated:
        return False
    
    return user.role in ['president', 'admin']


@register.filter(name='can_acknowledge')
def can_acknowledge(user, ticket):
    """
    هل يمكن للمستخدم تأكيد استلام التذكرة أو العمل عليها؟
    """
    if not user or not user.is_authenticated:
        return False
        
    # الإدارة العليا دائماً يمكنها ذلك
    if user.role in ['admin', 'president']:
        return True
        
    # الموظف المعين مباشرة
    if ticket.assigned_to == user:
        return True
        
    # الموظف المعين ضمن مجموعة
    if ticket.assigned_to_users.filter(id=user.id).exists():
        return True
        
    # رئيس القسم أو العميد للقسم المعني
    if ticket.department == user.department and user.role in ['head', 'dean']:
        return True
        
    # رئيس القسم أو العميد للأقسام المعنية المتعددة
    if ticket.departments.filter(id=user.department_id).exists() and user.role in ['head', 'dean']:
        return True
        
    return False

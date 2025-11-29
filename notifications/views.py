from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification
from .forms import NotificationForm
import logging

logger = logging.getLogger('tickets')

# ---------------------------------------------------------------------------
# List notifications (page view)
# ---------------------------------------------------------------------------
@login_required
def notifications_list(request):
    """قائمة الإشعارات للمستخدم الحالي."""
    notifications = Notification.objects.filter(user=request.user).select_related('ticket')[:50]
    context = {
        'notifications': notifications,
        'unread_count': Notification.get_unread_count(request.user),
    }
    return render(request, 'notifications/list.html', context)

# ---------------------------------------------------------------------------
# Create a new notification (staff)
# ---------------------------------------------------------------------------
@login_required
def create_notification(request):
    """إنشاء إشعار جديد (الموظفون فقط)."""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            notification = form.save(commit=False)
            notification.user = request.user
            notification.save()
            return redirect('notifications_list')
    else:
        form = NotificationForm()
    return render(request, 'notifications/create.html', {'form': form})
@login_required
def notifications_api(request):
    """API للحصول على الإشعارات (AJAX)."""
    notifications = Notification.objects.filter(
        user=request.user,
        is_read=False,
    ).select_related('ticket')[:10]

    data = {
        'count': Notification.get_unread_count(request.user),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'ticket_id': n.ticket.id if n.ticket else None,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
                'icon': get_notification_icon(n.notification_type),
                'color': get_notification_color(n.notification_type),
            }
            for n in notifications
        ],
    }
    return JsonResponse(data)

# ---------------------------------------------------------------------------
# Mark selected notifications as read (POST)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def mark_as_read(request):
    """تحديد الإشعارات كمقروءة (محددة أو جميعها)."""
    notification_ids = request.POST.getlist('notification_ids[]')
    if notification_ids:
        Notification.mark_as_read(request.user, notification_ids)
    else:
        Notification.mark_as_read(request.user)
    logger.info(f'User {request.user.id} marked notifications as read')
    return JsonResponse({'success': True})

# ---------------------------------------------------------------------------
# Mark all notifications as read (POST)
# ---------------------------------------------------------------------------
@login_required
@require_POST
def mark_all_as_read(request):
    """تحديد جميع الإشعارات كمقروءة."""
    Notification.mark_as_read(request.user)
    logger.info(f'User {request.user.id} marked all notifications as read')
    return JsonResponse({'success': True})

# ---------------------------------------------------------------------------
# Helper: icon & color per notification type
# ---------------------------------------------------------------------------
def get_notification_icon(notification_type):
    """إرجاع أيقونة Bootstrap حسب نوع الإشعار."""
    icons = {
        'new_ticket': 'bi-file-earmark-plus',
        'ticket_assigned': 'bi-person-check',
        'ticket_acknowledged': 'bi-check-circle',
        'ticket_escalated': 'bi-arrow-up-circle',
        'deadline_approaching': 'bi-clock-history',
        'ticket_commented': 'bi-chat-dots',
        'ticket_closed': 'bi-check2-circle',
        'ticket_violated': 'bi-exclamation-triangle',
    }
    return icons.get(notification_type, 'bi-bell')

def get_notification_color(notification_type):
    """إرجاع لون Bootstrap حسب نوع الإشعار."""
    colors = {
        'new_ticket': 'primary',
        'ticket_assigned': 'info',
        'ticket_acknowledged': 'success',
        'ticket_escalated': 'warning',
        'deadline_approaching': 'warning',
        'ticket_commented': 'secondary',
        'ticket_closed': 'success',
        'ticket_violated': 'danger',
    }
    return colors.get(notification_type, 'secondary')


@login_required
def edit_notification(request, pk):
    """Edit an existing notification (staff only)."""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return redirect('notifications_list')
    if request.method == 'POST':
        form = NotificationForm(request.POST, instance=notification)
        if form.is_valid():
            form.save()
            return redirect('notifications_list')
    else:
        form = NotificationForm(instance=notification)
    return render(request, 'notifications/edit.html', {'form': form, 'notification': notification})

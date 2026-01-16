// ===== تحسينات الإشعارات المتقدمة =====

function renderNotificationsList(notifications) {
    const container = document.getElementById('notificationsContainer');
    container.innerHTML = '';

    if (notifications.length === 0) {
        container.innerHTML = `
            <li class="dropdown-item text-center py-4">
                <i class="bi bi-bell-slash fs-1 text-muted d-block mb-2"></i>
                <span class="text-muted">لا توجد إشعارات جديدة</span>
            </li>`;
        return;
    }

    notifications.forEach(n => {
        const li = document.createElement('li');

        // تحديد نوع الإشعار والأيقونة واللون
        let notifType = 'info';
        let icon = 'bi-info-circle';
        let bgColor = '#e0f2fe';
        let borderColor = '#0ea5e9';
        let iconColor = '#0ea5e9';

        if (n.title.includes('إغلاق') || n.title.includes('مكتمل') || n.title.includes('تم')) {
            notifType = 'success';
            icon = 'bi-check-circle-fill';
            bgColor = '#dcfce7';
            borderColor = '#22c55e';
            iconColor = '#22c55e';
        } else if (n.title.includes('متأخر') || n.title.includes('مخالفة') || n.title.includes('تحذير')) {
            notifType = 'danger';
            icon = 'bi-exclamation-triangle-fill';
            bgColor = '#fee2e2';
            borderColor = '#ef4444';
            iconColor = '#ef4444';
        } else if (n.title.includes('جديد') || n.title.includes('طلب')) {
            notifType = 'primary';
            icon = 'bi-ticket-perforated-fill';
            bgColor = '#dbeafe';
            borderColor = '#3b82f6';
            iconColor = '#3b82f6';
        }

        // تنسيق الوقت
        const timeAgo = formatTimeAgo(n.created_at);

        li.className = 'notification-item';
        li.style.cssText = `
            border-right: 4px solid ${borderColor};
            background: ${bgColor};
            margin: 4px 8px;
            border-radius: 8px;
            padding: 12px;
            cursor: pointer;
            transition: all 0.3s ease;
        `;

        li.innerHTML = `
            <div class="d-flex align-items-start gap-3">
                <div class="notification-icon" style="color: ${iconColor}; font-size: 1.5rem;">
                    <i class="bi ${icon}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start mb-1">
                        <strong style="color: #1f2937; font-size: 0.95rem;">${n.title}</strong>
                        <span class="badge ${getBadgeClass(notifType)}" style="font-size: 0.7rem; padding: 2px 6px;">
                            ${getNotifLabel(notifType)}
                        </span>
                    </div>
                    <p style="margin: 4px 0; color: #6b7280; font-size: 0.85rem; line-height: 1.4;">
                        ${n.message}
                    </p>
                    <div class="d-flex justify-content-between align-items-center mt-2">
                        <small style="color: #9ca3af; font-size: 0.75rem;">
                            <i class="bi bi-clock"></i> ${timeAgo}
                        </small>
                        ${n.ticket_id ? `
                            <a href="/tickets/${n.ticket_id}/" class="btn btn-sm" 
                               style="background: ${iconColor}; color: white; padding: 2px 8px; font-size: 0.75rem; border-radius: 4px;">
                                <i class="bi bi-eye"></i> عرض
                            </a>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;

        // تأثيرات hover
        li.addEventListener('mouseenter', function () {
            this.style.transform = 'translateX(-3px)';
            this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
        });

        li.addEventListener('mouseleave', function () {
            this.style.transform = 'translateX(0)';
            this.style.boxShadow = 'none';
        });

        // النقر على الإشعار
        if (n.ticket_id) {
            li.addEventListener('click', function (e) {
                if (!e.target.closest('a')) {
                    window.location.href = `/tickets/${n.ticket_id}/`;
                }
            });
        }

        container.appendChild(li);
    });
}

// دالة لتنسيق الوقت (منذ كم)
function formatTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);

    if (seconds < 60) return 'الآن';
    if (seconds < 3600) return `منذ ${Math.floor(seconds / 60)} دقيقة`;
    if (seconds < 86400) return `منذ ${Math.floor(seconds / 3600)} ساعة`;
    if (seconds < 604800) return `منذ ${Math.floor(seconds / 86400)} يوم`;
    return date.toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' });
}

// دالة للحصول على class للbadge
function getBadgeClass(type) {
    const classes = {
        'success': 'bg-success',
        'danger': 'bg-danger',
        'primary': 'bg-primary',
        'info': 'bg-info'
    };
    return classes[type] || 'bg-secondary';
}

// دالة للحصول على تسمية النوع
function getNotifLabel(type) {
    const labels = {
        'success': 'مكتمل',
        'danger': 'مهم',
        'primary': 'جديد',
        'info': 'معلومة'
    };
    return labels[type] || 'إشعار';
}

// تصميم محسن لعداد الإشعارات
function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationCount');
    if (count > 0) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = 'inline';
        badge.style.animation = 'pulse-badge 0.5s ease';
    } else {
        badge.style.display = 'none';
    }
}

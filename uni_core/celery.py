import os
from celery import Celery
from celery.schedules import crontab

# تعيين إعدادات Django الافتراضية لبرنامج celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uni_core.settings')

app = Celery('uni_core')

# استخدام namespace CELERY لجميع الإعدادات المتعلقة بـ celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# تحميل المهام (tasks) من جميع التطبيقات المسجلة
app.autodiscover_tasks()

# جدولة المهام الدورية
app.conf.beat_schedule = {
    'check-sla-violations-every-10-minutes': {
        'task': 'tickets.tasks.check_sla_violations',
        'schedule': crontab(minute='*/10'),  # كل 10 دقائق
    },
    'auto-reassign-overdue-tickets': {
        'task': 'tickets.tasks.auto_reassign_tickets',
        'schedule': crontab(hour='*/6'),  # كل 6 ساعات
    },
    'send-daily-report': {
        'task': 'tickets.tasks.send_daily_report',
        'schedule': crontab(hour=10, minute=0),  # كل يوم الساعة 10 صباحاً
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

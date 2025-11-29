# دليل تشغيل المهام الآلية (Celery & Redis)

## نظرة عامة

النظام يحتوي على **3 مهام آلية** حرجة لعمل السياسات الصارمة:
1. ✅ فحص انتهاكات SLA (كل 10 دقائق)
2. ✅ إعادة التعيين التلقائي (كل 6 ساعات)
3. ✅ التقرير اليومي (الساعة 10 صباحاً)

---

## تثبيت Redis

### على Windows:
```powershell
# تحميل Redis من:
# https://github.com/microsoftarchive/redis/releases

# أو استخدام Chocolatey:
choco install redis-64

# أو استخدام WSL:
wsl
sudo apt-get install redis-server
```

### على Linux/Mac:
```bash
# Ubuntu/Debian:
sudo apt-get install redis-server

# Mac:
brew install redis
```

---

## تشغيل النظام الكامل

### الطريقة 1: تشغيل يدوي (4 نوافذ Terminal)

#### نافذة 1: Django Server
```bash
cd "c:/Users/munta/Desktop/قسم الحاسبة الالكترونية"
python manage.py runserver
```
✅ سيعمل على: http://localhost:8000

---

#### نافذة 2: Redis Server
```bash
redis-server
```
✅ سيعمل على: localhost:6379

---

#### نافذة 3: Celery Worker
```bash
cd "c:/Users/munta/Desktop/قسم الحاسبة الالكترونية"
celery -A uni_core worker -l info --pool=solo
```
> ملاحظة: `--pool=solo` ضروري على Windows

✅ سترى رسالة:
```
[tasks]
  . tickets.tasks.auto_reassign_tickets
  . tickets.tasks.check_sla_violations
  . tickets.tasks.send_daily_report

[2025-11-22 15:00:00] [INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-11-22 15:00:00] [INFO/MainProcess] mingle: searching for neighbors
[2025-11-22 15:00:00] [INFO/MainProcess] celery@hostname ready.
```

---

#### نافذة 4: Celery Beat (المهام المجدولة)
```bash
cd "c:/Users/munta/Desktop/قسم الحاسبة الالكترونية"
celery -A uni_core beat -l info
```

✅ سترى الجدول الزمني:
```
[2025-11-22 15:00:00] Scheduler: Sending due task check-sla-violations-every-10-minutes
[2025-11-22 21:00:00] Scheduler: Sending due task auto-reassign-overdue-tickets
[2025-11-23 10:00:00] Scheduler: Sending due task send-daily-report
```

---

### الطريقة 2: استخدام ملف Batch (Windows)

قم بإنشاء ملف `start_all.bat`:

```batch
@echo off
start "Django Server" cmd /k "cd /d c:\Users\munta\Desktop\قسم الحاسبة الالكترونية && python manage.py runserver"
timeout /t 2
start "Redis Server" cmd /k "redis-server"
timeout /t 2
start "Celery Worker" cmd /k "cd /d c:\Users\munta\Desktop\قسم الحاسبة الالكترونية && celery -A uni_core worker -l info --pool=solo"
timeout /t 2
start "Celery Beat" cmd /k "cd /d c:\Users\munta\Desktop\قسم الحاسبة الالكترونية && celery -A uni_core beat -l info"
```

---

## التحقق من عمل المهام

### اختبار يدوي للمهمة:

في shell Python:
```bash
python manage.py shell
```

ثم:
```python
from tickets.tasks import check_sla_violations

# تشغيل المهمة يدوياً
result = check_sla_violations.delay()

# التحقق من النتيجة
print(result.get())
# المخرج: "تم معالجة X تذكرة مخالفة"
```

---

## جدولة المهام (celery.py)

```python
app.conf.beat_schedule = {
    # مهمة 1: فحص SLA كل 10 دقائق
    'check-sla-violations-every-10-minutes': {
        'task': 'tickets.tasks.check_sla_violations',
        'schedule': crontab(minute='*/10'),
    },
    
    # مهمة 2: إعادة التعيين كل 6 ساعات
    'auto-reassign-overdue-tickets': {
        'task': 'tickets.tasks.auto_reassign_tickets',
        'schedule': crontab(hour='*/6'),
    },
    
    # مهمة 3: التقرير اليومي الساعة 10 صباحاً
    'send-daily-report': {
        'task': 'tickets.tasks.send_daily_report',
        'schedule': crontab(hour=10, minute=0),
    },
}
```

---

## مراقبة المهام

### Flower (واجهة مراقبة Celery)

تثبيت:
```bash
pip install flower
```

تشغيل:
```bash
celery -A uni_core flower
```

الوصول: http://localhost:5555

---

## حل المشاكل الشائعة

### مشكلة 1: `ModuleNotFoundError: No module named 'celery'`
**الحل:**
```bash
pip install celery redis django-celery-beat
```

---

### مشكلة 2: `Error: Can't connect to Redis`
**الحل:**
1. تأكد أن Redis يعمل:
   ```bash
   redis-cli ping
   # يجب أن يرجع: PONG
   ```

2. إذا لم يعمل، شغّل Redis:
   ```bash
   redis-server
   ```

---

### مشكلة 3: Celery لا يعمل على Windows
**الحل:**
استخدم العلم `--pool=solo`:
```bash
celery -A uni_core worker -l info --pool=solo
```

---

### مشكلة 4: المهام لا تنفذ تلقائياً
**الحل:**
تأكد من تشغيل **Celery Beat** (ليس فقط Worker):
```bash
celery -A uni_core beat -l info
```

---

## اختبار سريع للنظام الكامل

### 1. إنشاء طلب متأخر يدوياً:

```python
python manage.py shell
```

```python
from tickets.models import Ticket
from accounts.models import CustomUser, Department
from django.utils import timezone
from datetime import timedelta

# إنشاء طلب بمهلة منتهية
dept = Department.objects.first()
user = CustomUser.objects.filter(role='employee').first()
creator = CustomUser.objects.filter(role='president').first()

ticket = Ticket.objects.create(
    title='اختبار SLA',
    description='طلب لاختبار النظام',
    priority='critical',
    department=dept,
    assigned_to=user,
    created_by=creator,
    status='in_progress',
    # مهلة منتهية (قبل ساعتين)
    sla_deadline=timezone.now() - timedelta(hours=2)
)

print(f"تم إنشاء طلب #{ticket.id}")
print(f"متأخر: {ticket.is_overdue}")
print(f"ساعات التأخير: {ticket.hours_delayed}")
```

---

### 2. انتظر 10 دقائق أو شغّل المهمة يدوياً:

```python
from tickets.tasks import check_sla_violations
result = check_sla_violations.delay()
print(result.get())
```

---

### 3. تحقق من النتيجة:

```python
ticket.refresh_from_db()
print(f"الحالة الجديدة: {ticket.status}")  # يجب أن تكون 'violated'
print(f"مستوى التصعيد: {ticket.escalation_level}")
```

---

## الإعدادات في settings.py

```python
# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Baghdad'

# SLA Deadlines (in hours)
SLA_DEADLINES = {
    'normal': 24,
    'urgent': 4,
    'critical': 2,
}

# Auto-reassign after 48 hours
AUTO_REASSIGN_AFTER_HOURS = 48
```

---

## الخلاصة

لتشغيل النظام **بكامل قوته الصارمة**، يجب تشغيل **4 عمليات**:

1. ✅ Django Server - الواجهة والمنطق
2. ✅ Redis - قاعدة بيانات المهام
3. ✅ Celery Worker - تنفيذ المهام
4. ✅ Celery Beat - جدولة المهام

بدون Celery، النظام سيعمل لكن **بدون**:
- ❌ فحص SLA التلقائي
- ❌ التصعيد التلقائي
- ❌ إعادة التعيين التلقائي
- ❌ التقارير اليومية

**النظام يعمل لكن بدون الصرامة الكاملة!** 🔴

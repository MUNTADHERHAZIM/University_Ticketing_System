# 🚀 دليل نشر المشروع للإنتاج (Production Deployment Guide)

## ✅ الميزات المكتملة

- ✅ نظام البريد الإلكتروني (يحتاج تكوين SMTP)
- ✅ تصدير PDF بالعربية (يعمل بشكل كامل)
- ✅ تصميم متجاوب 100%
- ✅ نظام الطلبات الكامل
- ✅ نظام الإشعارات
- ✅ التقارير والإحصائيات
- ✅ نظام الصلاحيات

---

## ⚠️ خطوات ضرورية قبل النشر

### 1. تشغيل Migrations

```bash
python manage.py migrate
```

> **مهم:** تم اكتشاف migrations جديدة لـ `django_celery_beat`. يجب تشغيلها.

---

### 2. إعدادات الأمان في `settings.py`

#### أ) تعطيل وضع التطوير

```python
# قبل النشر
DEBUG = False

# السماح للنطاقات المحددة فقط
ALLOWED_HOSTS = [
    'yourdomain.com',
    'www.yourdomain.com',
    'your-server-ip',
]
```

#### ب) المفتاح السري (SECRET_KEY)

**لا تنشر المشروع بالمفتاح الحالي!**

طريقة آمنة:

```python
# settings.py
import os
from pathlib import Path

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'your-temporary-key-for-dev')

# لتوليد مفتاح جديد:
# python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

على السيرفر، أضف متغير البيئة:
```bash
export DJANGO_SECRET_KEY='your-generated-secret-key-here'
```

#### ج) إعدادات الأمان الأخرى

```python
# settings.py

# HTTPS إجباري
SECURE_SSL_REDIRECT = True  # فقط إذا كان لديك شهادة SSL
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# حماية من XSS
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # سنة
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF trusted origins
CSRF_TRUSTED_ORIGINS = [
    'https://yourdomain.com',
    'https://www.yourdomain.com',
]
```

---

### 3. قاعدة البيانات (Production)

**SQLite غير مناسب للإنتاج!** استخدم PostgreSQL:

#### أ) تثبيت PostgreSQL

```bash
pip install psycopg2-binary
```

#### ب) تحديث settings.py

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'ticketing_db'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'your-password'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}
```

#### ج) نقل البيانات (Migration)

```bash
# تصدير من SQLite
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.permission \
    --indent 4 > backup.json

# استيراد إلى PostgreSQL
python manage.py loaddata backup.json
```

---

### 4. إعدادات البريد الإلكتروني (SMTP)

حالياً يستخدم `console.EmailBackend`. للإنتاج:

```python
# settings.py

# Gmail مثال
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'your-app-password')
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
```

> **ملاحظة:** لـ Gmail، استخدم [App Password](https://support.google.com/accounts/answer/185833) وليس كلمة المرور العادية.

---

### 5. جمع الملفات الثابتة (Static Files)

```bash
# إنشاء مجلد للملفات الثابتة
python manage.py collectstatic --noinput
```

في `settings.py`:

```python
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# للملفات المُرفعة
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
```

---

### 6. خادم الويب (Web Server)

**لا تستخدم** `runserver` في الإنتاج!

#### خيار 1: Gunicorn + Nginx

**أ) تثبيت Gunicorn:**

```bash
pip install gunicorn
```

**ب) تشغيل:**

```bash
gunicorn uni_core.wsgi:application --bind 0.0.0.0:8000
```

**ج) Nginx Configuration:**

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

### 7. Celery (للمهام الخلفية)

يجب تشغيل Celery worker و beat:

```bash
# Worker
celery -A uni_core worker -l info

# Beat (للمهام المجدولة)
celery -A uni_core beat -l info
```

للإنتاج، استخدم supervisor أو systemd لتشغيلهم تلقائياً.

---

### 8. Redis (للتخزين المؤقت و Celery)

```bash
# تثبيت
pip install redis

# تشغيل Redis server
redis-server
```

---

### 9. متطلبات إضافية

تأكد من وجود جميع المكتبات في `requirements.txt`:

```bash
pip freeze > requirements.txt
```

يجب أن يشمل:
- Django==5.1
- celery
- redis
- psycopg2-binary
- gunicorn
- weasyprint
- reportlab
- arabic-reshaper
- python-bidi
- django-templated-email

---

## 📝 Checklist قبل النشر

### إعدادات Django
- [ ] `DEBUG = False`
- [ ] `ALLOWED_HOSTS` محدد
- [ ] `SECRET_KEY` في متغير بيئة
- [ ] قاعدة بيانات PostgreSQL
- [ ] `collectstatic` تم تشغيله
- [ ] `migrate` تم تشغيله

### الأمان
- [ ] HTTPS مُفعّل
- [ ] SECURE_SSL_REDIRECT
- [ ] Session/CSRF cookies secure
- [ ] HSTS مُفعّل
- [ ] كلمات المرور قوية

### البريد الإلكتروني
- [ ] SMTP مُكوّن بشكل صحيح
- [ ] تم اختبار إرسال البريد
- [ ] App Password لـ Gmail (إن وُجد)

### الخوادم
- [ ] Gunicorn مثبت ويعمل
- [ ] Nginx مُكوّن
- [ ] Redis يعمل
- [ ] Celery worker يعمل
- [ ] Celery beat يعمل

### النسخ الاحتياطي
- [ ] نسخة احتياطية من قاعدة البيانات
- [ ] نسخة احتياطية من الملفات المُرفعة
- [ ] خطة للنسخ الاحتياطي التلقائي

---

## 🔧 متغيرات البيئة الموصى بها

إنشاء ملف `.env` (لا تنشره على Git!):

```bash
# .env
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

DB_NAME=ticketing_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432

EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

استخدم `python-decouple` أو `django-environ`:

```bash
pip install python-decouple
```

```python
# settings.py
from decouple import config

SECRET_KEY = config('DJANGO_SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])
```

---

## 📊 المراقبة والصيانة

### 1. Logging

```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/errors.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

### 2. Monitoring Tools

- **Sentry**: لتتبع الأخطاء
- **New Relic / DataDog**: لمراقبة الأداء
- **Uptime Robot**: للتحقق من عمل الموقع

---

## 🚀 سيناريو النشر السريع

### على Ubuntu Server

```bash
# 1. تحديث النظام
sudo apt update && sudo apt upgrade -y

# 2. تثبيت المتطلبات
sudo apt install python3-pip python3-venv nginx postgresql redis-server

# 3. إعداد PostgreSQL
sudo -u postgres createdb ticketing_db
sudo -u postgres createuser ticketing_user

# 4. استنساخ المشروع
git clone your-repo-url
cd your-project

# 5. البيئة الافتراضية
python3 -m venv venv
source venv/bin/activate

# 6. تثبيت المكتبات
pip install -r requirements.txt

# 7. تكوين البيئة
cp .env.example .env
# عدّل .env بالقيم الصحيحة

# 8. Django setup
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser

# 9. تشغيل الخوادم
gunicorn uni_core.wsgi:application --bind 0.0.0.0:8000 &
celery -A uni_core worker -l info &
celery -A uni_core beat -l info &
```

---

## ⚡ الخلاصة

### ✅ جاهز الآن:
- الكود البرمجي كامل
- جميع الميزات تعمل
- PDF بالعربية يعمل بنجاح

### ⚠️ يحتاج قبل النشر:
1. **تشغيل migrations الجديدة**
2. **تكوين الأمان** (DEBUG, SECRET_KEY, HTTPS)
3. **PostgreSQL** بدلاً من SQLite
4. **SMTP** للبريد الإلكتروني
5. **Gunicorn + Nginx** بدلاً من runserver
6. **Celery** للمهام الخلفية

---

## 📞 دعم إضافي

إذا احتجت مساعدة في:
- إعداد السيرفر
- تكوين Nginx
- مشاكل النشر
- أي تحسينات

**المشروع جاهز تقنياً، لكن يحتاج إعداد البيئة الإنتاجية!** 🚀

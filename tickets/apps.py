from django.apps import AppConfig


class TicketsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tickets'

    def ready(self):
        # استيراد الإشارات (signals)
        import tickets.signals
        
        # تعريب أسماء تطبيق المهام الدورية (Celery Beat)
        try:
            from django.apps import apps
            from django_celery_beat.models import (
                PeriodicTask, IntervalSchedule, CrontabSchedule, 
                SolarSchedule, ClockedSchedule
            )

            # تعريب اسم التطبيق في القائمة الجانبية
            beat_app_config = apps.get_app_config('django_celery_beat')
            beat_app_config.verbose_name = "إدارة المهام التلقائية"

            # تعريب النماذج (Models) بأسماء مفهومة
            
            # PeriodicTask -> المهام المجدولة
            PeriodicTask._meta.verbose_name = "مهمة مجدولة"
            PeriodicTask._meta.verbose_name_plural = "المهام المجدولة (الرئيسية)"
            
            # تعريب حقول PeriodicTask
            PeriodicTask._meta.get_field('name').verbose_name = "اسم المهمة"
            PeriodicTask._meta.get_field('task').verbose_name = "المهمة البرمجية (Task)"
            
            PeriodicTask._meta.get_field('interval').verbose_name = "تكرار كل فترة (Interval)"
            PeriodicTask._meta.get_field('interval').help_text = "اختر هذا الخيار إذا كنت تريد تكرار المهمة كل فترة زمنية محددة (مثلاً كل دقيقة). اترك الحقول الأخرى فارغة."
            
            PeriodicTask._meta.get_field('crontab').verbose_name = "تكرار في وقت محدد (Crontab)"
            PeriodicTask._meta.get_field('crontab').help_text = "اختر هذا الخيار إذا كنت تريد تكرار المهمة في أوقات محددة (مثلاً كل يوم جمعة الساعة 5). اترك الحقول الأخرى فارغة."
            
            PeriodicTask._meta.get_field('solar').verbose_name = "حدث شمسي (Solar)"
            PeriodicTask._meta.get_field('solar').help_text = "للأحداث المرتبطة بالشمس. اترك الحقول الأخرى فارغة."
            
            PeriodicTask._meta.get_field('clocked').verbose_name = "موعد محدد (Clocked)"
            PeriodicTask._meta.get_field('clocked').help_text = "اختر هذا الخيار لتشغيل المهمة في تاريخ ووقت محدد بالضبط. اترك الحقول الأخرى فارغة."
            
            PeriodicTask._meta.get_field('args').verbose_name = "معاملات (Arguments)"
            PeriodicTask._meta.get_field('kwargs').verbose_name = "معاملات مفتاحية (Keyword Arguments)"
            PeriodicTask._meta.get_field('queue').verbose_name = "طابور التنفيذ (Queue)"
            PeriodicTask._meta.get_field('exchange').verbose_name = "التبادل (Exchange)"
            PeriodicTask._meta.get_field('routing_key').verbose_name = "مفتاح التوجيه (Routing Key)"
            PeriodicTask._meta.get_field('expires').verbose_name = "تاريخ الانتهاء"
            PeriodicTask._meta.get_field('enabled').verbose_name = "مفعلة؟"
            PeriodicTask._meta.get_field('last_run_at').verbose_name = "آخر تشغيل"
            PeriodicTask._meta.get_field('total_run_count').verbose_name = "عدد مرات التشغيل"
            PeriodicTask._meta.get_field('date_changed').verbose_name = "تاريخ التعديل"
            PeriodicTask._meta.get_field('description').verbose_name = "الوصف"
            PeriodicTask._meta.get_field('start_time').verbose_name = "تاريخ البدء"
            PeriodicTask._meta.get_field('one_off').verbose_name = "تشغيل لمرة واحدة فقط"

            # IntervalSchedule -> تكرار كل فترة
            IntervalSchedule._meta.verbose_name = "تكرار كل فترة"
            IntervalSchedule._meta.verbose_name_plural = "تكرار كل فترة (مثلاً: كل 5 دقائق)"

            # CrontabSchedule -> تكرار في أوقات محددة
            CrontabSchedule._meta.verbose_name = "تكرار في وقت محدد"
            CrontabSchedule._meta.verbose_name_plural = "تكرار في أوقات محددة (مثلاً: كل يوم جمعة)"

            # SolarSchedule -> أحداث شمسية
            SolarSchedule._meta.verbose_name = "حدث شمسي"
            SolarSchedule._meta.verbose_name_plural = "أحداث مرتبطة بالشمس (شروق/غروب)"

            # ClockedSchedule -> تشغيل لمرة واحدة
            ClockedSchedule._meta.verbose_name = "موعد لمرة واحدة"
            ClockedSchedule._meta.verbose_name_plural = "تشغيل لمرة واحدة فقط"

        except ImportError:
            pass

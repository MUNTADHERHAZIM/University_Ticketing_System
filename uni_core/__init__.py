# هذا سيتأكد من تحميل تطبيق Celery دائماً عند بدء Django
from .celery import app as celery_app

__all__ = ('celery_app',)

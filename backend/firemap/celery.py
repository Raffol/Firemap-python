import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'firemap.settings')

app = Celery('firemap')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'refresh-weather-nightly': {
        'task': 'fires.tasks.refresh_all_weather',
        'schedule': crontab(hour=1, minute=0),
    },
    'compute-nesterov-nightly': {
        'task': 'fires.tasks.compute_nesterov_today',
        'schedule': crontab(hour=2, minute=0),
    },
}

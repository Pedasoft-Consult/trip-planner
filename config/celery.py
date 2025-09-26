"""
Celery configuration for the ELD Trip Planner project.
"""
import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

app = Celery('eld_trip_planner')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery beat schedule for periodic tasks
app.conf.beat_schedule = {
    'update-trip-status': {
        'task': 'apps.trips.tasks.update_trip_status',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'cleanup-old-trips': {
        'task': 'apps.trips.tasks.cleanup_old_trips',
        'schedule': 86400.0,  # Run daily
    },
    'generate-trip-reports': {
        'task': 'apps.trips.tasks.generate_trip_reports',
        'schedule': 86400.0,  # Run daily
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

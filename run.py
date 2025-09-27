# run.py
import os
from django.core.wsgi import get_wsgi_application

# Detect environment (default to production on Vercel)
DJANGO_ENV = os.getenv("DJANGO_ENV", "production")

if DJANGO_ENV == "development":
    settings_module = "config.settings.development"
else:
    settings_module = "config.settings.production"

os.environ.setdefault("DJANGO_SETTINGS_MODULE", settings_module)

# Expose Django app for Vercel
app = get_wsgi_application()

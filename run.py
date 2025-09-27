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

# Run collectstatic automatically on Vercel
if os.getenv("VERCEL", None):
    from django.core.management import call_command
    try:
        print("Running collectstatic on Vercel...")
        call_command("collectstatic", interactive=False, verbosity=0)
    except Exception as e:
        print(f"Static collection skipped: {e}")

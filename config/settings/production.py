import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ImproperlyConfigured(f"The {name} environment variable is required.")
    return value


SECRET_KEY = required_environment_variable("DJANGO_SECRET_KEY")
DEBUG = False

render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
configured_hosts = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
ALLOWED_HOSTS = [host for host in [render_hostname, *configured_hosts] if host]

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Set RENDER_EXTERNAL_HOSTNAME or DJANGO_ALLOWED_HOSTS in production."
    )

DATABASES = {
    "default": dj_database_url.parse(
        required_environment_variable("DATABASE_URL"),
        conn_max_age=600,
        conn_health_checks=True,
        ssl_require=True,
    )
}

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False

CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]

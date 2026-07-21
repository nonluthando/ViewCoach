import os

import dj_database_url

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv(
            "TEST_DATABASE_URL",
            os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/adaptive_interview_coach",
            ),
        ),
        conn_max_age=0,
    )
}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "whitenoise.middleware.WhiteNoiseMiddleware"
]

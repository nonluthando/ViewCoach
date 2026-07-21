import os

import dj_database_url

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

DATABASES = {
    "default": dj_database_url.parse(
        os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/adaptive_interview_coach",
        ),
        conn_max_age=0,
    )
}

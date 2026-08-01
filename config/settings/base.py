import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "unsafe-local-development-key",
)
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "apps.core.apps.CoreConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.questions.apps.QuestionsConfig",
    "apps.reviews.apps.ReviewsConfig",
    "apps.roadmaps.apps.RoadmapsConfig",
    "apps.planner.apps.PlannerConfig",
    "apps.interviews.apps.InterviewsConfig",
    "apps.goals.apps.GoalsConfig",
    "apps.evidence.apps.EvidenceConfig",
    "apps.knowledge.apps.KnowledgeConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": ("django.contrib.auth.password_validation.UserAttributeSimilarityValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

PLANNER_USE_OPTIMISER = os.getenv(
    "PLANNER_USE_OPTIMISER",
    "true",
).strip().casefold() in {
    "1",
    "true",
    "yes",
    "on",
}
PLANNER_OPTIMISER_TIME_LIMIT_SECONDS = float(
    os.getenv(
        "PLANNER_OPTIMISER_TIME_LIMIT_SECONDS",
        "0.25",
    )
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
)
RAG_EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "gemini-embedding-001",
)
RAG_EMBEDDING_DIMENSIONS = int(
    os.getenv(
        "RAG_EMBEDDING_DIMENSIONS",
        "1536",
    )
)
RAG_CHUNK_MAX_CHARACTERS = int(
    os.getenv(
        "RAG_CHUNK_MAX_CHARACTERS",
        "2400",
    )
)
RAG_CHUNK_OVERLAP_CHARACTERS = int(
    os.getenv(
        "RAG_CHUNK_OVERLAP_CHARACTERS",
        "300",
    )
)
RAG_RETRIEVAL_LIMIT = int(
    os.getenv(
        "RAG_RETRIEVAL_LIMIT",
        "6",
    )
)
RAG_MINIMUM_SIMILARITY = float(
    os.getenv(
        "RAG_MINIMUM_SIMILARITY",
        "0.25",
    )
)


RAG_GENERATION_MODEL = os.getenv(
    "RAG_GENERATION_MODEL",
    "gemini-3.5-flash-lite",
)
RAG_MAX_OUTPUT_TOKENS = int(
    os.getenv(
        "RAG_MAX_OUTPUT_TOKENS",
        "700",
    )
)
RAG_MAX_REQUESTS_PER_WINDOW = int(
    os.getenv(
        "RAG_MAX_REQUESTS_PER_WINDOW",
        "10",
    )
)
RAG_RATE_LIMIT_WINDOW_SECONDS = int(
    os.getenv(
        "RAG_RATE_LIMIT_WINDOW_SECONDS",
        "600",
    )
)

QUESTION_GENERATION_MODEL = os.getenv(
    "QUESTION_GENERATION_MODEL",
    RAG_GENERATION_MODEL,
)
QUESTION_GENERATION_MAX_OUTPUT_TOKENS = int(
    os.getenv("QUESTION_GENERATION_MAX_OUTPUT_TOKENS", "1800")
)
QUESTION_GENERATION_MIN_NOTE_CHARACTERS = int(
    os.getenv("QUESTION_GENERATION_MIN_NOTE_CHARACTERS", "80")
)

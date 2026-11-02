"""Настройки Voltra API. Один модуль, всё переменное читается из окружения / .env."""

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DEBUG", default=False)

SECRET_KEY = env("SECRET_KEY", default="")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("SECRET_KEY обязателен при DEBUG=False")
    SECRET_KEY = "django-insecure-dev-only-key"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
# Render сам сообщает внешний адрес сервиса — добавляем его, чтобы не дублировать в ALLOWED_HOSTS.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default="")
if RENDER_EXTERNAL_HOSTNAME and RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")
SITE_NAME = "Voltra"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    # сторонние
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "drf_spectacular",
    # свои
    "apps.users",
    "apps.catalog",
    "apps.wishlist",
    "apps.cart",
    "apps.orders",
    "apps.payments",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
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

# ---------- База данных ----------

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Пользователи и пароли ----------

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Вход без подтверждённого email → 403 email_not_verified.
EMAIL_VERIFICATION_REQUIRED = env.bool("EMAIL_VERIFICATION_REQUIRED", default=True)

# ---------- Локализация ----------

LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

# ---------- Статика и медиа ----------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))

# Медиа (фото товаров, категорий, отзывов): локально — папка media/, в проде без постоянного
# диска — S3-совместимое хранилище (Cloudflare R2), см. docs/decisions.md «Деплой».
MEDIA_STORAGE = env("MEDIA_STORAGE", default="local")  # local | s3
if MEDIA_STORAGE == "s3":
    DEFAULT_STORAGE = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET"),
            "endpoint_url": env("S3_ENDPOINT_URL"),  # https://<account_id>.r2.cloudflarestorage.com
            "access_key": env("S3_ACCESS_KEY_ID"),
            "secret_key": env("S3_SECRET_ACCESS_KEY"),
            "region_name": env("S3_REGION", default="auto"),
            # Публичный домен бакета (pub-….r2.dev или свой): ссылки без подписи и срока жизни.
            "custom_domain": env("S3_PUBLIC_DOMAIN"),
            "querystring_auth": False,
            "default_acl": None,
            "file_overwrite": False,
            "signature_version": "s3v4",
        },
    }
elif MEDIA_STORAGE == "local":
    DEFAULT_STORAGE = {"BACKEND": "django.core.files.storage.FileSystemStorage"}
else:
    raise ImproperlyConfigured("MEDIA_STORAGE должен быть local или s3")
# Отдавать media/ самим Django (при local-хранилище и в проде) — запасной вариант без R2:
# работает, но файлы пропадут при перезапуске сервиса без постоянного диска.
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=MEDIA_STORAGE == "local")

STORAGES = {
    "default": DEFAULT_STORAGE,
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

# ---------- Почта ----------

vars().update(env.email_url("EMAIL_URL", default="consolemail://"))
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Voltra <no-reply@voltra.kz>")

# ---------- DRF ----------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        *(["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

# ---------- Лимиты частоты на эндпоинтах авторизации ----------

# Счётчики лежат в кэше Django (CACHES ниже). THROTTLE_RELAXED (по умолчанию = DEBUG) включает
# мягкие лимиты для локальной разработки и e2e-сценариев фронта; в pytest они ослабляются в
# conftest.py. Явные THROTTLE_* важнее; пустое значение отключает лимит.
THROTTLE_RELAXED = env.bool("THROTTLE_RELAXED", default=DEBUG)
RELAXED_THROTTLE_RATE = "1000/min"
AUTH_THROTTLE_RATES = {
    scope: env(
        f"THROTTLE_{scope.upper()}", default=RELAXED_THROTTLE_RATE if THROTTLE_RELAXED else rate
    )
    for scope, rate in {
        "login": "10/min",
        "register": "10/hour",
        "password_reset": "5/hour",
        "promo": "30/min",  # POST /cart/apply-promo/ — против перебора кодов
    }.items()
}

CACHES = {"default": env.cache_url("CACHE_URL", default="locmemcache://")}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_DAYS", default=14)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Refresh-токен живёт только в httpOnly-cookie. В проде фронт и бэк на разных доменах,
# поэтому SameSite=None + Secure; локально (localhost:3000 ↔ localhost:8000) хватает Lax.
REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
REFRESH_COOKIE_SECURE = env.bool("REFRESH_COOKIE_SECURE", default=not DEBUG)
REFRESH_COOKIE_SAMESITE = env("REFRESH_COOKIE_SAMESITE", default="Lax" if DEBUG else "None")

SPECTACULAR_SETTINGS = {
    "TITLE": "Voltra API",
    "DESCRIPTION": "API интернет-магазина Voltra",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------- CORS / CSRF ----------

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[FRONTEND_URL])
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        *CORS_ALLOWED_ORIGINS,
        # админка на домене самого API
        *([f"https://{RENDER_EXTERNAL_HOSTNAME}"] if RENDER_EXTERNAL_HOSTNAME else []),
    ],
)

# ---------- Магазин ----------

# Должно совпадать с DELIVERY во frontend/src/lib/config.ts.
COURIER_PRICE = Decimal(env("COURIER_PRICE", default="1500"))
FREE_SHIPPING_FROM = Decimal(env("FREE_SHIPPING_FROM", default="100000"))
# Номер заказа: VT-{ORDER_NUMBER_START + id}, например VT-100245.
ORDER_NUMBER_START = env.int("ORDER_NUMBER_START", default=100000)

# Stripe необязателен: без ключа онлайн-оплата выключена, остальное работает (см. README).
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_CURRENCY = env("STRIPE_CURRENCY", default="kzt").lower()
# Меньше этой суммы (в валюте магазина) онлайн-оплату не предлагаем: у Stripe есть минимальный
# платёж (~0,50 USD в пересчёте в валюту счёта выплат), см. docs/decisions.md.
STRIPE_MIN_AMOUNT = Decimal(env("STRIPE_MIN_AMOUNT", default="500"))
# Сколько живёт ссылка на оплату (Stripe: от 30 минут до 24 часов).
STRIPE_SESSION_MINUTES = env.int("STRIPE_SESSION_MINUTES", default=60)

# ---------- Прод ----------

if not DEBUG:
    # TLS завершается на прокси Render/Railway; схему берём из X-Forwarded-Proto.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # Редирект на https и HSTS — за прокси уже есть https; включаются по желанию.
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}

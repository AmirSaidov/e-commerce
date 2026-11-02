"""Настройки прода: хранилище медиа R2, хост Render, отдача media/ без постоянного диска."""

import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import RequestFactory
from django.urls import resolve
from django.views.static import serve
from storages.backends.s3 import S3Storage

from apps.core.media import absolute_media_url

PROD_ENV = {
    "DEBUG": "False",
    "SECRET_KEY": "prod-like-secret-key-for-settings-test-0123456789",
    "DATABASE_URL": "sqlite:///:memory:",
    "RENDER_EXTERNAL_HOSTNAME": "voltra-api.onrender.com",
    "FRONTEND_URL": "https://voltra.vercel.app",
    "CORS_ALLOWED_ORIGINS": "https://voltra.vercel.app",
    "MEDIA_STORAGE": "s3",
    "S3_BUCKET": "voltra-media",
    "S3_ENDPOINT_URL": "https://account.r2.cloudflarestorage.com",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_PUBLIC_DOMAIN": "pub-123.r2.dev",
}

PROBE = """
import json, django
django.setup()
from django.conf import settings as s
print(json.dumps({
    "allowed_hosts": s.ALLOWED_HOSTS,
    "csrf": s.CSRF_TRUSTED_ORIGINS,
    "cors": s.CORS_ALLOWED_ORIGINS,
    "storage": s.STORAGES["default"]["BACKEND"],
    "static": s.STORAGES["staticfiles"]["BACKEND"],
    "serve_media": s.SERVE_MEDIA,
    "cookie": [s.REFRESH_COOKIE_SECURE, s.REFRESH_COOKIE_SAMESITE],
    "proxy_ssl": list(s.SECURE_PROXY_SSL_HEADER),
    "throttle_login": s.AUTH_THROTTLE_RATES["login"],
}))
"""


def prod_settings(**overrides):
    """Настройки в отдельном процессе: модуль settings читает окружение при импорте."""
    env = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", **PROD_ENV, **overrides}
    env.pop("THROTTLE_RELAXED", None)
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_production_settings_on_render():
    s = prod_settings()

    assert "voltra-api.onrender.com" in s["allowed_hosts"]
    assert s["cors"] == ["https://voltra.vercel.app"]
    assert s["csrf"] == ["https://voltra.vercel.app", "https://voltra-api.onrender.com"]
    assert s["storage"] == "storages.backends.s3.S3Storage"
    assert s["static"] == "whitenoise.storage.CompressedManifestStaticFilesStorage"
    assert s["serve_media"] is False  # медиа отдаёт R2, не Django
    assert s["cookie"] == [True, "None"]  # refresh-cookie: Secure; SameSite=None
    assert s["proxy_ssl"] == ["HTTP_X_FORWARDED_PROTO", "https"]
    assert s["throttle_login"] == "10/min"  # в проде лимиты строгие


def test_production_with_local_media_serves_it():
    assert prod_settings(MEDIA_STORAGE="local")["serve_media"] is True


def test_r2_urls_are_public_and_absolute():
    storage = S3Storage(
        bucket_name="voltra-media",
        endpoint_url="https://account.r2.cloudflarestorage.com",
        access_key="key",
        secret_key="secret",
        region_name="auto",
        custom_domain="pub-123.r2.dev",
        querystring_auth=False,
    )
    request = RequestFactory().get("/", HTTP_HOST="voltra-api.onrender.com")

    url = storage.url("products/apple-iphone-16-pro-1.svg")

    assert url == "https://pub-123.r2.dev/products/apple-iphone-16-pro-1.svg"
    # абсолютный URL хранилища не переписывается на домен API
    assert request.build_absolute_uri(url) == url


def test_local_media_url_is_absolute(settings):
    settings.ALLOWED_HOSTS = ["voltra-api.onrender.com"]
    request = RequestFactory().get("/", HTTP_HOST="voltra-api.onrender.com", secure=True)

    url = absolute_media_url(request, "products/x.svg")

    assert url == "https://voltra-api.onrender.com/media/products/x.svg"


def test_media_route_exists_for_local_storage():
    if not settings.SERVE_MEDIA:
        return
    assert resolve("/media/products/x.svg").func is serve

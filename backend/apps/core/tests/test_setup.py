import pytest
from django.conf import settings
from django.urls import reverse

FRONT = "http://localhost:3000"


@pytest.fixture
def cors(settings):
    settings.CORS_ALLOWED_ORIGINS = [FRONT]


def test_health(api_client):
    res = api_client.get(reverse("health"))

    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_cors_preflight_allows_frontend_with_credentials(client, cors):
    res = client.options(
        "/api/v1/health/",
        HTTP_ORIGIN=FRONT,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
    )

    assert res.status_code == 200
    assert res["Access-Control-Allow-Origin"] == FRONT
    assert res["Access-Control-Allow-Credentials"] == "true"
    assert "authorization" in res["Access-Control-Allow-Headers"]


def test_cors_rejects_foreign_origin(client, cors):
    res = client.get("/api/v1/health/", HTTP_ORIGIN="https://evil.example")

    assert "Access-Control-Allow-Origin" not in res


def test_locale_settings():
    assert settings.LANGUAGE_CODE == "ru"
    assert settings.TIME_ZONE == "Asia/Almaty"
    assert settings.USE_TZ is True


def test_openapi_schema_is_served(api_client):
    res = api_client.get("/api/schema/")

    assert res.status_code == 200

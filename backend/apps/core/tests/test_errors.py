import pytest

pytestmark = pytest.mark.urls("apps.core.tests.urls")


def assert_error_shape(data):
    assert set(data) == {"detail", "code", "fields"}
    assert isinstance(data["detail"], str) and data["detail"]
    assert isinstance(data["code"], str) and data["code"]
    assert isinstance(data["fields"], dict)


def test_field_errors_go_to_fields_in_russian(api_client):
    res = api_client.post("/api/v1/form/", {"email": "не-email"}, format="json")

    assert res.status_code == 400
    assert_error_shape(res.data)
    assert res.data["code"] == "validation_error"
    assert res.data["detail"] == "Проверьте правильность заполнения полей."
    assert res.data["fields"]["email"] == ["Введите правильный адрес электронной почты."]
    assert res.data["fields"]["password"] == ["Обязательное поле."]


def test_nested_errors_are_flattened(api_client):
    payload = {
        "email": "a@b.kz",
        "password": "x",
        "items": [{"variant_id": 1, "quantity": 1}, {"variant_id": 2, "quantity": 0}],
    }
    res = api_client.post("/api/v1/form/", payload, format="json")

    assert res.status_code == 400
    assert list(res.data["fields"]) == ["items.1.quantity"]
    assert "больше либо равно 1" in res.data["fields"]["items.1.quantity"][0]


def test_non_field_error_goes_to_detail_with_its_code(api_client):
    res = api_client.post(
        "/api/v1/form/", {"email": "a@b.kz", "password": "mismatch"}, format="json"
    )

    assert res.status_code == 400
    assert res.data == {
        "detail": "Пароли не совпадают.",
        "code": "password_mismatch",
        "fields": {},
    }


def test_plain_validation_error(api_client):
    res = api_client.post("/api/v1/plain/")

    assert res.status_code == 400
    assert res.data == {"detail": "Промокод не найден", "code": "promo_not_found", "fields": {}}


def test_api_exception_with_code(api_client):
    res = api_client.post("/api/v1/api-exception/")

    assert res.status_code == 400
    assert res.data["code"] == "order_not_cancellable"
    assert res.data["detail"] == "Заказ нельзя отменить."


def test_api_exception_with_custom_status(api_client):
    res = api_client.post("/api/v1/forbidden/")

    assert res.status_code == 403
    assert res.data["code"] == "email_not_verified"


def test_not_authenticated_is_401_in_russian(api_client):
    res = api_client.get("/api/v1/private/")

    assert res.status_code == 401
    assert_error_shape(res.data)
    assert res.data["code"] == "not_authenticated"
    assert res.data["detail"] == "Учетные данные не были предоставлены."


def test_invalid_bearer_token_is_401(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer garbage")
    res = api_client.get("/api/v1/private/")

    assert res.status_code == 401
    assert_error_shape(res.data)
    assert res.data["code"] == "token_not_valid"
    assert res.data["fields"] == {}


@pytest.mark.parametrize(
    ("url", "status", "code"),
    [("/api/v1/django-404/", 404, "not_found"), ("/api/v1/django-403/", 403, "permission_denied")],
)
def test_django_exceptions_are_converted(api_client, url, status, code):
    res = api_client.get(url)

    assert res.status_code == status
    assert_error_shape(res.data)
    assert res.data["code"] == code


def test_method_not_allowed(api_client):
    res = api_client.get("/api/v1/form/")

    assert res.status_code == 405
    assert_error_shape(res.data)
    assert res.data["code"] == "method_not_allowed"


def test_malformed_json(api_client):
    res = api_client.post("/api/v1/form/", "{oops", content_type="application/json")

    assert res.status_code == 400
    assert_error_shape(res.data)
    assert res.data["detail"] == "Не удалось разобрать тело запроса."
    assert res.data["code"] == "parse_error"


def test_unhandled_exception_is_json_500(api_client):
    res = api_client.get("/api/v1/crash/")

    assert res.status_code == 500
    assert res.json() == {
        "detail": "Внутренняя ошибка сервера. Попробуйте позже.",
        "code": "server_error",
        "fields": {},
    }


def test_unknown_url_is_json_404(api_client):
    res = api_client.get("/api/v1/does-not-exist/")

    assert res.status_code == 404
    assert res.json() == {"detail": "Страница не найдена.", "code": "not_found", "fields": {}}

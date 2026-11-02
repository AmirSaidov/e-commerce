from datetime import timedelta

import pytest
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.users.tests.factories import PASSWORD

pytestmark = pytest.mark.django_db

USER_FIELDS = {"id", "email", "first_name", "last_name", "phone", "avatar", "is_email_verified"}


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/v1/users/me/"),
        ("patch", "/api/v1/users/me/"),
        ("post", "/api/v1/users/me/password/"),
        ("get", "/api/v1/users/me/addresses/"),
        ("post", "/api/v1/users/me/addresses/"),
        ("get", "/api/v1/wishlist/"),
        ("post", "/api/v1/wishlist/"),
        ("delete", "/api/v1/wishlist/1/"),
    ],
)
def test_requires_authentication(api_client, method, url):
    res = getattr(api_client, method)(url)

    # 401 (а не 403), чтобы фронт попробовал обновить access-токен
    assert res.status_code == 401
    assert res.data["code"] == "not_authenticated"


def test_expired_access_token_is_401(api_client, user):
    token = AccessToken.for_user(user)
    token.set_exp(lifetime=-timedelta(seconds=1))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    res = api_client.get("/api/v1/users/me/")

    assert res.status_code == 401
    assert res.data["code"] == "token_not_valid"


# ---------- /users/me/ ----------


def test_get_me(auth_client, user):
    res = auth_client.get("/api/v1/users/me/")

    assert res.status_code == 200
    assert res.json() == {
        "id": user.id,
        "email": user.email,
        "first_name": "Айбек",
        "last_name": "Сапаров",
        "phone": "",
        "avatar": None,
        "is_email_verified": True,
    }


def test_login_then_me_like_frontend(api_client, user):
    # stores/auth.ts: login → users.me()
    access = api_client.post(
        "/api/v1/auth/login/", {"email": user.email, "password": PASSWORD}, format="json"
    ).data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    assert api_client.get("/api/v1/users/me/").data["email"] == user.email


def test_patch_me(auth_client, user):
    res = auth_client.patch(
        "/api/v1/users/me/",
        {"first_name": " Данияр ", "last_name": "Касымов", "phone": "+7 (700) 123-45-67"},
        format="json",
    )

    assert res.status_code == 200
    assert set(res.json()) == USER_FIELDS
    assert res.data["first_name"] == "Данияр"
    assert res.data["phone"] == "+7 (700) 123-45-67"
    user.refresh_from_db()
    assert (user.first_name, user.last_name) == ("Данияр", "Касымов")


def test_patch_me_partial_and_clear_phone(auth_client, user):
    user.phone = "+77001234567"
    user.save()

    res = auth_client.patch("/api/v1/users/me/", {"phone": ""}, format="json")

    assert res.status_code == 200
    assert res.data["phone"] == "" and res.data["first_name"] == "Айбек"


def test_patch_me_ignores_read_only_fields(auth_client, user):
    res = auth_client.patch(
        "/api/v1/users/me/",
        {"email": "hacker@evil.example", "is_email_verified": False, "id": 999},
        format="json",
    )

    assert res.status_code == 200
    user.refresh_from_db()
    assert user.email.endswith("@voltra.kz") and user.is_email_verified and user.id != 999


@pytest.mark.parametrize(
    ("payload", "field", "message"),
    [
        ({"phone": "12-34"}, "phone", "Введите телефон, например +7 700 123 45 67"),
        ({"phone": "+7 700 abc 45 67"}, "phone", "Введите телефон, например +7 700 123 45 67"),
        ({"first_name": "  "}, "first_name", "Это поле не может быть пустым."),
        ({"last_name": "x" * 51}, "last_name", None),
    ],
)
def test_patch_me_validation(auth_client, payload, field, message):
    res = auth_client.patch("/api/v1/users/me/", payload, format="json")

    assert res.status_code == 400
    assert list(res.data["fields"]) == [field]
    if message:
        assert res.data["fields"][field] == [message]


def test_put_me_not_allowed(auth_client):
    assert auth_client.put("/api/v1/users/me/", {}, format="json").status_code == 405


# ---------- /users/me/password/ ----------


def test_change_password(auth_client, user, api_client):
    other_device = RefreshToken.for_user(user)

    res = auth_client.post(
        "/api/v1/users/me/password/",
        {"old_password": PASSWORD, "new_password": "New-Galaxy-S25"},
        format="json",
    )

    assert res.status_code == 204
    user.refresh_from_db()
    assert user.check_password("New-Galaxy-S25")

    # этот браузер получил новый refresh в cookie и остаётся в системе
    cookie = res.cookies["refresh_token"]
    assert cookie["httponly"] and cookie["path"] == "/api/v1/auth/"
    api_client.cookies["refresh_token"] = cookie.value
    assert api_client.post("/api/v1/auth/refresh/").status_code == 200

    # другие устройства разлогинены
    api_client.cookies["refresh_token"] = str(other_device)
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401
    assert OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True).count() == 1


def test_change_password_wrong_old(auth_client, user):
    res = auth_client.post(
        "/api/v1/users/me/password/",
        {"old_password": "wrong", "new_password": "New-Galaxy-S25"},
        format="json",
    )

    assert res.status_code == 400
    assert res.data["fields"] == {"old_password": ["Текущий пароль указан неверно."]}
    user.refresh_from_db()
    assert user.check_password(PASSWORD)


def test_change_password_weak_new(auth_client):
    res = auth_client.post(
        "/api/v1/users/me/password/",
        {"old_password": PASSWORD, "new_password": "12345678"},
        format="json",
    )

    assert res.status_code == 400
    assert list(res.data["fields"]) == ["new_password"]
    assert "Введённый пароль состоит только из цифр." in res.data["fields"]["new_password"]


def test_change_password_similar_to_email(auth_client, user):
    res = auth_client.post(
        "/api/v1/users/me/password/",
        {"old_password": PASSWORD, "new_password": user.email},
        format="json",
    )

    assert res.status_code == 400
    assert any("похож" in m for m in res.data["fields"]["new_password"])


def test_change_password_required_fields(auth_client):
    res = auth_client.post("/api/v1/users/me/password/", {}, format="json")

    assert res.status_code == 400
    assert set(res.data["fields"]) == {"old_password", "new_password"}

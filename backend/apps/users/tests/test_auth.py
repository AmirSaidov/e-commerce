import re
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings as django_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from apps.users.models import User
from apps.users.tests.factories import PASSWORD, UserFactory
from apps.users.tokens import email_verification_token, encode_uid, password_reset_token

pytestmark = pytest.mark.django_db

COOKIE = "refresh_token"
FRONT = "http://localhost:3000"


@pytest.fixture(autouse=True)
def _auth_settings(settings):
    settings.FRONTEND_URL = FRONT
    settings.CORS_ALLOWED_ORIGINS = [FRONT]
    settings.EMAIL_VERIFICATION_REQUIRED = True
    settings.REFRESH_COOKIE_SECURE = False
    settings.REFRESH_COOKIE_SAMESITE = "Lax"


def login(client, email, password=PASSWORD):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")


def link_from(mail):
    url = re.search(r"https?://\S+", mail.body).group(0)
    parts = urlsplit(url)
    query = {key: values[0] for key, values in parse_qs(parts.query).items()}
    return f"{parts.scheme}://{parts.netloc}{parts.path}", query


def assert_cookie_deleted(response):
    cookie = response.cookies[COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == 0
    assert cookie["path"] == "/api/v1/auth/"


# ---------- Регистрация и подтверждение email ----------


REGISTER = {
    "email": "New.User@Voltra.kz",
    "password": "Galaxy-Watch-7",
    "first_name": "Айбек",
    "last_name": "Сапаров",
}


def test_register_creates_unverified_user_and_sends_link(api_client, mailoutbox):
    res = api_client.post("/api/v1/auth/register/", REGISTER, format="json")

    assert res.status_code == 201
    assert res.json() == {
        "id": res.data["id"],
        "email": "new.user@voltra.kz",
        "first_name": "Айбек",
        "last_name": "Сапаров",
        "phone": "",
        "avatar": None,
        "is_email_verified": False,
    }
    assert User.objects.get(email="new.user@voltra.kz").check_password("Galaxy-Watch-7")

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["new.user@voltra.kz"]
    url, query = link_from(mailoutbox[0])
    assert url == f"{FRONT}/verify-email"
    assert set(query) == {"uid", "token"}


def test_register_duplicate_email_case_insensitive(api_client, user):
    payload = {**REGISTER, "email": user.email.upper()}
    res = api_client.post("/api/v1/auth/register/", payload, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "validation_error"
    assert res.data["fields"] == {"email": ["Пользователь с таким email уже зарегистрирован."]}


def test_register_weak_password_errors_in_russian(api_client):
    payload = {**REGISTER, "password": "12345"}
    res = api_client.post("/api/v1/auth/register/", payload, format="json")

    assert res.status_code == 400
    messages = res.data["fields"]["password"]
    assert any("слишком короткий" in m for m in messages)
    assert "Введённый пароль состоит только из цифр." in messages


def test_register_password_similar_to_email(api_client):
    payload = {**REGISTER, "email": "galaxywatch@voltra.kz", "password": "galaxywatch"}
    res = api_client.post("/api/v1/auth/register/", payload, format="json")

    assert res.status_code == 400
    assert any("похож" in m for m in res.data["fields"]["password"])


def test_register_required_fields(api_client):
    res = api_client.post("/api/v1/auth/register/", {}, format="json")

    assert res.status_code == 400
    assert set(res.data["fields"]) == {"email", "password", "first_name", "last_name"}
    assert res.data["fields"]["email"] == ["Обязательное поле."]


def test_verify_email_from_letter_then_login(api_client, mailoutbox):
    api_client.post("/api/v1/auth/register/", REGISTER, format="json")
    _, query = link_from(mailoutbox[0])

    res = api_client.post("/api/v1/auth/verify-email/", query, format="json")
    assert res.status_code == 204
    assert User.objects.get(email="new.user@voltra.kz").is_email_verified

    # повторный переход по той же ссылке не ломается
    assert api_client.post("/api/v1/auth/verify-email/", query, format="json").status_code == 204
    assert login(api_client, "new.user@voltra.kz", "Galaxy-Watch-7").status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"uid": "MQ", "token": "bad-token"},
        {"uid": "not-base64!", "token": "x"},
        {"uid": "OTk5OTk", "token": "x"},  # несуществующий pk
    ],
)
def test_verify_email_invalid_link(api_client, user, payload):
    res = api_client.post("/api/v1/auth/verify-email/", payload, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "invalid_token"
    assert res.data["detail"].startswith("Ссылка недействительна")


def test_password_reset_token_does_not_verify_email(api_client):
    user = UserFactory(is_email_verified=False)
    payload = {"uid": encode_uid(user), "token": password_reset_token.make_token(user)}

    res = api_client.post("/api/v1/auth/verify-email/", payload, format="json")

    assert res.status_code == 400


# ---------- Вход ----------


def test_login_returns_only_access_and_sets_refresh_cookie(api_client, user):
    res = login(api_client, user.email)

    assert res.status_code == 200
    assert set(res.json()) == {"access"}
    assert str(AccessToken(res.data["access"])["user_id"]) == str(user.id)

    cookie = res.cookies[COOKIE]
    assert RefreshToken(cookie.value)["user_id"] == AccessToken(res.data["access"])["user_id"]
    assert cookie["httponly"] is True
    assert cookie["path"] == "/api/v1/auth/"
    assert cookie["samesite"] == "Lax"
    assert not cookie["secure"]
    assert cookie["max-age"] == int(
        django_settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
    )
    user.refresh_from_db()
    assert user.last_login is not None


def test_login_cookie_in_production_mode(api_client, user, settings):
    settings.REFRESH_COOKIE_SECURE = True
    settings.REFRESH_COOKIE_SAMESITE = "None"

    cookie = login(api_client, user.email).cookies[COOKIE]

    assert cookie["secure"] is True
    assert cookie["samesite"] == "None"
    assert cookie["httponly"] is True


def test_login_email_is_case_insensitive(api_client, user):
    assert login(api_client, f"  {user.email.upper()} ").status_code == 200


@pytest.mark.parametrize("email_suffix", ["", "-unknown"])
def test_login_wrong_credentials(api_client, user, email_suffix):
    res = login(api_client, user.email + email_suffix, "wrong-password")

    assert res.status_code == 401
    assert res.data == {
        "detail": "Неверный email или пароль.",
        "code": "invalid_credentials",
        "fields": {},
    }
    assert COOKIE not in res.cookies


def test_login_inactive_user(api_client):
    user = UserFactory(is_active=False)

    assert login(api_client, user.email).status_code == 401


def test_login_unverified_email_is_403_and_resends_link_once(api_client, mailoutbox):
    user = UserFactory(is_email_verified=False)

    res = login(api_client, user.email)
    assert res.status_code == 403
    assert res.data["code"] == "email_not_verified"
    assert user.email in res.data["detail"]
    assert COOKIE not in res.cookies
    assert len(mailoutbox) == 1

    login(api_client, user.email)
    assert len(mailoutbox) == 1  # пауза между повторными письмами


def test_login_unverified_with_wrong_password_does_not_reveal_status(api_client, mailoutbox):
    user = UserFactory(is_email_verified=False)

    res = login(api_client, user.email, "wrong-password")

    assert res.status_code == 401
    assert mailoutbox == []


def test_login_unverified_allowed_when_verification_disabled(api_client, settings):
    settings.EMAIL_VERIFICATION_REQUIRED = False
    user = UserFactory(is_email_verified=False)

    assert login(api_client, user.email).status_code == 200


def test_login_ignores_expired_bearer_header(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired-garbage")

    assert login(api_client, user.email).status_code == 200


def test_login_validation(api_client):
    res = api_client.post("/api/v1/auth/login/", {"email": ""}, format="json")

    assert res.status_code == 400
    assert set(res.data["fields"]) == {"email", "password"}


def test_login_is_throttled(api_client, user, settings):
    settings.AUTH_THROTTLE_RATES = {**settings.AUTH_THROTTLE_RATES, "login": "2/min"}

    login(api_client, user.email, "wrong")
    login(api_client, user.email, "wrong")
    res = login(api_client, user.email)

    assert res.status_code == 429
    assert res.data["code"] == "throttled"
    assert set(res.data) == {"detail", "code", "fields"}


@pytest.mark.parametrize(
    ("scope", "url", "payload"),
    [
        ("register", "/api/v1/auth/register/", REGISTER),
        ("password_reset", "/api/v1/auth/password-reset/", {"email": "a@voltra.kz"}),
    ],
)
def test_other_auth_endpoints_are_throttled(api_client, settings, scope, url, payload):
    settings.AUTH_THROTTLE_RATES = {**settings.AUTH_THROTTLE_RATES, scope: "1/hour"}

    api_client.post(url, payload, format="json")
    res = api_client.post(url, payload, format="json")

    assert res.status_code == 429


def test_relaxed_rates_do_not_block_e2e_style_bursts(api_client, user):
    # В режиме тестов лимиты ослаблены: десятки входов подряд, как в e2e-сценариях фронта.
    for _ in range(30):
        assert login(api_client, user.email).status_code == 200


def test_empty_rate_disables_throttle(api_client, user, settings):
    settings.AUTH_THROTTLE_RATES = {**settings.AUTH_THROTTLE_RATES, "login": ""}

    for _ in range(3):
        assert login(api_client, user.email).status_code == 200


# ---------- Refresh ----------


def test_refresh_rotates_cookie_and_blacklists_old(api_client, user):
    old_refresh = login(api_client, user.email).cookies[COOKIE].value

    res = api_client.post("/api/v1/auth/refresh/")

    assert res.status_code == 200
    assert set(res.json()) == {"access"}
    assert str(AccessToken(res.data["access"])["user_id"]) == str(user.id)
    new_refresh = res.cookies[COOKIE].value
    assert new_refresh and new_refresh != old_refresh
    assert res.cookies[COOKIE]["httponly"] is True

    # новый refresh работает
    assert api_client.post("/api/v1/auth/refresh/").status_code == 200

    # старый — уже в blacklist
    api_client.cookies[COOKIE] = old_refresh
    res = api_client.post("/api/v1/auth/refresh/")
    assert res.status_code == 401
    assert res.data["code"] == "token_not_valid"
    assert_cookie_deleted(res)


def test_refresh_without_cookie(api_client):
    res = api_client.post("/api/v1/auth/refresh/")

    assert res.status_code == 401
    assert res.data["code"] == "not_authenticated"
    assert res.data["detail"] == "Сессия истекла. Войдите снова."


def test_refresh_with_garbage_cookie_clears_it(api_client):
    api_client.cookies[COOKIE] = "garbage"

    res = api_client.post("/api/v1/auth/refresh/")

    assert res.status_code == 401
    assert_cookie_deleted(res)


def test_refresh_for_deactivated_user(api_client, user):
    login(api_client, user.email)
    User.objects.filter(pk=user.pk).update(is_active=False)

    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


def test_refresh_from_frontend_origin(api_client, user):
    login(api_client, user.email)

    res = api_client.post("/api/v1/auth/refresh/", HTTP_ORIGIN=FRONT)

    assert res.status_code == 200


def test_refresh_from_foreign_origin_is_rejected(api_client, user):
    login(api_client, user.email)

    res = api_client.post("/api/v1/auth/refresh/", HTTP_ORIGIN="https://evil.example")

    assert res.status_code == 403
    assert res.data["code"] == "origin_not_allowed"


# ---------- Logout ----------


def test_logout_blacklists_refresh_and_deletes_cookie(api_client, user):
    access = login(api_client, user.email).data["access"]
    refresh = api_client.cookies[COOKIE].value
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    res = api_client.post("/api/v1/auth/logout/")

    assert res.status_code == 204
    assert_cookie_deleted(res)
    api_client.cookies[COOKIE] = refresh
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


def test_logout_without_session_is_still_204(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired-garbage")

    res = api_client.post("/api/v1/auth/logout/")

    assert res.status_code == 204
    assert_cookie_deleted(res)


def test_logout_with_already_blacklisted_cookie(api_client, user):
    login(api_client, user.email)
    refresh = api_client.cookies[COOKIE].value
    api_client.post("/api/v1/auth/logout/")
    api_client.cookies[COOKIE] = refresh

    assert api_client.post("/api/v1/auth/logout/").status_code == 204


def test_logout_from_foreign_origin_is_rejected(api_client, user):
    login(api_client, user.email)

    res = api_client.post("/api/v1/auth/logout/", HTTP_ORIGIN="https://evil.example")

    assert res.status_code == 403
    assert api_client.post("/api/v1/auth/refresh/").status_code == 200


# ---------- Сброс пароля ----------


def test_password_reset_unknown_email_is_204_without_letter(api_client, mailoutbox):
    res = api_client.post("/api/v1/auth/password-reset/", {"email": "nobody@voltra.kz"})

    assert res.status_code == 204
    assert mailoutbox == []


def test_password_reset_full_flow(api_client, user, mailoutbox):
    login(api_client, user.email)  # активная сессия, которая должна завершиться
    old_refresh = api_client.cookies[COOKIE].value

    res = api_client.post("/api/v1/auth/password-reset/", {"email": user.email.upper()})
    assert res.status_code == 204
    assert len(mailoutbox) == 1
    url, query = link_from(mailoutbox[0])
    assert url == f"{FRONT}/password-reset/confirm"

    res = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {**query, "password": "New-Galaxy-S25"},
        format="json",
    )
    assert res.status_code == 204
    assert login(api_client, user.email, "New-Galaxy-S25").status_code == 200
    assert login(api_client, user.email, PASSWORD).status_code == 401

    # ссылка одноразовая
    res = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {**query, "password": "Another-Pass-77"},
        format="json",
    )
    assert res.status_code == 400
    assert res.data["code"] == "invalid_token"

    # старые сессии завершены
    api_client.cookies[COOKIE] = old_refresh
    assert api_client.post("/api/v1/auth/refresh/").status_code == 401


def test_password_reset_confirm_weak_password(api_client, user):
    payload = {
        "uid": encode_uid(user),
        "token": password_reset_token.make_token(user),
        "password": "123",
    }

    res = api_client.post("/api/v1/auth/password-reset/confirm/", payload, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "validation_error"
    messages = res.data["fields"]["password"]
    assert any("слишком короткий" in m for m in messages)
    # фронт на этой странице показывает только detail
    assert res.data["detail"] == messages[0]


def test_password_reset_confirm_bad_token(api_client, user):
    payload = {"uid": encode_uid(user), "token": "bad", "password": "New-Galaxy-S25"}

    res = api_client.post("/api/v1/auth/password-reset/confirm/", payload, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "invalid_token"


def test_email_verification_token_cannot_reset_password(api_client, user):
    payload = {
        "uid": encode_uid(user),
        "token": email_verification_token.make_token(user),
        "password": "New-Galaxy-S25",
    }

    res = api_client.post("/api/v1/auth/password-reset/confirm/", payload, format="json")

    assert res.status_code == 400


def test_password_reset_confirms_email(api_client):
    user = UserFactory(is_email_verified=False)
    payload = {
        "uid": encode_uid(user),
        "token": password_reset_token.make_token(user),
        "password": "New-Galaxy-S25",
    }

    api_client.post("/api/v1/auth/password-reset/confirm/", payload, format="json")

    user.refresh_from_db()
    assert user.is_email_verified


def test_password_reset_smtp_failure_still_204(api_client, user, monkeypatch):
    def broken_send_mail(*args, **kwargs):
        raise ConnectionRefusedError

    monkeypatch.setattr("apps.users.emails.send_mail", broken_send_mail)

    res = api_client.post("/api/v1/auth/password-reset/", {"email": user.email})

    assert res.status_code == 204

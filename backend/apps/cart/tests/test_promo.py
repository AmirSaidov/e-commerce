from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.cart.promo import calc_discount
from apps.cart.tests.factories import PromoCodeFactory

pytestmark = pytest.mark.django_db

URL = "/api/v1/cart/apply-promo/"


@pytest.fixture
def promos():
    PromoCodeFactory(code="WELCOME10", type="percent", value=Decimal("10"))
    PromoCodeFactory(code="VOLTRA5000", type="fixed", value=Decimal("5000"))
    PromoCodeFactory(
        code="SUMMER25",
        type="percent",
        value=Decimal("25"),
        expires_at=timezone.now() - timedelta(days=1),
    )


def check(client, code, subtotal):
    return client.post(URL, {"code": code, "subtotal": subtotal}, format="json")


def test_percent_promo_for_guest(api_client, promos):
    res = check(api_client, " welcome10 ", 599990)

    assert res.status_code == 200
    assert res.json() == {
        "code": "WELCOME10",
        "type": "percent",
        "value": "10.00",
        "discount": "59999.00",
    }


def test_fixed_promo(api_client, promos):
    res = check(api_client, "VOLTRA5000", 129990)

    assert res.json() == {
        "code": "VOLTRA5000",
        "type": "fixed",
        "value": "5000.00",
        "discount": "5000.00",
    }


def test_fixed_discount_not_above_subtotal(api_client, promos):
    assert check(api_client, "VOLTRA5000", 3000).json()["discount"] == "3000.00"


def test_works_with_bearer_token_too(auth_client, promos):
    assert check(auth_client, "WELCOME10", 1000).status_code == 200


def test_unknown_promo(api_client, promos):
    res = check(api_client, "NOPE", 1000)

    assert res.status_code == 400
    assert res.data == {"detail": "Такого промокода нет.", "code": "promo_not_found", "fields": {}}


def test_expired_promo(api_client, promos):
    res = check(api_client, "summer25", 1000)

    assert res.status_code == 400
    assert res.data == {
        "detail": "Срок действия промокода истёк.",
        "code": "promo_expired",
        "fields": {},
    }


def test_inactive_promo(api_client):
    PromoCodeFactory(code="OFF", is_active=False)

    assert check(api_client, "OFF", 1000).data["code"] == "promo_inactive"


def test_min_subtotal(api_client):
    PromoCodeFactory(code="BIG", min_subtotal=Decimal("100000"))

    res = check(api_client, "BIG", 99999)

    assert res.status_code == 400
    assert res.data["code"] == "promo_min_subtotal"
    assert res.data["detail"] == "Промокод действует для заказов от 100 000 ₸."
    assert check(api_client, "BIG", 100000).status_code == 200


def test_saves_nothing(api_client, promos, django_assert_max_num_queries):
    with django_assert_max_num_queries(1):  # один SELECT промокода, без записей
        check(api_client, "WELCOME10", 1000)


@pytest.mark.parametrize(
    ("payload", "fields"),
    [({}, {"code", "subtotal"}), ({"code": "X", "subtotal": -1}, {"subtotal"})],
)
def test_validation(api_client, payload, fields):
    res = api_client.post(URL, payload, format="json")

    assert res.status_code == 400
    assert set(res.data["fields"]) == fields


def test_apply_promo_is_throttled(api_client, promos, settings):
    settings.AUTH_THROTTLE_RATES = {**settings.AUTH_THROTTLE_RATES, "promo": "2/min"}

    check(api_client, "A", 1)
    check(api_client, "B", 1)

    assert check(api_client, "WELCOME10", 1).status_code == 429


@pytest.mark.parametrize(
    ("type_", "value", "subtotal", "expected"),
    [
        ("percent", "10", "599990", "59999.00"),
        ("percent", "10", "15", "2.00"),  # 1.5 → 2, как Math.round
        ("percent", "10", "14", "1.00"),  # 1.4 → 1
        ("percent", "100", "5000", "5000.00"),
        ("fixed", "5000", "4999", "4999.00"),
        ("fixed", "5000", "0", "0.00"),
    ],
)
def test_calc_discount_matches_frontend(type_, value, subtotal, expected):
    promo = PromoCodeFactory.build(type=type_, value=Decimal(value))

    assert calc_discount(Decimal(subtotal), promo) == Decimal(expected)

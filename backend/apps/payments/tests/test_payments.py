import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace

import pytest
import stripe

from apps.cart.tests.factories import PromoCodeFactory
from apps.catalog.models import Product
from apps.catalog.tests.factories import make_product
from apps.orders.models import Order
from apps.payments import gateway
from apps.payments.services import to_minor_units
from apps.users.models import Address
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = pytest.mark.django_db

CHECKOUT = "/api/v1/payments/checkout-session/"
WEBHOOK = "/api/v1/payments/webhook/"
WEBHOOK_SECRET = "whsec_test_secret"
FRONT = "http://localhost:3000"


@pytest.fixture(autouse=True)
def stripe_settings(settings):
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET
    settings.STRIPE_CURRENCY = "kzt"
    settings.STRIPE_MIN_AMOUNT = Decimal("500")
    settings.FRONTEND_URL = FRONT


class FakeStripe:
    """Подмена apps.payments.gateway: запоминает вызовы, в сеть не ходит."""

    def __init__(self):
        self.sessions, self.coupons, self.expired = [], [], []

    def create_checkout_session(self, params):
        self.sessions.append(params)
        n = len(self.sessions)
        return {"id": f"cs_test_{n}", "url": f"https://checkout.stripe.com/c/pay/cs_test_{n}"}

    def create_coupon(self, params):
        self.coupons.append(params)
        return f"coupon_{len(self.coupons)}"

    def expire_checkout_session(self, session_id):
        self.expired.append(session_id)


@pytest.fixture
def fake_stripe(monkeypatch):
    fake = FakeStripe()
    for name in ("create_checkout_session", "create_coupon", "expire_checkout_session"):
        monkeypatch.setattr(gateway, name, getattr(fake, name))
    return fake


def make_order(
    client, user, *, price="129990", quantity=1, payment="card", delivery="courier", promo=None
):
    variant = make_product(prices=(price,), stocks=(10,), name="Apple AirPods Pro 2").variants.get()
    address = Address.objects.create(
        user=user, city="Алматы", street="Абая", building="1", is_default=True
    )
    payload = {
        "items": [{"variant_id": variant.id, "quantity": quantity}],
        "delivery_method": delivery,
        "payment_method": payment,
        "address_id": address.id,
    }
    if promo:
        payload["promo_code"] = promo
    res = client.post("/api/v1/orders/", payload, format="json")
    assert res.status_code == 201, res.data
    return Order.objects.get(number=res.data["number"])


# ---------- checkout-session ----------


def test_checkout_session_params(auth_client, user, fake_stripe):
    order = make_order(auth_client, user, price="30000", quantity=2)  # 60 000 + доставка 1 500

    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.status_code == 200
    assert res.json() == {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}
    params = fake_stripe.sessions[0]
    assert params["mode"] == "payment"
    assert params["success_url"] == f"{FRONT}/checkout/success?order={order.number}"
    assert params["cancel_url"] == f"{FRONT}/account/orders/{order.number}"
    assert params["client_reference_id"] == order.number
    assert params["metadata"] == {"order_number": order.number}
    assert params["customer_email"] == user.email
    assert params["line_items"] == [
        {
            "price_data": {
                "currency": "kzt",
                "unit_amount": 3_000_000,  # 30 000 ₸ в тиынах
                "product_data": {"name": "Apple AirPods Pro 2 — 128 ГБ"},
            },
            "quantity": 2,
        },
        {
            "price_data": {
                "currency": "kzt",
                "unit_amount": 150_000,
                "product_data": {"name": "Доставка курьером"},
            },
            "quantity": 1,
        },
    ]
    assert "discounts" not in params
    order.refresh_from_db()
    assert order.stripe_session_id == "cs_test_1"
    assert order.status == "created"  # paid ставит только вебхук


def test_checkout_session_total_matches_order_with_discount(auth_client, user, fake_stripe):
    PromoCodeFactory(code="WELCOME10", value=Decimal("10"))
    order = make_order(auth_client, user, price="129990", promo="WELCOME10")

    auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    params = fake_stripe.sessions[0]
    assert params["discounts"] == [{"coupon": "coupon_1"}]
    coupon = fake_stripe.coupons[0]
    assert coupon["amount_off"] == 1_299_900 and coupon["currency"] == "kzt"
    assert coupon["duration"] == "once" and coupon["max_redemptions"] == 1
    lines = sum(i["price_data"]["unit_amount"] * i["quantity"] for i in params["line_items"])
    assert lines - coupon["amount_off"] == to_minor_units(order.total)


def test_repeat_checkout_expires_previous_session(auth_client, user, fake_stripe):
    order = make_order(auth_client, user)

    auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")
    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.data["url"].endswith("cs_test_2")
    assert fake_stripe.expired == ["cs_test_1"]
    order.refresh_from_db()
    assert order.stripe_session_id == "cs_test_2"


@pytest.mark.parametrize(
    ("setup", "code"),
    [
        ({"payment": "cash"}, "payment_not_required"),
        ({"status": "paid"}, "order_already_paid"),
        ({"status": "cancelled"}, "order_not_payable"),
        ({"status": "shipped"}, "order_not_payable"),
    ],
)
def test_checkout_not_allowed(auth_client, user, fake_stripe, setup, code):
    order = make_order(auth_client, user, payment=setup.get("payment", "card"))
    if "status" in setup:
        Order.objects.filter(pk=order.pk).update(status=setup["status"])

    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.status_code == 400
    assert res.data["code"] == code
    assert fake_stripe.sessions == []


def test_checkout_amount_too_small(auth_client, user, fake_stripe):
    order = make_order(auth_client, user, price="100", delivery="pickup")

    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "amount_too_small"


def test_checkout_foreign_or_unknown_order(auth_client, fake_stripe):
    stranger = UserFactory()
    foreign = make_order(bearer_client(stranger), stranger)

    for number in (foreign.number, "VT-999999"):
        res = auth_client.post(CHECKOUT, {"order_number": number}, format="json")
        assert res.status_code == 404
        assert res.data["detail"] == "Заказ не найден."


def test_checkout_without_stripe_keys(auth_client, user, settings, fake_stripe):
    order = make_order(auth_client, user)  # заказ создан, пока ключ был
    settings.STRIPE_SECRET_KEY = ""

    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.status_code == 503
    assert res.data["code"] == "payments_unavailable"


def test_checkout_stripe_error_is_502(auth_client, user, monkeypatch):
    def network_down(params):
        raise stripe.APIConnectionError("network down")

    fake_client = SimpleNamespace(
        v1=SimpleNamespace(checkout=SimpleNamespace(sessions=SimpleNamespace(create=network_down)))
    )
    monkeypatch.setattr(gateway, "_client", lambda: fake_client)
    order = make_order(auth_client, user)

    res = auth_client.post(CHECKOUT, {"order_number": order.number}, format="json")

    assert res.status_code == 502
    assert res.data["code"] == "payment_provider_error"
    assert res.data["detail"] == "Не удалось перейти к оплате. Попробуйте ещё раз."
    order.refresh_from_db()
    assert order.stripe_session_id == ""


def test_checkout_requires_auth(api_client):
    assert api_client.post(CHECKOUT, {"order_number": "VT-1"}, format="json").status_code == 401


@pytest.mark.parametrize(("currency", "minor"), [("kzt", 12_999_000), ("jpy", 129_990)])
def test_to_minor_units(currency, minor):
    assert to_minor_units(Decimal("129990.00"), currency) == minor


# ---------- вебхук ----------


def sign(payload, secret=WEBHOOK_SECRET, timestamp=None):
    timestamp = timestamp or int(time.time())
    signature = hmac.new(
        secret.encode(), f"{timestamp}.{payload}".encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def completed_event(
    order,
    *,
    amount=None,
    currency="kzt",
    payment_status="paid",
    event_type="checkout.session.completed",
):
    return json.dumps(
        {
            "id": "evt_test_1",
            "object": "event",
            "type": event_type,
            "data": {
                "object": {
                    "id": "cs_test_paid",
                    "object": "checkout.session",
                    "client_reference_id": order.number,
                    "metadata": {"order_number": order.number},
                    "payment_status": payment_status,
                    "payment_intent": "pi_test_123",
                    "amount_total": to_minor_units(order.total) if amount is None else amount,
                    "currency": currency,
                }
            },
        }
    )


def post_webhook(client, payload, signature=None):
    return client.post(
        WEBHOOK,
        payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=signature if signature is not None else sign(payload),
    )


def test_webhook_marks_order_paid_and_counts_popularity(api_client, auth_client, user):
    order = make_order(auth_client, user, quantity=3)
    product = Product.objects.get(pk=order.items.get().product_id)
    product.popularity = 10
    product.save()

    res = post_webhook(api_client, completed_event(order))

    assert res.status_code == 200
    assert res.json() == {"status": "paid"}
    order.refresh_from_db()
    assert order.status == "paid" and order.paid_at is not None
    assert order.stripe_payment_intent == "pi_test_123"
    assert order.stripe_session_id == "cs_test_paid"
    product.refresh_from_db()
    assert product.popularity == 13
    # страница успеха фронта увидит это при опросе GET /orders/{number}/
    assert auth_client.get(f"/api/v1/orders/{order.number}/").data["status"] == "paid"


def test_webhook_is_idempotent(api_client, auth_client, user):
    order = make_order(auth_client, user, quantity=2)
    payload = completed_event(order)

    post_webhook(api_client, payload)
    res = post_webhook(api_client, payload)

    assert res.json() == {"status": "already_paid"}
    product = Product.objects.get(pk=order.items.get().product_id)
    assert product.popularity == 2  # засчитано один раз


def test_webhook_bad_signature(api_client, auth_client, user):
    order = make_order(auth_client, user)
    payload = completed_event(order)

    for signature in (sign(payload, secret="whsec_wrong"), "", "t=1,v1=deadbeef"):
        res = post_webhook(api_client, payload, signature)
        assert res.status_code == 400
        assert res.data["code"] == "invalid_signature"
    order.refresh_from_db()
    assert order.status == "created"


def test_webhook_stale_timestamp_rejected(api_client, auth_client, user):
    order = make_order(auth_client, user)
    payload = completed_event(order)

    res = post_webhook(api_client, payload, sign(payload, timestamp=int(time.time()) - 3600))

    assert res.status_code == 400


def test_webhook_tampered_payload_rejected(api_client, auth_client, user):
    order = make_order(auth_client, user)
    signature = sign(completed_event(order, amount=1))

    res = post_webhook(api_client, completed_event(order), signature)

    assert res.status_code == 400


def test_webhook_without_secret(api_client, settings):
    settings.STRIPE_WEBHOOK_SECRET = ""

    res = post_webhook(api_client, "{}")

    assert res.status_code == 503
    assert res.data["code"] == "payments_unavailable"


def test_webhook_amount_mismatch_does_not_mark_paid(api_client, auth_client, user):
    order = make_order(auth_client, user)

    res = post_webhook(api_client, completed_event(order, amount=100))

    assert res.json() == {"status": "amount_mismatch"}
    order.refresh_from_db()
    assert order.status == "created"


def test_webhook_currency_mismatch(api_client, auth_client, user):
    order = make_order(auth_client, user)

    assert post_webhook(api_client, completed_event(order, currency="usd")).json() == {
        "status": "amount_mismatch"
    }


def test_webhook_unpaid_session_waits(api_client, auth_client, user):
    order = make_order(auth_client, user)

    res = post_webhook(api_client, completed_event(order, payment_status="unpaid"))

    assert res.json() == {"status": "pending"}
    order.refresh_from_db()
    assert order.status == "created"


def test_webhook_async_payment_succeeded(api_client, auth_client, user):
    order = make_order(auth_client, user)

    payload = completed_event(order, event_type="checkout.session.async_payment_succeeded")

    assert post_webhook(api_client, payload).json() == {"status": "paid"}


def test_webhook_ignores_other_events(api_client, auth_client, user):
    order = make_order(auth_client, user)

    payload = completed_event(order, event_type="payment_intent.created")

    assert post_webhook(api_client, payload).json() == {"status": "ignored"}


def test_webhook_for_cancelled_order(api_client, auth_client, user, caplog):
    order = make_order(auth_client, user)
    auth_client.post(f"/api/v1/orders/{order.number}/cancel/")

    res = post_webhook(api_client, completed_event(order))

    assert res.json() == {"status": "not_payable"}
    assert "ручной возврат" in caplog.text
    order.refresh_from_db()
    assert order.status == "cancelled"


def test_webhook_unknown_order(api_client):
    fake = Order(number="VT-999999", total=Decimal("100"))

    assert post_webhook(api_client, completed_event(fake)).json() == {"status": "unknown_order"}


def test_webhook_ignores_bearer_header(api_client, auth_client, user):
    order = make_order(auth_client, user)
    api_client.credentials(HTTP_AUTHORIZATION="Bearer garbage")

    assert post_webhook(api_client, completed_event(order)).status_code == 200


def test_paid_then_cancel_rolls_back_popularity(api_client, auth_client, user):
    order = make_order(auth_client, user, quantity=2)
    post_webhook(api_client, completed_event(order))

    assert auth_client.post(f"/api/v1/orders/{order.number}/cancel/").data["status"] == "cancelled"

    assert Product.objects.get(pk=order.items.get().product_id).popularity == 0

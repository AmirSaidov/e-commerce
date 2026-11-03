"""Сценарий покупки той же последовательностью запросов, что делает фронт в режиме api:

stores/auth.ts      — restore (refresh по cookie) → login → users.me → cart.merge → wishlist.load
providers.tsx       — PUT /cart/ после изменений корзины
promo-form.tsx      — POST /cart/apply-promo/ (без токена)
checkout/page.tsx   — addresses.list → orders.create → payments.checkoutSession → редирект в Stripe
вебхук Stripe       — checkout.session.completed
checkout/success    — опрос GET /orders/{number}/, пока заказ не станет paid
"""

from decimal import Decimal

import pytest

from apps.cart.tests.factories import PromoCodeFactory
from apps.catalog.tests.factories import make_product
from apps.orders.models import Order
from apps.payments import gateway
from apps.payments.tests.test_payments import WEBHOOK_SECRET, completed_event, sign
from apps.users.tests.factories import PASSWORD

pytestmark = pytest.mark.django_db
FRONT = "http://localhost:3000"


@pytest.fixture(autouse=True)
def frontend_like_settings(settings):
    settings.FRONTEND_URL = FRONT
    settings.CORS_ALLOWED_ORIGINS = [FRONT]
    settings.STRIPE_WEBHOOK_SECRET = WEBHOOK_SECRET


def test_full_purchase_like_frontend(api_client, user, monkeypatch):
    sessions = []
    monkeypatch.setattr(
        gateway,
        "create_checkout_session",
        lambda params: (
            sessions.append(params) or {"id": "cs_1", "url": "https://checkout.stripe.com/x"}
        ),
    )
    monkeypatch.setattr(gateway, "create_coupon", lambda params: "coupon_1")
    PromoCodeFactory(code="WELCOME10", value=Decimal("10"))
    airpods = make_product(prices=("129990",), stocks=(5,), name="AirPods Pro 2").variants.get()
    origin = {"HTTP_ORIGIN": FRONT}

    # 1. Старт приложения гостем: refresh без cookie → 401, фронт работает как гость
    assert api_client.post("/api/v1/auth/refresh/", **origin).status_code == 401

    # 2. Гость проверяет промокод в корзине (без токена)
    promo = api_client.post(
        "/api/v1/cart/apply-promo/", {"code": "WELCOME10", "subtotal": 129990}, format="json"
    )
    assert promo.data["discount"] == "12999.00"

    # 3. Вход → access в памяти, refresh в cookie → users.me
    login = api_client.post(
        "/api/v1/auth/login/", {"email": user.email, "password": PASSWORD}, format="json", **origin
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
    assert api_client.get("/api/v1/users/me/").data["email"] == user.email

    # 4. Слияние гостевой корзины и загрузка избранного
    merged = api_client.post(
        "/api/v1/cart/merge/", {"items": [{"variant_id": airpods.id, "quantity": 1}]}, format="json"
    )
    assert [i["variant"]["id"] for i in merged.data["items"]] == [airpods.id]
    assert api_client.get("/api/v1/wishlist/").data == []

    # 5. Синхронизация корзины (debounce 800 мс на фронте)
    items = [{"variant_id": airpods.id, "quantity": 1}]
    assert api_client.put("/api/v1/cart/", {"items": items}, format="json").status_code == 204

    # 6. Перезагрузка вкладки: access потерян, сессия восстанавливается по refresh-cookie
    restored = api_client.post("/api/v1/auth/refresh/", **origin)
    assert restored.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {restored.data['access']}")

    # 7. Оформление: адрес → заказ картой с промокодом → Checkout Session
    address = api_client.post(
        "/api/v1/users/me/addresses/",
        {"city": "Алматы", "street": "пр. Абая", "building": "150", "is_default": True},
        format="json",
    ).data
    assert [a["id"] for a in api_client.get("/api/v1/users/me/addresses/").data] == [address["id"]]
    order = api_client.post(
        "/api/v1/orders/",
        {
            "address_id": address["id"],
            "delivery_method": "courier",
            "payment_method": "card",
            "promo_code": "WELCOME10",
            "items": items,
        },
        format="json",
    ).data
    # 129 990 − 12 999 = 116 991 ≥ 100 000 → доставка бесплатно, как считает фронт
    assert (order["total"], order["delivery_price"], order["status"]) == (
        "116991.00",
        "0.00",
        "created",
    )
    checkout = api_client.post(
        "/api/v1/payments/checkout-session/", {"order_number": order["number"]}, format="json"
    )
    assert checkout.data["url"].startswith("https://checkout.stripe.com/")
    assert sessions[0]["success_url"] == f"{FRONT}/checkout/success?order={order['number']}"
    assert merged_cart_is_empty(api_client)

    # 8. Страница успеха опрашивает заказ: до вебхука — created, после — paid
    url = f"/api/v1/orders/{order['number']}/"
    assert api_client.get(url).data["status"] == "created"
    payload = completed_event(Order.objects.get(number=order["number"]))
    hook = api_client.post(
        "/api/v1/payments/webhook/",
        payload,
        content_type="application/json",
        HTTP_STRIPE_SIGNATURE=sign(payload),
    )
    assert hook.data == {"status": "paid"}
    assert api_client.get(url).data["status"] == "paid"
    assert api_client.get("/api/v1/orders/", {"page_size": 50}).data["count"] == 1

    # 9. Выход: refresh отозван, повторное восстановление сессии невозможно
    assert api_client.post("/api/v1/auth/logout/", **origin).status_code == 204
    assert api_client.post("/api/v1/auth/refresh/", **origin).status_code == 401


def merged_cart_is_empty(client):
    """После заказа серверная корзина пуста (фронт увидит это при следующем merge)."""
    return client.post("/api/v1/cart/merge/", {"items": []}, format="json").data["items"] == []

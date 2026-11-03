"""Оплата заказа через Stripe Checkout.

- checkout-session создаёт ссылку на оплату по позициям заказа (+ доставка, − скидка купоном);
- статус «оплачен» ставит только вебхук checkout.session.completed — идемпотентно.
"""

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import Product
from apps.core.exceptions import ApiException
from apps.orders.models import Order

from . import gateway
from .gateway import PaymentsUnavailable

logger = logging.getLogger(__name__)

# Валюты Stripe, где сумма передаётся без умножения на 100 (docs.stripe.com/currencies).
# KZT в этот список не входит: сумма передаётся в тиынах (× 100).
ZERO_DECIMAL_CURRENCIES = {
    "bif", "clp", "djf", "gnf", "jpy", "kmf", "krw", "mga",
    "pyg", "rwf", "vnd", "vuv", "xaf", "xof", "xpf",
}  # fmt: skip

PAID_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}


def to_minor_units(amount, currency=None):
    currency = (currency or settings.STRIPE_CURRENCY).lower()
    multiplier = 1 if currency in ZERO_DECIMAL_CURRENCIES else 100
    return int((Decimal(amount) * multiplier).quantize(Decimal("1")))


# ---------- checkout-session ----------


def start_checkout(order):
    """Создаёт Stripe Checkout Session для заказа и возвращает URL оплаты."""
    _ensure_payable(order)
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentsUnavailable()

    params = _session_params(order)
    if order.discount > 0:
        params["discounts"] = [{"coupon": gateway.create_coupon(_coupon_params(order))}]
    session = gateway.create_checkout_session(params)

    previous = order.stripe_session_id
    Order.objects.filter(pk=order.pk).update(stripe_session_id=session["id"])
    if previous and previous != session["id"]:
        # Повторное «Оплатить заказ»: старая ссылка больше не должна принимать деньги.
        gateway.expire_checkout_session(previous)
    return session["url"]


def _ensure_payable(order):
    if order.payment_method != Order.Payment.CARD:
        raise ApiException("Этот заказ оплачивается при получении.", code="payment_not_required")
    if order.status == Order.Status.PAID:
        raise ApiException("Заказ уже оплачен.", code="order_already_paid")
    if order.status != Order.Status.CREATED:
        raise ApiException("Этот заказ нельзя оплатить.", code="order_not_payable")
    if order.total < settings.STRIPE_MIN_AMOUNT:
        raise ApiException(
            "Сумма заказа слишком мала для онлайн-оплаты. Выберите оплату при получении.",
            code="amount_too_small",
        )


def _line(name, amount, quantity=1):
    return {
        "price_data": {
            "currency": settings.STRIPE_CURRENCY,
            "unit_amount": to_minor_units(amount),
            "product_data": {"name": name},
        },
        "quantity": quantity,
    }


def _session_params(order):
    line_items = [
        _line(f"{item.product_name} — {item.variant_name}", item.price, item.quantity)
        for item in order.items.all()
    ]
    if order.delivery_price > 0:
        line_items.append(_line("Доставка курьером", order.delivery_price))
    expires_at = timezone.now() + timedelta(minutes=settings.STRIPE_SESSION_MINUTES)
    return {
        "mode": "payment",
        "line_items": line_items,
        "success_url": f"{settings.FRONTEND_URL}/checkout/success?order={order.number}",
        "cancel_url": f"{settings.FRONTEND_URL}/account/orders/{order.number}",
        "client_reference_id": order.number,
        "metadata": {"order_number": order.number},
        "payment_intent_data": {"metadata": {"order_number": order.number}},
        "customer_email": order.user.email,
        "locale": "ru",
        "expires_at": int(expires_at.timestamp()),
    }


def _coupon_params(order):
    return {
        "amount_off": to_minor_units(order.discount),
        "currency": settings.STRIPE_CURRENCY,
        "duration": "once",
        "max_redemptions": 1,
        "name": f"Скидка {order.promo_code or ''}".strip()[:40],
    }


# ---------- вебхук ----------


def handle_event(event):
    """Обрабатывает событие Stripe. Возвращает короткий итог для ответа и логов."""
    if event["type"] not in PAID_EVENTS:
        return "ignored"
    session = event["data"]["object"]
    if session.get("payment_status") != "paid":
        return "pending"  # асинхронный способ оплаты: ждём async_payment_succeeded
    metadata = session.get("metadata") or {}
    number = metadata.get("order_number") or session.get("client_reference_id")
    return mark_paid(number, session)


@transaction.atomic
def mark_paid(number, session):
    order = Order.objects.select_for_update().filter(number=number).first()
    if order is None:
        logger.error("Stripe: оплачен неизвестный заказ %s (session %s)", number, session.get("id"))
        return "unknown_order"
    if order.status == Order.Status.PAID:
        return "already_paid"  # повтор события — идемпотентно
    if order.status != Order.Status.CREATED:
        logger.error(
            "Stripe: оплата пришла для заказа %s в статусе %s — нужен ручной возврат (session %s)",
            number,
            order.status,
            session.get("id"),
        )
        return "not_payable"

    expected = to_minor_units(order.total)
    currency = (session.get("currency") or "").lower()
    if session.get("amount_total") != expected or currency != settings.STRIPE_CURRENCY:
        logger.error(
            "Stripe: сумма не совпала для %s: %s %s, ожидалось %s %s",
            number,
            session.get("amount_total"),
            currency,
            expected,
            settings.STRIPE_CURRENCY,
        )
        return "amount_mismatch"

    order.status = Order.Status.PAID
    order.paid_at = timezone.now()
    order.stripe_session_id = session.get("id") or order.stripe_session_id
    order.stripe_payment_intent = session.get("payment_intent") or ""
    order.save(
        update_fields=[
            "status",
            "paid_at",
            "stripe_session_id",
            "stripe_payment_intent",
            "updated_at",
        ]
    )

    # popularity — число проданных штук.
    sold = defaultdict(int)
    for item in order.items.all():
        sold[item.product_id] += item.quantity
    for product_id, quantity in sold.items():
        Product.objects.filter(pk=product_id).update(popularity=F("popularity") + quantity)
    return "paid"

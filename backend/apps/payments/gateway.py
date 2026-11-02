"""Единственное место, где код ходит в Stripe. В тестах эти функции подменяются моком,
поэтому тесты работают без сети и без ключей; проверка подписи вебхука — настоящая (офлайн)."""

import logging

import stripe
from django.conf import settings

from apps.core.exceptions import ApiException

logger = logging.getLogger(__name__)


class PaymentsUnavailable(ApiException):
    status_code = 503
    default_detail = "Онлайн-оплата временно недоступна. Выберите оплату при получении."
    default_code = "payments_unavailable"


class PaymentProviderError(ApiException):
    status_code = 502
    default_detail = "Не удалось перейти к оплате. Попробуйте ещё раз."
    default_code = "payment_provider_error"


def _client():
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentsUnavailable()
    return stripe.StripeClient(settings.STRIPE_SECRET_KEY)


def create_checkout_session(params):
    """→ {"id": "cs_…", "url": "https://checkout.stripe.com/…"}"""
    try:
        session = _client().v1.checkout.sessions.create(params=params)
    except stripe.StripeError as exc:
        logger.exception("Stripe: не удалось создать Checkout Session")
        raise PaymentProviderError() from exc
    return {"id": session.id, "url": session.url}


def create_coupon(params):
    """Разовый купон на сумму скидки заказа → id купона."""
    try:
        return _client().v1.coupons.create(params=params).id
    except stripe.StripeError as exc:
        logger.exception("Stripe: не удалось создать купон")
        raise PaymentProviderError() from exc


def expire_checkout_session(session_id):
    """Закрывает старую ссылку на оплату, чтобы заказ нельзя было оплатить дважды.
    Ошибки не критичны (сессия могла уже истечь) — только пишем в лог."""
    try:
        _client().v1.checkout.sessions.expire(session_id)
    except stripe.StripeError:
        logger.warning("Stripe: не удалось закрыть Checkout Session %s", session_id)


def construct_event(payload, signature):
    """Проверяет подпись вебхука (STRIPE_WEBHOOK_SECRET) и разбирает событие. Сеть не нужна.
    Возвращает обычный dict: объекты stripe-python 16 — не словари."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise PaymentsUnavailable("Вебхук Stripe не настроен.")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        return event.to_dict()
    except stripe.SignatureVerificationError as exc:
        raise ApiException("Неверная подпись Stripe.", code="invalid_signature") from exc
    except ValueError as exc:
        raise ApiException("Некорректное тело события.", code="invalid_payload") from exc

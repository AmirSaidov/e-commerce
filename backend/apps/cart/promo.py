"""Промокоды. Расчёт скидки совпадает с calcPromoDiscount во frontend/src/lib/utils.ts:
min(Math.round(raw), subtotal), где raw = subtotal * value / 100 для процента или value для суммы.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.core.exceptions import ApiException

from .models import PromoCode

TENGE = Decimal("1")
CENTS = Decimal("0.01")


def normalize_code(code):
    return (code or "").strip().upper()


def calc_discount(subtotal, promo):
    if promo.type == PromoCode.Type.PERCENT:
        raw = subtotal * promo.value / 100
    else:
        raw = promo.value
    return min(raw.quantize(TENGE, rounding=ROUND_HALF_UP), subtotal).quantize(CENTS)


def get_valid_promo(code, subtotal, *, lock=False):
    """Промокод, который можно применить к заказу на сумму subtotal, иначе ApiException 400.

    lock=True — при оформлении заказа: строка промокода блокируется до конца транзакции,
    чтобы параллельные заказы не превысили usage_limit.
    """
    queryset = PromoCode.objects.select_for_update() if lock else PromoCode.objects
    promo = queryset.filter(code=normalize_code(code)).first()
    if promo is None:
        raise ApiException("Такого промокода нет.", code="promo_not_found")
    if promo.expires_at is not None and promo.expires_at <= timezone.now():
        raise ApiException("Срок действия промокода истёк.", code="promo_expired")
    if not promo.is_active:
        raise ApiException("Промокод больше не действует.", code="promo_inactive")
    if promo.usage_limit is not None:
        used = promo.orders.exclude(status="cancelled").count()
        if used >= promo.usage_limit:
            raise ApiException("Промокод больше не действует.", code="promo_exhausted")
    if promo.min_subtotal is not None and subtotal < promo.min_subtotal:
        raise ApiException(
            f"Промокод действует для заказов от {format_tenge(promo.min_subtotal)}.",
            code="promo_min_subtotal",
        )
    return promo


def format_tenge(amount):
    # 100000 → «100 000 ₸» (неразрывные пробелы, как Intl.NumberFormat("ru-RU") на фронте)
    return f"{int(amount):,}".replace(",", " ") + " ₸"

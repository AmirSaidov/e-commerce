"""Оформление и отмена заказа.

Состав заказа приходит в запросе (а не из серверной корзины), но цены, остатки и скидка
берутся только из БД. Остатки списываются в одной транзакции под select_for_update.
"""

from collections import defaultdict
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest
from django.utils import timezone

from apps.cart.promo import calc_discount, get_valid_promo
from apps.cart.services import clear_cart
from apps.catalog.models import Product, ProductImage, ProductVariant
from apps.core.exceptions import ApiException
from apps.users.models import Address

from .models import Order, OrderItem

ADDRESS_SNAPSHOT_FIELDS = ("city", "street", "building", "apartment", "postal_code")


def calc_delivery_price(method, subtotal_after_discount):
    """Как calcDeliveryPrice во frontend/src/lib/utils.ts (правила DELIVERY в config.ts)."""
    if method == Order.Delivery.PICKUP:
        return Decimal("0.00")
    if subtotal_after_discount >= settings.FREE_SHIPPING_FROM:
        return Decimal("0.00")
    return settings.COURIER_PRICE.quantize(Decimal("0.01"))


def out_of_stock_message(variant):
    """«AirPods Pro 2» осталось только 2 шт. — для товара с несколькими вариантами
    добавляется вариант («Apple iPhone 16 Pro, 512 ГБ»), иначе непонятно, чего не хватает."""
    name = variant.product.name
    if variant.product.variants.count() > 1:
        name = f"{name}, {variant.name}"
    if variant.stock == 0:
        return f"«{name}» закончился."
    return f"«{name}» осталось только {variant.stock} шт."


@transaction.atomic
def create_order(user, *, items, delivery_method, payment_method, address_id=None, promo_code=None):
    quantities = defaultdict(int)  # одинаковые варианты в запросе складываем
    for line in items:
        quantities[line["variant_id"]] += line["quantity"]
    if not quantities:
        raise ApiException("Корзина пуста.", code="cart_empty")
    if payment_method == Order.Payment.CARD and not settings.STRIPE_SECRET_KEY:
        # Без ключей Stripe заказ «картой» нельзя оплатить: не создаём его, а сразу говорим, что
        # делать (иначе фронт оставит неоплачиваемый заказ и полную корзину).
        raise ApiException(
            "Оплата картой онлайн сейчас недоступна. Выберите оплату при получении.",
            code="payment_method_unavailable",
        )

    address = _address_snapshot(user, delivery_method, address_id)

    # Блокируем строки вариантов в порядке id (без дедлоков между параллельными заказами).
    # of=("self",) — блокируются только варианты, не присоединённые товары.
    variants = list(
        ProductVariant.objects.select_for_update(of=("self",))
        .select_related("product")
        .filter(pk__in=quantities)
        .order_by("pk")
    )
    found = {variant.pk: variant for variant in variants}
    for variant_id in quantities:
        variant = found.get(variant_id)
        if variant is None:
            raise ApiException("Товар больше не продаётся.", code="variant_not_found")
        if not variant.product.is_active:
            raise ApiException(
                f"«{variant.product.name}» больше не продаётся.", code="variant_not_found"
            )
        if variant.stock < quantities[variant_id]:
            raise ApiException(out_of_stock_message(variant), code="out_of_stock")

    subtotal = sum((v.price * quantities[v.pk] for v in variants), Decimal("0.00"))
    promo, discount = None, Decimal("0.00")
    if promo_code and promo_code.strip():
        # Промокод проверяется заново: клиенту не доверяем ни код, ни сумму скидки.
        promo = get_valid_promo(promo_code, subtotal, lock=True)
        discount = calc_discount(subtotal, promo)
    delivery_price = calc_delivery_price(delivery_method, subtotal - discount)

    order = Order.objects.create(
        number=f"tmp-{uuid4().hex[:16]}",  # настоящий номер — сразу после вставки
        user=user,
        delivery_method=delivery_method,
        payment_method=payment_method,
        address=address,
        subtotal=subtotal,
        discount=discount,
        delivery_price=delivery_price,
        total=subtotal - discount + delivery_price,
        promo=promo,
        promo_code=promo.code if promo else "",
    )
    order.number = f"VT-{settings.ORDER_NUMBER_START + order.pk}"
    order.save(update_fields=["number"])

    images = _main_images({v.product_id for v in variants})
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            product=variant.product,
            variant=variant,
            product_name=variant.product.name,
            product_slug=variant.product.slug,
            variant_name=variant.name,
            sku=variant.sku,
            image=images.get(variant.product_id, ""),
            price=variant.price,
            quantity=quantities[variant.pk],
        )
        for variant in variants
    )
    for variant in variants:
        ProductVariant.objects.filter(pk=variant.pk).update(
            stock=F("stock") - quantities[variant.pk]
        )

    clear_cart(user)
    return order


@transaction.atomic
def cancel_order(order):
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status not in Order.CANCELLABLE:
        raise ApiException("Этот заказ уже нельзя отменить.", code="order_not_cancellable")

    was_paid = order.status == Order.Status.PAID
    for item in order.items.all():
        ProductVariant.objects.filter(pk=item.variant_id).update(stock=F("stock") + item.quantity)
        if was_paid:
            # popularity — число проданных; оплаченный и отменённый заказ продажей не считается.
            Product.objects.filter(pk=item.product_id).update(
                popularity=Greatest(F("popularity") - item.quantity, 0)
            )

    order.status = Order.Status.CANCELLED
    order.cancelled_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at", "updated_at"])
    return order


def _address_snapshot(user, delivery_method, address_id):
    # Для самовывоза адрес не нужен: фронт присылает address_id всегда, но мы его игнорируем.
    if delivery_method != Order.Delivery.COURIER:
        return None
    if not address_id:
        raise ApiException("Укажите адрес доставки.", code="address_required")
    address = Address.objects.filter(pk=address_id, user=user).first()
    if address is None:
        raise ApiException("Адрес доставки не найден.", code="address_not_found")
    return {field: getattr(address, field) for field in ADDRESS_SNAPSHOT_FIELDS}


def _main_images(product_ids):
    result = {}
    for product_id, image in (
        ProductImage.objects.filter(product_id__in=product_ids)
        .order_by("product_id", "order", "id")
        .values_list("product_id", "image")
    ):
        result.setdefault(product_id, image)
    return result

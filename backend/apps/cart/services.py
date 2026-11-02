"""Серверная корзина. Фронт ведёт корзину у себя и только синхронизирует её:

- POST /cart/merge/ — сразу после входа: гостевая корзина сливается с серверной, при совпадении
  варианта берётся максимум количества (как mergeCart в моке фронта);
- PUT /cart/ — после каждого изменения (debounce 800 мс): корзина полностью заменяется.

Неизвестные варианты и товары, снятые с продажи, молча отбрасываются: в localStorage гостя
могут лежать устаревшие id, а одна такая строка не должна ломать синхронизацию всей корзины.
"""

from collections import defaultdict

from django.db import transaction
from django.db.models import Prefetch

from apps.catalog.models import ProductImage, ProductVariant

from .models import Cart, CartItem


def _sellable_variants(variant_ids):
    return ProductVariant.objects.filter(pk__in=variant_ids, product__is_active=True).in_bulk()


def _lock_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return Cart.objects.select_for_update().get(pk=cart.pk)


@transaction.atomic
def merge_cart(user, lines):
    cart = _lock_cart(user)
    wanted = defaultdict(int)
    for item in cart.items.all():
        wanted[item.variant_id] = item.quantity
    for line in lines:
        wanted[line["variant_id"]] = max(wanted[line["variant_id"]], line["quantity"])

    variants = _sellable_variants(wanted)
    cart.items.all().delete()
    # Количество не больше остатка; закончившиеся товары в серверную корзину не попадают.
    CartItem.objects.bulk_create(
        CartItem(
            cart=cart, variant_id=variant_id, quantity=min(quantity, variants[variant_id].stock)
        )
        for variant_id, quantity in wanted.items()
        if variant_id in variants and variants[variant_id].stock > 0
    )
    return cart


@transaction.atomic
def replace_cart(user, lines):
    cart = _lock_cart(user)
    wanted = defaultdict(int)
    for line in lines:
        wanted[line["variant_id"]] += line["quantity"]
    variants = _sellable_variants(wanted)
    cart.items.all().delete()
    CartItem.objects.bulk_create(
        CartItem(cart=cart, variant_id=variant_id, quantity=quantity)
        for variant_id, quantity in wanted.items()
        if variant_id in variants
    )
    return cart


def cart_with_items(cart):
    """Позиции для ServerCart: вариант, товар и его главное фото — за два запроса."""
    images = Prefetch(
        "variant__product__images", queryset=ProductImage.objects.order_by("order", "id")
    )
    cart.loaded_items = list(
        cart.items.select_related("variant__product").prefetch_related(images).order_by("id")
    )
    return cart


def clear_cart(user):
    CartItem.objects.filter(cart__user=user).delete()

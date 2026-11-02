"""Запросы каталога. Всё, что нужно ProductListItem, достаётся за фиксированное число запросов:
основной SELECT с аннотациями + prefetch вариантов."""

from django.db.models import Case, Exists, OuterRef, Q, Subquery, Value, When

from .models import Category, Product, ProductImage, ProductVariant

MAX_SEARCH_WORDS = 10


def product_list_queryset():
    variants = ProductVariant.objects.filter(product=OuterRef("pk"))
    # default_variant — самый дешёвый вариант в наличии, если таких нет — самый дешёвый вообще.
    best_variant = variants.annotate(
        out_of_stock=Case(When(stock__gt=0, then=Value(0)), default=Value(1))
    ).order_by("out_of_stock", "price", "id")
    main_image = ProductImage.objects.filter(product=OuterRef("pk")).order_by("order", "id")

    return (
        Product.objects.filter(is_active=True)
        .select_related("category", "brand")
        .prefetch_related("variants")
        .annotate(
            default_variant_id=Subquery(best_variant.values("id")[:1]),
            price_value=Subquery(best_variant.values("price")[:1]),
            old_price_value=Subquery(best_variant.values("old_price")[:1]),
            in_stock=Exists(variants.filter(stock__gt=0)),
            main_image=Subquery(main_image.values("image")[:1]),
        )
        # Товар без вариантов купить нельзя, а фронт ждёт default_variant всегда.
        .filter(default_variant_id__isnull=False)
        .order_by("-popularity", "id")
    )


def category_ids_with_descendants(slug):
    """id категории и всех её подкатегорий (любой глубины) за один запрос."""
    rows = list(Category.objects.values_list("id", "parent_id", "slug"))
    root = next((pk for pk, _, s in rows if s == slug), None)
    if root is None:
        return set()
    children = {}
    for pk, parent_id, _ in rows:
        children.setdefault(parent_id, []).append(pk)
    result, stack = set(), [root]
    while stack:
        pk = stack.pop()
        result.add(pk)
        stack.extend(children.get(pk, []))
    return result


def search_products(queryset, text):
    """Каждое слово должно встретиться в названии, бренде, категории или описании.

    Поиск по подстроке, как в мок-режиме фронта: подсказки в шапке приходят на недописанное
    слово («iph»), которое полнотекстовый поиск со стеммингом не найдёт.
    """
    for word in text.split()[:MAX_SEARCH_WORDS]:
        queryset = queryset.filter(
            Q(name__icontains=word)
            | Q(brand__name__icontains=word)
            | Q(category__name__icontains=word)
            | Q(description__icontains=word)
        )
    return queryset

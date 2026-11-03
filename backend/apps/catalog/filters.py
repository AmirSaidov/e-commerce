import django_filters as filters

from .selectors import category_ids_with_descendants, search_products

# Значения ordering, которые шлёт фронт (frontend/src/lib/catalog-params.ts) → поле сортировки.
ORDERING_FIELDS = {
    "-popularity": "-popularity",
    "price": "price_value",
    "-price": "-price_value",
    "-created_at": "-created_at",
    "-rating": "-rating",
}


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class ProductFilter(filters.FilterSet):
    category = filters.CharFilter(method="filter_category")
    brand = CharInFilter(field_name="brand__slug")
    price_min = filters.NumberFilter(field_name="price_value", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="price_value", lookup_expr="lte")
    rating_min = filters.NumberFilter(field_name="rating", lookup_expr="gte")
    in_stock = filters.BooleanFilter(method="filter_in_stock")
    on_sale = filters.BooleanFilter(method="filter_on_sale")
    search = filters.CharFilter(method="filter_search")
    ordering = filters.ChoiceFilter(
        choices=[(value, value) for value in ORDERING_FIELDS],
        method="filter_ordering",
        empty_label=None,
    )

    def filter_category(self, queryset, name, value):
        return queryset.filter(category_id__in=category_ids_with_descendants(value))

    # Фронт передаёт только true; false означает «не фильтровать», как в мок-режиме.
    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(in_stock=True) if value else queryset

    def filter_on_sale(self, queryset, name, value):
        return queryset.filter(old_price_value__isnull=False) if value else queryset

    def filter_search(self, queryset, name, value):
        return search_products(queryset, value)

    def filter_ordering(self, queryset, name, value):
        return queryset.order_by(ORDERING_FIELDS[value], "id")

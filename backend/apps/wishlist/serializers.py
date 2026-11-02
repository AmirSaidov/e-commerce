from rest_framework import serializers

from apps.catalog.models import Product


class WishlistAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Товар не найден.", code="product_not_found")
        return value

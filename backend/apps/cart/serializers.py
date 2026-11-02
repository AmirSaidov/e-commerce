from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.serializers import ProductVariantSerializer
from apps.core.media import absolute_media_url

MAX_LINES = 100
MAX_QUANTITY = 999


class CartLineSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, max_value=MAX_QUANTITY)


class CartLinesSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True, max_length=MAX_LINES)


class CartProductSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    image = serializers.SerializerMethodField()

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, product):
        images = product.images.all()  # prefetch, отсортировано по order
        return absolute_media_url(self.context.get("request"), images[0].image if images else None)


class CartItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    variant = ProductVariantSerializer()
    product = CartProductSerializer(source="variant.product")
    quantity = serializers.IntegerField()


class ServerCartSerializer(serializers.Serializer):
    """ServerCart: {id, items: [{id, variant, product: {id, name, slug, image}, quantity}]}."""

    id = serializers.IntegerField()
    items = CartItemSerializer(source="loaded_items", many=True)


class PromoCheckRequestSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class PromoCheckSerializer(serializers.Serializer):
    code = serializers.CharField()
    type = serializers.CharField()
    value = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2)

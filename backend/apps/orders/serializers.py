from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.cart.serializers import MAX_LINES, CartLineSerializer
from apps.core.media import absolute_media_url

from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "variant_id",
            "product_name",
            "product_slug",
            "variant_name",
            "image",
            "price",
            "quantity",
        )

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, item):
        return absolute_media_url(self.context.get("request"), item.image)


class OrderAddressSerializer(serializers.Serializer):
    city = serializers.CharField()
    street = serializers.CharField()
    building = serializers.CharField()
    apartment = serializers.CharField()
    postal_code = serializers.CharField()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    address = OrderAddressSerializer(allow_null=True)
    promo_code = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "number",
            "status",
            "created_at",
            "items",
            "address",
            "delivery_method",
            "payment_method",
            "subtotal",
            "discount",
            "delivery_price",
            "total",
            "promo_code",
        )

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_promo_code(self, order):
        return order.promo_code or None  # фронт ждёт null, если промокода не было


class CreateOrderSerializer(serializers.Serializer):
    """CreateOrderPayload из frontend/src/lib/api/types.ts."""

    items = CartLineSerializer(many=True, max_length=MAX_LINES, allow_empty=True)
    delivery_method = serializers.ChoiceField(choices=Order.Delivery.choices)
    payment_method = serializers.ChoiceField(choices=Order.Payment.choices)
    address_id = serializers.IntegerField(required=False, allow_null=True)
    promo_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=32
    )

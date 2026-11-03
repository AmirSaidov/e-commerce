from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.throttling import AuthRateThrottle

from . import serializers
from .promo import calc_discount, get_valid_promo
from .services import cart_with_items, merge_cart, replace_cart


class CartView(APIView):
    @extend_schema(request=serializers.CartLinesSerializer, responses={204: None})
    def put(self, request):
        """Полностью заменяет серверную корзину."""
        payload = serializers.CartLinesSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        replace_cart(request.user, payload.validated_data["items"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class CartMergeView(APIView):
    @extend_schema(
        request=serializers.CartLinesSerializer, responses=serializers.ServerCartSerializer
    )
    def post(self, request):
        """Сливает гостевую корзину с серверной (максимум количества) и возвращает итог."""
        payload = serializers.CartLinesSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        cart = cart_with_items(merge_cart(request.user, payload.validated_data["items"]))
        return Response(serializers.ServerCartSerializer(cart, context={"request": request}).data)


class ApplyPromoView(APIView):
    """Только проверяет промокод и считает скидку; ничего не сохраняет. Доступен гостям."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]
    throttle_scope = "promo"  # защита от перебора кодов

    @extend_schema(
        request=serializers.PromoCheckRequestSerializer,
        responses=serializers.PromoCheckSerializer,
    )
    def post(self, request):
        payload = serializers.PromoCheckRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        subtotal = payload.validated_data["subtotal"]
        promo = get_valid_promo(payload.validated_data["code"], subtotal)
        data = {
            "code": promo.code,
            "type": promo.type,
            "value": promo.value,
            "discount": calc_discount(subtotal, promo),
        }
        return Response(serializers.PromoCheckSerializer(data).data)

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.orders.models import Order

from . import gateway, services


class CheckoutSessionRequestSerializer(serializers.Serializer):
    order_number = serializers.CharField(max_length=20)


class CheckoutSessionView(APIView):
    @extend_schema(
        request=CheckoutSessionRequestSerializer,
        responses=inline_serializer("CheckoutSession", {"url": serializers.URLField()}),
    )
    def post(self, request):
        payload = CheckoutSessionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        order = (
            Order.objects.filter(user=request.user, number=payload.validated_data["order_number"])
            .select_related("user")
            .prefetch_related("items")
            .first()
        )
        if order is None:
            raise NotFound("Заказ не найден.")
        return Response({"url": services.start_checkout(order)})


class StripeWebhookView(APIView):
    """Вебхук Stripe: подпись проверяется по STRIPE_WEBHOOK_SECRET, тело читается «как есть»."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        request=None,
        responses=inline_serializer("StripeWebhookResult", {"status": serializers.CharField()}),
    )
    def post(self, request):
        event = gateway.construct_event(request.body, request.headers.get("Stripe-Signature", ""))
        return Response({"status": services.handle_event(event)})

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from .models import Order
from .serializers import CreateOrderSerializer, OrderSerializer
from .services import cancel_order, create_order


class OrderViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Заказы видит только владелец; чужой номер — 404."""

    serializer_class = OrderSerializer
    lookup_field = "number"
    lookup_value_regex = "[A-Za-z0-9-]+"

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # генерация OpenAPI-схемы
            return Order.objects.none()
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    def get_object(self):
        order = self.get_queryset().filter(number=self.kwargs["number"]).first()
        if order is None:
            raise NotFound("Заказ не найден.")  # тот же текст, что в моке фронта
        return order

    @extend_schema(request=CreateOrderSerializer, responses={201: OrderSerializer})
    def create(self, request):
        payload = CreateOrderSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        order = create_order(request.user, **payload.validated_data)
        return Response(self._serialize(order), status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=OrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, number=None):
        order = cancel_order(self.get_object())
        return Response(self._serialize(order))

    def _serialize(self, order):
        order = self.get_queryset().get(pk=order.pk)  # свежие items одним prefetch
        return self.get_serializer(order).data

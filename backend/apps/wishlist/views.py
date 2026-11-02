from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Subquery
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.selectors import product_list_queryset
from apps.catalog.serializers import ProductListSerializer

from .models import WishlistItem
from .serializers import WishlistAddSerializer


class WishlistView(APIView):
    @extend_schema(responses=ProductListSerializer(many=True))
    def get(self, request):
        """ProductListItem[] без пагинации, последние добавленные — сверху."""
        items = WishlistItem.objects.filter(user=request.user, product=OuterRef("pk"))
        products = (
            product_list_queryset()
            .filter(Exists(items))
            .annotate(added_at=Subquery(items.values("created_at")[:1]))
            .order_by("-added_at", "-id")
        )
        return Response(
            ProductListSerializer(products, many=True, context={"request": request}).data
        )

    @extend_schema(request=WishlistAddSerializer, responses={204: None})
    def post(self, request):
        """Идемпотентно: повторное добавление — тоже 204."""
        serializer = WishlistAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                WishlistItem.objects.get_or_create(
                    user=request.user, product_id=serializer.validated_data["product_id"]
                )
        except IntegrityError:
            pass  # параллельный запрос уже добавил этот товар
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistItemView(APIView):
    @extend_schema(responses={204: None})
    def delete(self, request, product_id):
        """Удаление по id товара, а не записи; идемпотентно."""
        WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

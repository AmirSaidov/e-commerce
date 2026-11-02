from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import validate_with_summary

from . import serializers
from .filters import ProductFilter
from .models import Brand, Category, Product, Review
from .reviews import create_review, ensure_can_review
from .selectors import product_list_queryset, search_products

RELATED_LIMIT = 8
SEARCH_LIMIT = 6


class PublicCatalogMixin:
    # Каталог открыт всем и не читает Authorization: серверные компоненты Next ходят без токена,
    # а просроченный токен в браузере не должен ломать витрину.
    authentication_classes = []
    permission_classes = [AllowAny]


class CategoryTreeView(PublicCatalogMixin, generics.GenericAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    pagination_class = None

    @extend_schema(responses=serializers.CategorySerializer(many=True))
    def get(self, request):
        categories = list(self.get_queryset())
        for category in categories:
            category.tree_children = []
        by_id = {category.id: category for category in categories}
        roots = []
        for category in categories:
            parent = by_id.get(category.parent_id)
            (parent.tree_children if parent else roots).append(category)
        return Response(self.get_serializer(roots, many=True).data)


class BrandListView(PublicCatalogMixin, generics.ListAPIView):
    queryset = Brand.objects.all()
    serializer_class = serializers.BrandSerializer
    pagination_class = None


class ProductViewSet(PublicCatalogMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProductFilter

    def get_queryset(self):
        queryset = product_list_queryset()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("images")
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return serializers.ProductDetailSerializer
        return serializers.ProductListSerializer

    def filter_queryset(self, queryset):
        # Фильтры каталога относятся только к списку, не к карточке и не к related.
        return super().filter_queryset(queryset) if self.action == "list" else queryset

    @extend_schema(responses=serializers.ProductListSerializer(many=True))
    @action(detail=True, pagination_class=None)
    def related(self, request, slug=None):
        """До 8 товаров: сначала из той же категории, затем из соседних (тот же родитель)."""
        product = self.get_object()
        others = product_list_queryset().exclude(pk=product.pk)
        result = list(others.filter(category_id=product.category_id)[:RELATED_LIMIT])
        parent_id = product.category.parent_id
        if len(result) < RELATED_LIMIT and parent_id is not None:
            siblings = others.filter(category__parent_id=parent_id).exclude(
                category_id=product.category_id
            )
            result += list(siblings[: RELATED_LIMIT - len(result)])
        return Response(self.get_serializer(result, many=True).data)

    @extend_schema(
        parameters=[OpenApiParameter("q", str, required=True)],
        responses=serializers.ProductListSerializer(many=True),
    )
    @action(detail=False, pagination_class=None)
    def search(self, request):
        """Подсказки в шапке: до 6 товаров, самые популярные."""
        text = request.query_params.get("q", "").strip()
        if not text:
            return Response([])
        products = search_products(product_list_queryset(), text)[:SEARCH_LIMIT]
        return Response(self.get_serializer(products, many=True).data)


class ReviewPagination(PageNumberPagination):
    page_size = 5  # как в моке фронта; page_size из запроса не принимаем


class ProductReviewsView(generics.ListCreateAPIView):
    """GET — отзывы товара (публично, по 5, новые сверху); POST — свой отзыв (multipart)."""

    serializer_class = serializers.ReviewSerializer
    pagination_class = ReviewPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def _is_read(self):
        # request бывает None, когда drf-spectacular строит схему
        return getattr(self.request, "method", None) in SAFE_METHODS

    def get_authenticators(self):
        # Список не читает Authorization (как весь каталог), отправка отзыва — только с токеном.
        return [] if self._is_read() else super().get_authenticators()

    def get_permissions(self):
        return [AllowAny()] if self._is_read() else [IsAuthenticated()]

    def get_product(self):
        product = Product.objects.filter(slug=self.kwargs["slug"], is_active=True).first()
        if product is None:
            raise NotFound("Товар не найден.")
        return product

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # генерация OpenAPI-схемы
            return Review.objects.none()
        return (
            Review.objects.filter(product=self.get_product())
            .select_related("user")
            .prefetch_related("images")
            .order_by("-created_at", "-id")
        )

    @extend_schema(
        request={"multipart/form-data": serializers.ReviewCreateSerializer},
        responses={201: serializers.ReviewSerializer},
    )
    def post(self, request, slug):
        product = self.get_product()
        # Тело (multipart с фото) дочитываем до любого отказа: если ответить, не прочитав его,
        # сервер закрывает соединение с непрочитанными данными, и клиент может получить обрыв
        # вместо ответа (воспроизводилось на runserver под Windows).
        payload = serializers.ReviewCreateSerializer(data=request.data)
        # Право на отзыв проверяем раньше формы — порядок ошибок как в моке фронта.
        ensure_can_review(request.user, product)
        data = validate_with_summary(payload)
        review = create_review(
            request.user,
            product,
            rating=data["rating"],
            text=data["text"],
            images=data.get("images", []),
        )
        review = self.get_queryset().get(pk=review.pk)
        return Response(self.get_serializer(review).data, status=status.HTTP_201_CREATED)

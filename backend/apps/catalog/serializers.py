from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.core.media import absolute_media_url

from .models import Brand, Category, Product, ProductImage, ProductVariant, Review
from .reviews import author_name


class AbsoluteImageField(serializers.ImageField):
    def to_representation(self, value):
        return absolute_media_url(self.context.get("request"), value)


class CategoryRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")


class BrandRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ("id", "name", "slug")


class CategorySerializer(serializers.ModelSerializer):
    image = AbsoluteImageField(allow_null=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ("id", "name", "slug", "parent", "image", "children")

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_children(self, obj):
        # Дерево собирается во view из одного запроса и кладётся в tree_children.
        return CategorySerializer(obj.tree_children, many=True, context=self.context).data


class BrandSerializer(serializers.ModelSerializer):
    logo = AbsoluteImageField(allow_null=True)

    class Meta:
        model = Brand
        fields = ("id", "name", "slug", "logo")


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ("id", "sku", "name", "price", "old_price", "stock")


class ProductImageSerializer(serializers.ModelSerializer):
    image = AbsoluteImageField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt", "order")


class ProductListSerializer(serializers.ModelSerializer):
    """ProductListItem. Ожидает queryset из selectors.product_list_queryset()."""

    category = CategoryRefSerializer()
    brand = BrandRefSerializer()
    image = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    old_price = serializers.SerializerMethodField()
    rating = serializers.FloatField()
    in_stock = serializers.BooleanField()
    variants_count = serializers.SerializerMethodField()
    default_variant = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            "id",
            "name",
            "slug",
            "category",
            "brand",
            "image",
            "price",
            "old_price",
            "rating",
            "reviews_count",
            "in_stock",
            "variants_count",
            "default_variant",
            "created_at",
        )

    def _default_variant(self, obj):
        # Варианты уже в prefetch — берём выбранный в аннотации, без лишних запросов.
        if not hasattr(obj, "_default_variant_data"):
            variant = next(v for v in obj.variants.all() if v.id == obj.default_variant_id)
            obj._default_variant_data = ProductVariantSerializer(variant).data
        return obj._default_variant_data

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_image(self, obj):
        return absolute_media_url(self.context.get("request"), obj.main_image)

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2))
    def get_price(self, obj):
        return self._default_variant(obj)["price"]

    @extend_schema_field(serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True))
    def get_old_price(self, obj):
        return self._default_variant(obj)["old_price"]

    @extend_schema_field(serializers.IntegerField())
    def get_variants_count(self, obj):
        return len(obj.variants.all())

    @extend_schema_field(ProductVariantSerializer)
    def get_default_variant(self, obj):
        return self._default_variant(obj)


class ProductDetailSerializer(ProductListSerializer):
    images = ProductImageSerializer(many=True)
    variants = ProductVariantSerializer(many=True)

    class Meta(ProductListSerializer.Meta):
        fields = (*ProductListSerializer.Meta.fields, "description", "specs", "images", "variants")


# ---------- Отзывы ----------

REVIEW_MAX_IMAGES = 5
REVIEW_IMAGE_MAX_SIZE = 5 * 1024 * 1024  # как MAX_IMAGE_SIZE в форме отзыва на фронте
REVIEW_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}  # как IMAGE_TYPES на фронте


class ReviewSerializer(serializers.ModelSerializer):
    """Review фронта: {id, author, rating, text, images: string[], created_at}."""

    author = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ("id", "author", "rating", "text", "images", "created_at")

    def get_author(self, review) -> str:
        return author_name(review.user)

    def get_images(self, review) -> list[str]:
        request = self.context.get("request")
        return [absolute_media_url(request, image.image) for image in review.images.all()]


class ReviewCreateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        error_messages={
            "min_value": "Поставьте оценку от 1 до 5.",
            "max_value": "Поставьте оценку от 1 до 5.",
            "required": "Поставьте оценку.",
        },
    )
    text = serializers.CharField(
        min_length=10,
        max_length=2000,
        error_messages={
            "min_length": "Напишите хотя бы пару предложений — от 10 символов.",
            "max_length": "Отзыв слишком длинный — не больше 2000 символов.",
            "blank": "Напишите текст отзыва.",
            "required": "Напишите текст отзыва.",
        },
    )
    images = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        max_length=REVIEW_MAX_IMAGES,
        error_messages={"max_length": f"Не больше {REVIEW_MAX_IMAGES} фото."},
    )

    def validate_images(self, files):
        for file in files:
            if file.size > REVIEW_IMAGE_MAX_SIZE:
                raise serializers.ValidationError("Каждое фото — до 5 МБ.", code="image_too_large")
            if getattr(file.image, "format", None) not in REVIEW_IMAGE_FORMATS:
                raise serializers.ValidationError(
                    "Загрузите фото в формате JPEG, PNG или WEBP.", code="image_format"
                )
        return files

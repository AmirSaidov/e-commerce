from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count
from django.utils import timezone


class Category(models.Model):
    name = models.CharField("название", max_length=100)
    slug = models.SlugField("slug", max_length=100, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="родитель",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    image = models.ImageField("картинка", upload_to="categories/", blank=True)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"
        ordering = ("order", "name")

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField("название", max_length=100)
    slug = models.SlugField("slug", max_length=100, unique=True)
    logo = models.ImageField("логотип", upload_to="brands/", blank=True)

    class Meta:
        verbose_name = "бренд"
        verbose_name_plural = "бренды"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField("название", max_length=255)
    slug = models.SlugField("slug", max_length=255, unique=True)
    description = models.TextField("описание", blank=True)
    specs = models.JSONField("характеристики", default=dict, blank=True)
    category = models.ForeignKey(
        Category, verbose_name="категория", on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, verbose_name="бренд", on_delete=models.PROTECT, related_name="products"
    )
    # Денормализованы: rating/reviews_count пересчитываются при изменении отзывов,
    # popularity — число проданных штук, растёт при оплате заказа.
    rating = models.DecimalField("рейтинг", max_digits=2, decimal_places=1, default=Decimal("0"))
    reviews_count = models.PositiveIntegerField("отзывов", default=0)
    popularity = models.PositiveIntegerField("продано, шт.", default=0, db_index=True)
    is_active = models.BooleanField("активен", default=True)
    created_at = models.DateTimeField("создан", default=timezone.now, db_index=True)
    updated_at = models.DateTimeField("изменён", auto_now=True)

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ("-popularity", "id")

    def __str__(self):
        return self.name

    def recalculate_rating(self):
        stats = self.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
        avg = Decimal(str(stats["avg"] or 0)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        Product.objects.filter(pk=self.pk).update(rating=avg, reviews_count=stats["count"])
        self.rating, self.reviews_count = avg, stats["count"]


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="товар", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("файл", upload_to="products/")
    alt = models.CharField("alt", max_length=255, blank=True)
    order = models.PositiveIntegerField("порядок", default=0)

    class Meta:
        verbose_name = "фото товара"
        verbose_name_plural = "фото товаров"
        ordering = ("order", "id")

    def __str__(self):
        return self.alt or self.image.name


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="товар", on_delete=models.CASCADE, related_name="variants"
    )
    sku = models.CharField("артикул", max_length=64, unique=True)
    # Одна строка с атрибутами варианта («256 ГБ», «Чёрный», «16 ГБ / 512 ГБ») — как в типе фронта.
    name = models.CharField("вариант", max_length=100)
    price = models.DecimalField("цена", max_digits=12, decimal_places=2)
    old_price = models.DecimalField(
        "старая цена", max_digits=12, decimal_places=2, null=True, blank=True
    )
    stock = models.PositiveIntegerField("остаток", default=0)

    class Meta:
        verbose_name = "вариант товара"
        verbose_name_plural = "варианты товаров"
        ordering = ("price", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0), name="catalog_variant_price_non_negative"
            ),
        ]

    def __str__(self):
        return f"{self.product.name} — {self.name}"


class Review(models.Model):
    product = models.ForeignKey(
        Product, verbose_name="товар", on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="автор",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        "оценка", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("текст")
    created_at = models.DateTimeField("создан", default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(fields=("product", "user"), name="catalog_review_unique_user"),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5), name="catalog_review_rating_1_5"
            ),
        ]

    def __str__(self):
        return f"{self.product} — {self.rating}★"


def review_image_path(instance, filename):
    # Имя от пользователя в хранилище не попадает: случайное имя, папки по месяцам.
    suffix = Path(filename).suffix.lower()[:5] or ".jpg"
    return f"reviews/{timezone.now():%Y/%m}/{uuid4().hex}{suffix}"


class ReviewImage(models.Model):
    review = models.ForeignKey(
        Review, verbose_name="отзыв", on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField("файл", upload_to=review_image_path)

    class Meta:
        verbose_name = "фото отзыва"
        verbose_name_plural = "фото отзывов"
        ordering = ("id",)

    def __str__(self):
        return self.image.name

from django.conf import settings
from django.db import models

from apps.cart.models import PromoCode
from apps.catalog.models import Product, ProductVariant


class Order(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "создан"
        PAID = "paid", "оплачен"
        ASSEMBLING = "assembling", "собирается"
        SHIPPED = "shipped", "передан в доставку"
        DELIVERED = "delivered", "доставлен"
        CANCELLED = "cancelled", "отменён"

    class Delivery(models.TextChoices):
        COURIER = "courier", "курьером"
        PICKUP = "pickup", "самовывоз"

    class Payment(models.TextChoices):
        CARD = "card", "картой онлайн"
        CASH = "cash", "при получении"

    CANCELLABLE = (Status.CREATED, Status.PAID)

    # VT-{100000 + id}: последовательный и уникальный, присваивается сразу после вставки.
    number = models.CharField("номер", max_length=20, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="покупатель",
        on_delete=models.PROTECT,
        related_name="orders",
    )
    status = models.CharField(
        "статус", max_length=20, choices=Status.choices, default=Status.CREATED, db_index=True
    )
    delivery_method = models.CharField("доставка", max_length=10, choices=Delivery.choices)
    payment_method = models.CharField("оплата", max_length=10, choices=Payment.choices)
    # Снимок адреса на момент заказа (без id и is_default); для самовывоза — null.
    address = models.JSONField("адрес", null=True, blank=True)

    subtotal = models.DecimalField("товары", max_digits=12, decimal_places=2)
    discount = models.DecimalField("скидка", max_digits=12, decimal_places=2, default=0)
    delivery_price = models.DecimalField("доставка, ₸", max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField("итого", max_digits=12, decimal_places=2)
    promo = models.ForeignKey(
        PromoCode,
        verbose_name="промокод",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    promo_code = models.CharField("код промокода", max_length=32, blank=True)

    created_at = models.DateTimeField("создан", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("изменён", auto_now=True)
    paid_at = models.DateTimeField("оплачен", null=True, blank=True)
    cancelled_at = models.DateTimeField("отменён", null=True, blank=True)

    # Stripe: последняя созданная Checkout Session и платёж, которым заказ оплачен.
    stripe_session_id = models.CharField("Stripe Checkout Session", max_length=255, blank=True)
    stripe_payment_intent = models.CharField("Stripe PaymentIntent", max_length=255, blank=True)

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return self.number


class OrderItem(models.Model):
    """Снимок позиции: название, вариант, артикул, цена и картинка на момент заказа."""

    order = models.ForeignKey(
        Order, verbose_name="заказ", on_delete=models.CASCADE, related_name="items"
    )
    # PROTECT: товар с заказами не удаляют, а снимают с продажи (is_active=False).
    product = models.ForeignKey(
        Product, verbose_name="товар", on_delete=models.PROTECT, related_name="order_items"
    )
    variant = models.ForeignKey(
        ProductVariant, verbose_name="вариант", on_delete=models.PROTECT, related_name="order_items"
    )
    product_name = models.CharField("товар", max_length=255)
    product_slug = models.CharField("slug товара", max_length=255)
    variant_name = models.CharField("вариант", max_length=100)
    sku = models.CharField("артикул", max_length=64)
    image = models.CharField("картинка", max_length=255, blank=True)  # путь в хранилище
    price = models.DecimalField("цена", max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField("количество")

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"
        ordering = ("id",)

    def __str__(self):
        return f"{self.product_name} ({self.variant_name}) × {self.quantity}"

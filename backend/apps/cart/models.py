from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.catalog.models import ProductVariant


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        on_delete=models.CASCADE,
        related_name="cart",
    )
    updated_at = models.DateTimeField("изменена", auto_now=True)

    class Meta:
        verbose_name = "корзина"
        verbose_name_plural = "корзины"

    def __str__(self):
        return f"Корзина {self.user}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart, verbose_name="корзина", on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(
        ProductVariant, verbose_name="вариант", on_delete=models.CASCADE, related_name="+"
    )
    quantity = models.PositiveIntegerField("количество", validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "позиция корзины"
        verbose_name_plural = "позиции корзины"
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(fields=("cart", "variant"), name="cart_item_unique_variant"),
        ]

    def __str__(self):
        return f"{self.variant} × {self.quantity}"


class PromoCode(models.Model):
    class Type(models.TextChoices):
        PERCENT = "percent", "процент"
        FIXED = "fixed", "сумма, ₸"

    # Хранится в верхнем регистре; пользователь может ввести в любом.
    code = models.CharField("код", max_length=32, unique=True)
    type = models.CharField("тип", max_length=10, choices=Type.choices)
    value = models.DecimalField(
        "значение", max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    expires_at = models.DateTimeField("действует до", null=True, blank=True)
    is_active = models.BooleanField("активен", default=True)
    min_subtotal = models.DecimalField(
        "минимальная сумма заказа", max_digits=12, decimal_places=2, null=True, blank=True
    )
    usage_limit = models.PositiveIntegerField(
        "лимит использований", null=True, blank=True, help_text="Пусто — без ограничений"
    )
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "промокод"
        verbose_name_plural = "промокоды"
        ordering = ("code",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(type="percent") | models.Q(value__lte=100),
                name="cart_promo_percent_max_100",
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

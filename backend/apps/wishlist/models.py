from django.conf import settings
from django.db import models

from apps.catalog.models import Product


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="пользователь",
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    product = models.ForeignKey(
        Product, verbose_name="товар", on_delete=models.CASCADE, related_name="wishlist_items"
    )
    created_at = models.DateTimeField("добавлен", auto_now_add=True)

    class Meta:
        verbose_name = "товар в избранном"
        verbose_name_plural = "избранное"
        ordering = ("-created_at", "-id")
        constraints = [
            models.UniqueConstraint(fields=("user", "product"), name="wishlist_unique_product"),
        ]

    def __str__(self):
        return f"{self.user} — {self.product}"

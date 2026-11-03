from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField("email", unique=True)
    phone = models.CharField("телефон", max_length=32, blank=True)
    # Фронт ждёт поле avatar в User; загрузки аватара пока нет, поле всегда может быть пустым.
    avatar = models.ImageField("аватар", upload_to="avatars/", blank=True, null=True)
    is_email_verified = models.BooleanField("email подтверждён", default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)


class Address(models.Model):
    user = models.ForeignKey(
        User, verbose_name="пользователь", on_delete=models.CASCADE, related_name="addresses"
    )
    city = models.CharField("город", max_length=100)
    street = models.CharField("улица", max_length=200)
    building = models.CharField("дом", max_length=20)
    apartment = models.CharField("квартира", max_length=10, blank=True)
    postal_code = models.CharField("индекс", max_length=6, blank=True)
    is_default = models.BooleanField("основной", default=False)
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "адрес"
        verbose_name_plural = "адреса"
        ordering = ("id",)
        constraints = [
            # Не больше одного основного адреса на пользователя (частичный уникальный индекс).
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(is_default=True),
                name="users_address_one_default",
            ),
        ]

    def __str__(self):
        parts = [self.city, f"{self.street}, {self.building}"]
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)

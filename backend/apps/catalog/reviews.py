"""Отзывы о товарах. Правила и тексты ошибок — как createReview в моке фронта:

- оставить отзыв можно только на полученный товар (есть свой заказ в статусе delivered с этим
  товаром), иначе 403 review_not_purchased;
- один отзыв на товар от пользователя, иначе 400 review_exists.
"""

from django.db import IntegrityError, transaction

from apps.core.exceptions import ApiException
from apps.orders.models import Order, OrderItem

from .models import Review, ReviewImage

REVIEW_EXISTS = "Вы уже оставили отзыв на этот товар."


def author_name(user):
    """«Имя Ф.»; без фамилии — только имя; без имени — «Покупатель»."""
    first, last = user.first_name.strip(), user.last_name.strip()
    if not first:
        return "Покупатель"
    return f"{first} {last[0]}." if last else first


def ensure_can_review(user, product):
    purchased = OrderItem.objects.filter(
        order__user=user, order__status=Order.Status.DELIVERED, product=product
    ).exists()
    if not purchased:
        raise ApiException(
            "Отзыв можно оставить только на полученный товар.",
            code="review_not_purchased",
            status_code=403,
        )
    if Review.objects.filter(user=user, product=product).exists():
        raise ApiException(REVIEW_EXISTS, code="review_exists")


@transaction.atomic
def create_review(user, product, *, rating, text, images):
    try:
        with transaction.atomic():
            review = Review.objects.create(user=user, product=product, rating=rating, text=text)
    except IntegrityError as exc:  # параллельная отправка той же формы
        raise ApiException(REVIEW_EXISTS, code="review_exists") from exc
    for image in images:
        ReviewImage.objects.create(review=review, image=image)
    return review

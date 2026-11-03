import io
import re
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.catalog import serializers as catalog_serializers
from apps.catalog.models import Review, ReviewImage
from apps.catalog.reviews import author_name
from apps.catalog.tests.factories import ReviewFactory, make_product
from apps.orders.models import Order
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = pytest.mark.django_db

REVIEW_FIELDS = {"id", "author", "rating", "text", "images", "created_at"}
TEXT = "Отличные наушники, шумоподавление работает на ура."


@pytest.fixture(autouse=True)
def media_in_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"


@pytest.fixture
def product():
    return make_product(slug="airpods", name="AirPods Pro 2")


def url(slug="airpods"):
    return f"/api/v1/products/{slug}/reviews/"


def api_list_ids(client):
    return [r["id"] for r in client.get(url()).json()["results"]]


def image_file(name="photo.png", fmt="PNG", size=(8, 8)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


def deliver(user, product, status="delivered"):
    """Заказ пользователя с этим товаром в нужном статусе."""
    variant = product.variants.first()
    order = Order.objects.create(
        number=f"VT-T{Order.objects.count() + 1}",
        user=user,
        status=status,
        delivery_method="pickup",
        payment_method="cash",
        subtotal=variant.price,
        total=variant.price,
    )
    order.items.create(
        product=product,
        variant=variant,
        product_name=product.name,
        product_slug=product.slug,
        variant_name=variant.name,
        sku=variant.sku,
        price=variant.price,
        quantity=1,
    )
    return order


def post_review(client, slug="airpods", **data):
    payload = {"rating": 5, "text": TEXT, **data}
    return client.post(url(slug), payload, format="multipart")


# ---------- Список ----------


def test_list_is_public_paginated_by_5_newest_first(api_client, product):
    reviews = [ReviewFactory(product=product, text=f"Отзыв номер {n}") for n in range(7)]

    res = api_client.get(url())

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 7
    assert len(data["results"]) == 5
    assert data["next"].endswith("/api/v1/products/airpods/reviews/?page=2")
    assert [r["id"] for r in data["results"]] == [r.id for r in reversed(reviews)][:5]
    assert set(data["results"][0]) == REVIEW_FIELDS
    assert len(api_client.get(url(), {"page": 2}).json()["results"]) == 2
    assert len(api_client.get(url(), {"page_size": 50}).json()["results"]) == 5


def test_list_item_shape(api_client, product):
    user = UserFactory(first_name="Айгерим", last_name="Сапарова")
    review = ReviewFactory(product=product, user=user, rating=4, text=TEXT)
    ReviewImage.objects.create(review=review, image="reviews/2026/11/a.png")

    item = api_client.get(url()).json()["results"][0]

    assert item["author"] == "Айгерим С."
    assert item["rating"] == 4
    assert item["text"] == TEXT
    assert item["images"] == ["http://testserver/media/reviews/2026/11/a.png"]
    assert item["created_at"].endswith("+05:00")


def test_list_only_this_product(api_client, product):
    ReviewFactory(product=product)
    ReviewFactory(product=make_product(slug="other"))

    assert api_client.get(url()).json()["count"] == 1


def test_list_unknown_or_hidden_product_is_404(api_client):
    make_product(slug="hidden", is_active=False)

    for slug in ("missing", "hidden"):
        res = api_client.get(url(slug))
        assert res.status_code == 404
        assert res.data["detail"] == "Товар не найден."


def test_list_ignores_invalid_bearer(api_client, product):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired-garbage")

    assert api_client.get(url()).status_code == 200


def test_list_query_count(api_client, product, django_assert_max_num_queries):
    for _ in range(5):
        review = ReviewFactory(product=product)
        ReviewImage.objects.create(review=review, image="reviews/x.png")

    # товар + COUNT + отзывы с авторами + prefetch фото
    with django_assert_max_num_queries(4):
        assert len(api_client.get(url()).json()["results"]) == 5


@pytest.mark.parametrize(
    ("first", "last", "expected"),
    [("Айгерим", "Сапарова", "Айгерим С."), ("Тимур", "", "Тимур"), ("", "", "Покупатель")],
)
def test_author_name(first, last, expected):
    assert author_name(UserFactory.build(first_name=first, last_name=last)) == expected


# ---------- Создание ----------


def test_create_review_with_photos(auth_client, user, product):
    deliver(user, product)

    res = post_review(
        auth_client, rating=4, images=[image_file("a.png"), image_file("b.jpg", "JPEG")]
    )

    assert res.status_code == 201, res.data
    data = res.json()
    assert set(data) == REVIEW_FIELDS
    assert data["author"] == "Айбек С."
    assert data["rating"] == 4 and data["text"] == TEXT
    assert len(data["images"]) == 2
    # имена случайные (uuid), а не «a.png»/«b.jpg» от пользователя; папки по месяцам
    pattern = r"^http://testserver/media/reviews/\d{4}/\d{2}/[0-9a-f]{32}\.(png|jpg)$"
    assert all(re.match(pattern, u) for u in data["images"]), data["images"]
    assert data["images"][0].endswith(".png") and data["images"][1].endswith(".jpg")

    # рейтинг товара пересчитан
    product.refresh_from_db()
    assert product.reviews_count == 1 and product.rating == Decimal("4.0")
    # отзыв сразу виден в списке
    assert api_list_ids(auth_client) == [data["id"]]


def test_create_review_without_photos(auth_client, user, product):
    deliver(user, product)

    res = post_review(auth_client)

    assert res.status_code == 201
    assert res.data["images"] == []


def test_rating_is_recalculated_with_existing_reviews(auth_client, user, product):
    ReviewFactory(product=product, rating=5)
    deliver(user, product)

    post_review(auth_client, rating=4)

    product.refresh_from_db()
    assert (product.rating, product.reviews_count) == (Decimal("4.5"), 2)


@pytest.mark.parametrize("status", [None, "created", "paid", "shipped", "cancelled"])
def test_review_not_purchased(auth_client, user, product, status):
    if status:
        deliver(user, product, status=status)

    res = post_review(auth_client)

    assert res.status_code == 403
    assert res.data == {
        "detail": "Отзыв можно оставить только на полученный товар.",
        "code": "review_not_purchased",
        "fields": {},
    }
    assert not Review.objects.exists()


def test_delivered_other_product_does_not_count(auth_client, user, product):
    deliver(user, make_product(slug="other"))

    assert post_review(auth_client).data["code"] == "review_not_purchased"


def test_someone_elses_delivered_order_does_not_count(auth_client, product):
    deliver(UserFactory(), product)

    assert post_review(auth_client).status_code == 403


def test_review_exists(auth_client, user, product):
    deliver(user, product)
    post_review(auth_client)

    res = post_review(auth_client, rating=1)

    assert res.status_code == 400
    assert res.data == {
        "detail": "Вы уже оставили отзыв на этот товар.",
        "code": "review_exists",
        "fields": {},
    }
    assert Review.objects.get().rating == 5


@pytest.mark.parametrize(
    ("data", "field", "detail"),
    [
        ({"rating": 0}, "rating", "Поставьте оценку от 1 до 5."),
        ({"rating": 6}, "rating", "Поставьте оценку от 1 до 5."),
        ({"text": "Коротко"}, "text", "Напишите хотя бы пару предложений — от 10 символов."),
        ({"text": "x" * 2001}, "text", "Отзыв слишком длинный — не больше 2000 символов."),
    ],
)
def test_validation_error_goes_to_detail(auth_client, user, product, data, field, detail):
    deliver(user, product)

    res = post_review(auth_client, **data)

    assert res.status_code == 400
    assert res.data["detail"] == detail  # форма отзыва на фронте показывает только detail
    assert res.data["fields"][field] == [detail]
    assert res.data["code"] == "validation_error"


def test_too_many_photos(auth_client, user, product):
    deliver(user, product)

    res = post_review(auth_client, images=[image_file(f"{n}.png") for n in range(6)])

    assert res.status_code == 400
    assert res.data["detail"] == "Не больше 5 фото."
    assert not ReviewImage.objects.exists()


def test_not_an_image(auth_client, user, product):
    deliver(user, product)
    fake = SimpleUploadedFile("virus.png", b"not an image", content_type="image/png")

    res = post_review(auth_client, images=[fake])

    assert res.status_code == 400
    assert "images.0" in res.data["fields"]
    assert not Review.objects.exists()


def test_unsupported_image_format(auth_client, user, product):
    deliver(user, product)

    res = post_review(auth_client, images=[image_file("a.gif", "GIF")])

    assert res.status_code == 400
    assert res.data["detail"] == "Загрузите фото в формате JPEG, PNG или WEBP."


def test_photo_too_large(auth_client, user, product, monkeypatch):
    monkeypatch.setattr(catalog_serializers, "REVIEW_IMAGE_MAX_SIZE", 10)
    deliver(user, product)

    res = post_review(auth_client, images=[image_file()])

    assert res.status_code == 400
    assert res.data["detail"] == "Каждое фото — до 5 МБ."


def test_create_requires_auth(api_client, product):
    res = post_review(api_client)

    assert res.status_code == 401
    assert res.data["code"] == "not_authenticated"


def test_create_for_hidden_product_is_404(auth_client, user):
    hidden = make_product(slug="hidden", is_active=False)
    deliver(user, hidden)

    assert post_review(auth_client, slug="hidden").status_code == 404


def test_each_user_can_review_once(product):
    first, second = UserFactory(), UserFactory()
    for user in (first, second):
        deliver(user, product)
        assert post_review(bearer_client(user)).status_code == 201

    product.refresh_from_db()
    assert product.reviews_count == 2

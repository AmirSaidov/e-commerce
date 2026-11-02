import pytest

from apps.catalog.tests.factories import make_product
from apps.users.tests.factories import UserFactory
from apps.wishlist.models import WishlistItem
from conftest import bearer_client

pytestmark = pytest.mark.django_db

URL = "/api/v1/wishlist/"
LIST_FIELDS = {
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
}


def add(client, product_id):
    return client.post(URL, {"product_id": product_id}, format="json")


def ids(client):
    res = client.get(URL)
    assert res.status_code == 200
    return [p["id"] for p in res.json()]


def test_add_and_list_newest_first(auth_client):
    first, second = make_product(), make_product()

    assert add(auth_client, first.id).status_code == 204
    assert add(auth_client, second.id).status_code == 204

    res = auth_client.get(URL)
    assert isinstance(res.json(), list)  # без пагинации
    assert [p["id"] for p in res.json()] == [second.id, first.id]
    assert set(res.json()[0]) == LIST_FIELDS
    assert res.json()[0]["image"].startswith("http://testserver/media/")


def test_add_is_idempotent(auth_client, user):
    product = make_product()

    add(auth_client, product.id)
    assert add(auth_client, product.id).status_code == 204

    assert WishlistItem.objects.filter(user=user).count() == 1


def test_add_unknown_or_inactive_product(auth_client):
    hidden = make_product(is_active=False)

    for product_id in (999999, hidden.id):
        res = add(auth_client, product_id)
        assert res.status_code == 400
        assert res.data["fields"] == {"product_id": ["Товар не найден."]}


def test_add_validation(auth_client):
    res = auth_client.post(URL, {}, format="json")

    assert res.status_code == 400
    assert res.data["fields"]["product_id"] == ["Обязательное поле."]


def test_delete_by_product_id_is_idempotent(auth_client):
    keep, drop = make_product(), make_product()
    add(auth_client, keep.id)
    add(auth_client, drop.id)

    assert auth_client.delete(f"{URL}{drop.id}/").status_code == 204
    assert auth_client.delete(f"{URL}{drop.id}/").status_code == 204
    assert auth_client.delete(f"{URL}999999/").status_code == 204

    assert ids(auth_client) == [keep.id]


def test_users_do_not_see_each_other(auth_client):
    other = bearer_client(UserFactory())
    product = make_product()
    add(other, product.id)

    assert ids(auth_client) == []
    # чужая запись не удаляется
    auth_client.delete(f"{URL}{product.id}/")
    assert ids(other) == [product.id]


def test_deactivated_product_disappears_from_list(auth_client):
    product = make_product()
    add(auth_client, product.id)

    product.is_active = False
    product.save()

    assert ids(auth_client) == []


def test_list_has_no_n_plus_one(auth_client, user, django_assert_max_num_queries):
    for _ in range(15):
        WishlistItem.objects.create(user=user, product=make_product(prices=("1", "2"), images=2))

    # пользователь по JWT + SELECT товаров с аннотациями + prefetch вариантов
    with django_assert_max_num_queries(3):
        assert len(auth_client.get(URL).json()) == 15

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.cart.models import Cart, CartItem
from apps.catalog.tests.factories import make_product
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = pytest.mark.django_db

MERGE = "/api/v1/cart/merge/"
CART = "/api/v1/cart/"


def variant(stock=10, **kwargs):
    return make_product(stocks=(stock,), **kwargs).variants.get()


def lines(user):
    return dict(CartItem.objects.filter(cart__user=user).values_list("variant_id", "quantity"))


def merge(client, items):
    res = client.post(MERGE, {"items": items}, format="json")
    assert res.status_code == 200, res.data
    return res.json()


# ---------- POST /cart/merge/ ----------


def test_merge_into_empty_cart_returns_server_cart(auth_client, user):
    v = variant(slug="iphone", name="iPhone")

    data = merge(auth_client, [{"variant_id": v.id, "quantity": 2}])

    assert data["id"] == Cart.objects.get(user=user).id
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert set(item) == {"id", "variant", "product", "quantity"}
    assert item["quantity"] == 2
    assert item["variant"] == {
        "id": v.id,
        "sku": v.sku,
        "name": v.name,
        "price": "100000.00",
        "old_price": None,
        "stock": 10,
    }
    assert item["product"] == {
        "id": v.product_id,
        "name": "iPhone",
        "slug": "iphone",
        "image": "http://testserver/media/products/iphone-0.svg",
    }


def test_merge_takes_max_quantity(auth_client, user):
    a, b, c = variant(), variant(), variant()
    merge(auth_client, [{"variant_id": a.id, "quantity": 3}, {"variant_id": b.id, "quantity": 1}])

    merge(
        auth_client,
        [
            {"variant_id": a.id, "quantity": 1},
            {"variant_id": b.id, "quantity": 4},
            {"variant_id": c.id, "quantity": 2},
        ],
    )

    assert lines(user) == {a.id: 3, b.id: 4, c.id: 2}


def test_merge_with_empty_guest_cart_returns_server_cart(auth_client, user):
    v = variant()
    merge(auth_client, [{"variant_id": v.id, "quantity": 2}])

    data = merge(auth_client, [])

    assert [(i["variant"]["id"], i["quantity"]) for i in data["items"]] == [(v.id, 2)]


def test_merge_clamps_to_stock_and_drops_unavailable(auth_client, user):
    few = variant(stock=2)
    sold_out = variant(stock=0)
    hidden = variant(is_active=False)

    data = merge(
        auth_client,
        [
            {"variant_id": few.id, "quantity": 5},
            {"variant_id": sold_out.id, "quantity": 1},
            {"variant_id": hidden.id, "quantity": 1},
            {"variant_id": 999999, "quantity": 1},
        ],
    )

    assert [(i["variant"]["id"], i["quantity"]) for i in data["items"]] == [(few.id, 2)]
    assert lines(user) == {few.id: 2}


def test_merge_query_count_does_not_grow(auth_client):
    def queries_for(n):
        items = [{"variant_id": variant().id, "quantity": 1} for _ in range(n)]
        with CaptureQueriesContext(connection) as ctx:
            assert len(merge(auth_client, items)["items"]) >= n
        return len(ctx)

    merge(auth_client, [])  # корзина уже создана — оба замера в одинаковых условиях
    # без N+1: одно и то же число запросов для 1 и 20 позиций
    assert queries_for(1) == queries_for(20)


def test_merge_validation(auth_client):
    res = auth_client.post(MERGE, {"items": [{"variant_id": 1, "quantity": 0}]}, format="json")

    assert res.status_code == 400
    assert list(res.data["fields"]) == ["items.0.quantity"]


# ---------- PUT /cart/ ----------


def test_put_replaces_cart(auth_client, user):
    a, b = variant(), variant()
    merge(auth_client, [{"variant_id": a.id, "quantity": 3}])

    res = auth_client.put(CART, {"items": [{"variant_id": b.id, "quantity": 2}]}, format="json")

    assert res.status_code == 204
    assert lines(user) == {b.id: 2}


def test_put_empty_clears_cart(auth_client, user):
    merge(auth_client, [{"variant_id": variant().id, "quantity": 1}])

    assert auth_client.put(CART, {"items": []}, format="json").status_code == 204
    assert lines(user) == {}


def test_put_skips_stale_variants_and_sums_duplicates(auth_client, user):
    v = variant()
    payload = {
        "items": [
            {"variant_id": v.id, "quantity": 1},
            {"variant_id": 999999, "quantity": 1},
            {"variant_id": v.id, "quantity": 2},
        ]
    }

    assert auth_client.put(CART, payload, format="json").status_code == 204
    assert lines(user) == {v.id: 3}


def test_put_is_per_user(auth_client, user):
    other = UserFactory()
    v = variant()
    bearer_client(other).put(CART, {"items": [{"variant_id": v.id, "quantity": 5}]}, format="json")

    auth_client.put(CART, {"items": [{"variant_id": v.id, "quantity": 1}]}, format="json")

    assert lines(user) == {v.id: 1}
    assert lines(other) == {v.id: 5}


def test_put_validation(auth_client):
    assert auth_client.put(CART, {}, format="json").status_code == 400
    res = auth_client.put(CART, {"items": [{"variant_id": "x", "quantity": 1}]}, format="json")
    assert list(res.data["fields"]) == ["items.0.variant_id"]


@pytest.mark.parametrize(("method", "url"), [("put", CART), ("post", MERGE)])
def test_cart_requires_auth(api_client, method, url):
    assert getattr(api_client, method)(url, {"items": []}, format="json").status_code == 401

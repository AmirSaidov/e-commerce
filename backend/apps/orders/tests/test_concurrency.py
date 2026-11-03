"""Параллельные запросы: блокировки select_for_update и уникальные ограничения под гонкой.

SQLite блокирует всю базу на запись и select_for_update игнорирует, поэтому эти тесты имеют смысл
только на PostgreSQL. Каждый поток работает в своём соединении и своей транзакции
(django_db(transaction=True)), старт синхронизирован барьером.
"""

import threading
from decimal import Decimal

import pytest
from django.db import connection, connections

from apps.cart.models import Cart
from apps.cart.tests.factories import PromoCodeFactory
from apps.catalog.tests.factories import make_product
from apps.orders.models import Order
from apps.users.models import Address
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = [
    pytest.mark.skipif(
        connection.vendor != "postgresql",
        reason="select_for_update и параллельные транзакции — только на PostgreSQL",
    ),
    pytest.mark.django_db(transaction=True),
]

THREADS = 4


def run_parallel(calls):
    barrier = threading.Barrier(len(calls))
    results = [None] * len(calls)

    def worker(index, call):
        try:
            barrier.wait(timeout=10)
            results[index] = call()
        except Exception as exc:  # noqa: BLE001 — результат проверяет тест
            results[index] = exc
        finally:
            connections.close_all()

    threads = [threading.Thread(target=worker, args=(i, c)) for i, c in enumerate(calls)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def order_call(client, variant, quantity=1, **extra):
    payload = {
        "delivery_method": "pickup",
        "payment_method": "cash",
        "items": [{"variant_id": variant.id, "quantity": quantity}],
        **extra,
    }
    return lambda: client.post("/api/v1/orders/", payload, format="json")


def test_last_unit_is_sold_once():
    variant = make_product(stocks=(1,)).variants.get()
    clients = [bearer_client(UserFactory()) for _ in range(THREADS)]

    responses = run_parallel([order_call(client, variant) for client in clients])

    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201] + [400] * (THREADS - 1), responses
    assert {r.data["code"] for r in responses if r.status_code == 400} == {"out_of_stock"}
    variant.refresh_from_db()
    assert variant.stock == 0
    assert Order.objects.count() == 1


def test_stock_is_decremented_exactly():
    variant = make_product(stocks=(10,)).variants.get()
    clients = [bearer_client(UserFactory()) for _ in range(THREADS)]

    responses = run_parallel([order_call(client, variant, quantity=2) for client in clients])

    assert all(r.status_code == 201 for r in responses), responses
    variant.refresh_from_db()
    assert variant.stock == 10 - 2 * THREADS


def test_promo_usage_limit_under_race():
    PromoCodeFactory(code="ONCE", usage_limit=1, value=Decimal("10"))
    variant = make_product(stocks=(100,)).variants.get()
    clients = [bearer_client(UserFactory()) for _ in range(THREADS)]

    responses = run_parallel([order_call(client, variant, promo_code="ONCE") for client in clients])

    assert sorted(r.status_code for r in responses) == [201] + [400] * (THREADS - 1), responses
    assert Order.objects.filter(promo_code="ONCE").count() == 1


def test_cancel_twice_in_parallel_returns_stock_once():
    variant = make_product(stocks=(5,)).variants.get()
    user = UserFactory()
    number = order_call(bearer_client(user), variant, quantity=2)().data["number"]
    url = f"/api/v1/orders/{number}/cancel/"
    clients = [bearer_client(user) for _ in range(THREADS)]

    responses = run_parallel([lambda c=c: c.post(url) for c in clients])

    assert sorted(r.status_code for r in responses) == [200] + [400] * (THREADS - 1), responses
    variant.refresh_from_db()
    assert variant.stock == 5


def test_first_addresses_in_parallel_have_one_default():
    user = UserFactory()
    clients = [bearer_client(user) for _ in range(THREADS)]
    payload = {"city": "Алматы", "street": "Абая", "building": "1"}

    responses = run_parallel(
        [lambda c=c: c.post("/api/v1/users/me/addresses/", payload, format="json") for c in clients]
    )

    assert all(r.status_code == 201 for r in responses), responses
    assert Address.objects.filter(user=user, is_default=True).count() == 1


def test_first_cart_merge_in_parallel():
    user = UserFactory()
    clients = [bearer_client(user) for _ in range(THREADS)]
    variant = make_product(stocks=(10,)).variants.get()
    payload = {"items": [{"variant_id": variant.id, "quantity": 1}]}

    responses = run_parallel(
        [lambda c=c: c.post("/api/v1/cart/merge/", payload, format="json") for c in clients]
    )

    assert all(r.status_code == 200 for r in responses), responses
    assert Cart.objects.filter(user=user).count() == 1

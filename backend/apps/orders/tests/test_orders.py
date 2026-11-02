from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.cart.models import CartItem
from apps.cart.tests.factories import PromoCodeFactory
from apps.catalog.models import Product, ProductVariant
from apps.catalog.tests.factories import make_product
from apps.orders.models import Order
from apps.orders.services import calc_delivery_price
from apps.users.models import Address
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = pytest.mark.django_db

URL = "/api/v1/orders/"
ORDER_FIELDS = {
    "number",
    "status",
    "created_at",
    "items",
    "address",
    "delivery_method",
    "payment_method",
    "subtotal",
    "discount",
    "delivery_price",
    "total",
    "promo_code",
}
ITEM_FIELDS = {
    "id",
    "variant_id",
    "product_name",
    "product_slug",
    "variant_name",
    "image",
    "price",
    "quantity",
}


def variant(price="50000", stock=10, **kwargs):
    return make_product(prices=(price,), stocks=(stock,), **kwargs).variants.get()


@pytest.fixture
def address(user):
    return Address.objects.create(
        user=user,
        city="Алматы",
        street="пр. Абая",
        building="150",
        apartment="12",
        postal_code="050000",
        is_default=True,
    )


def place(client, items, **extra):
    payload = {"delivery_method": "pickup", "payment_method": "cash", **extra}
    payload["items"] = [{"variant_id": v.id, "quantity": q} for v, q in items]
    return client.post(URL, payload, format="json")


# ---------- Создание ----------


def test_create_courier_order(auth_client, user, address):
    iphone = variant(price="599990", name="Apple iPhone 16 Pro", slug="iphone")

    res = place(
        auth_client,
        [(iphone, 1)],
        delivery_method="courier",
        payment_method="card",
        address_id=address.id,
    )

    assert res.status_code == 201, res.data
    data = res.json()
    assert set(data) == ORDER_FIELDS
    assert data["number"].startswith("VT-1")
    assert data["status"] == "created"
    assert data["address"] == {
        "city": "Алматы",
        "street": "пр. Абая",
        "building": "150",
        "apartment": "12",
        "postal_code": "050000",
    }
    assert data["subtotal"] == "599990.00"
    assert data["discount"] == "0.00"
    assert data["delivery_price"] == "0.00"  # бесплатно от 100 000
    assert data["total"] == "599990.00"
    assert data["promo_code"] is None
    item = data["items"][0]
    assert set(item) == ITEM_FIELDS
    assert item["variant_id"] == iphone.id
    assert item["product_name"] == "Apple iPhone 16 Pro"
    assert item["product_slug"] == "iphone"
    assert item["variant_name"] == iphone.name
    assert item["price"] == "599990.00"
    assert item["quantity"] == 1
    assert item["image"] == "http://testserver/media/products/iphone-0.svg"

    iphone.refresh_from_db()
    assert iphone.stock == 9
    order = Order.objects.get(number=data["number"])
    assert order.user == user
    assert order.items.get().sku == iphone.sku


def test_order_numbers_are_sequential(auth_client):
    v = variant()

    numbers = [place(auth_client, [(v, 1)]).data["number"] for _ in range(3)]

    values = [int(n.removeprefix("VT-")) for n in numbers]
    assert values == sorted(values) and len(set(values)) == 3
    assert values[1] - values[0] == 1


def test_prices_come_from_database(auth_client):
    v = variant(price="1000")
    payload = {
        "delivery_method": "pickup",
        "payment_method": "cash",
        "items": [{"variant_id": v.id, "quantity": 2, "price": "1.00"}],
        "subtotal": "1.00",
        "total": "1.00",
        "discount": "999999",
    }

    data = auth_client.post(URL, payload, format="json").json()

    assert (data["subtotal"], data["discount"], data["total"]) == ("2000.00", "0.00", "2000.00")


def test_duplicate_lines_are_summed(auth_client):
    v = variant(stock=5)

    data = place(auth_client, [(v, 2), (v, 1)]).json()

    assert [(i["variant_id"], i["quantity"]) for i in data["items"]] == [(v.id, 3)]
    v.refresh_from_db()
    assert v.stock == 2


# ---------- Остатки ----------


def test_not_enough_stock(auth_client):
    v = variant(stock=2, name="AirPods Pro 2")
    other = variant(stock=5)

    res = place(auth_client, [(other, 1), (v, 3)])

    assert res.status_code == 400
    assert res.data == {
        "detail": "«AirPods Pro 2» осталось только 2 шт.",
        "code": "out_of_stock",
        "fields": {},
    }
    # ничего не списано и заказ не создан
    other.refresh_from_db()
    assert other.stock == 5 and Order.objects.count() == 0


def test_not_enough_stock_names_variant_for_multi_variant_product(auth_client):
    product = make_product(prices=("599990", "799990"), stocks=(12, 2), name="Apple iPhone 16 Pro")
    v512 = product.variants.get(price=Decimal("799990"))
    v512.name = "512 ГБ"
    v512.save()

    res = place(auth_client, [(v512, 3)])

    assert res.data["detail"] == "«Apple iPhone 16 Pro, 512 ГБ» осталось только 2 шт."


def test_sold_out(auth_client):
    v = variant(stock=0, name="PlayStation 5")

    res = place(auth_client, [(v, 1)])

    assert res.data["detail"] == "«PlayStation 5» закончился."


@pytest.mark.parametrize("hidden", [True, False])
def test_variant_not_sellable(auth_client, hidden):
    if hidden:
        v = variant(name="Старый товар", is_active=False)
        items = [(v, 1)]
    else:
        items = [(ProductVariant(id=999999), 1)]

    res = place(auth_client, items)

    assert res.status_code == 400
    assert res.data["code"] == "variant_not_found"


def test_empty_cart(auth_client):
    res = auth_client.post(
        URL, {"items": [], "delivery_method": "pickup", "payment_method": "cash"}, format="json"
    )

    assert res.status_code == 400
    assert res.data == {"detail": "Корзина пуста.", "code": "cart_empty", "fields": {}}


# ---------- Доставка ----------


@pytest.mark.parametrize(
    ("method", "amount", "expected"),
    [
        ("courier", "99999.99", "1500.00"),
        ("courier", "100000", "0.00"),
        ("courier", "0", "1500.00"),
        ("pickup", "1000", "0.00"),
    ],
)
def test_calc_delivery_price(method, amount, expected):
    assert calc_delivery_price(method, Decimal(amount)) == Decimal(expected)


def test_courier_below_threshold_pays_delivery(auth_client, address):
    v = variant(price="30000")

    data = place(auth_client, [(v, 2)], delivery_method="courier", address_id=address.id).json()

    assert (data["subtotal"], data["delivery_price"], data["total"]) == (
        "60000.00",
        "1500.00",
        "61500.00",
    )


def test_free_shipping_threshold_counts_after_discount(auth_client, address):
    # 105 000 − 10% = 94 500 < 100 000 → доставка платная, как на фронте
    PromoCodeFactory(code="WELCOME10", value=Decimal("10"))
    v = variant(price="105000")

    data = place(
        auth_client,
        [(v, 1)],
        delivery_method="courier",
        address_id=address.id,
        promo_code="WELCOME10",
    ).json()

    assert data["discount"] == "10500.00"
    assert data["delivery_price"] == "1500.00"
    assert data["total"] == "96000.00"


def test_settings_drive_delivery(auth_client, address, settings):
    settings.COURIER_PRICE = Decimal("2000")
    settings.FREE_SHIPPING_FROM = Decimal("50000")
    v = variant(price="40000")

    data = place(auth_client, [(v, 1)], delivery_method="courier", address_id=address.id).json()

    assert data["delivery_price"] == "2000.00"


def test_pickup_ignores_address(auth_client, address):
    stranger_address = Address.objects.create(
        user=UserFactory(), city="X", street="Y", building="1", is_default=True
    )
    v = variant()

    for address_id in (None, address.id, stranger_address.id):
        data = place(auth_client, [(v, 1)], address_id=address_id).json()
        assert data["address"] is None and data["delivery_price"] == "0.00"


def test_courier_requires_address(auth_client):
    res = place(auth_client, [(variant(), 1)], delivery_method="courier")

    assert res.status_code == 400
    assert res.data["code"] == "address_required"
    assert res.data["detail"] == "Укажите адрес доставки."


def test_courier_with_foreign_address(auth_client):
    foreign = Address.objects.create(
        user=UserFactory(), city="X", street="Y", building="1", is_default=True
    )

    res = place(auth_client, [(variant(), 1)], delivery_method="courier", address_id=foreign.id)

    assert res.status_code == 400
    assert res.data["code"] == "address_not_found"


def test_address_snapshot_survives_address_changes(auth_client, address):
    number = place(
        auth_client, [(variant(), 1)], delivery_method="courier", address_id=address.id
    ).data["number"]

    address.city = "Астана"
    address.save()
    address.delete()

    assert auth_client.get(f"{URL}{number}/").data["address"]["city"] == "Алматы"


# ---------- Промокоды в заказе ----------


def test_order_with_percent_promo(auth_client):
    PromoCodeFactory(code="WELCOME10", value=Decimal("10"))
    v = variant(price="129990")

    data = place(auth_client, [(v, 1)], promo_code="welcome10").json()

    assert data["promo_code"] == "WELCOME10"
    assert (data["subtotal"], data["discount"], data["total"]) == (
        "129990.00",
        "12999.00",
        "116991.00",
    )


def test_order_with_fixed_promo(auth_client):
    PromoCodeFactory(code="VOLTRA5000", type="fixed", value=Decimal("5000"))

    data = place(auth_client, [(variant(price="3000"), 1)], promo_code="VOLTRA5000").json()

    assert data["discount"] == "3000.00" and data["total"] == "0.00"


@pytest.mark.parametrize(
    ("promo_kwargs", "code"),
    [
        ({"expires_at": timezone.now() - timedelta(days=1)}, "promo_expired"),
        ({"is_active": False}, "promo_inactive"),
        ({"min_subtotal": Decimal("1000000")}, "promo_min_subtotal"),
    ],
)
def test_invalid_promo_rejects_order(auth_client, promo_kwargs, code):
    PromoCodeFactory(code="BAD", **promo_kwargs)
    v = variant()

    res = place(auth_client, [(v, 1)], promo_code="BAD")

    assert res.status_code == 400
    assert res.data["code"] == code
    v.refresh_from_db()
    assert v.stock == 10 and Order.objects.count() == 0


def test_unknown_promo_rejects_order(auth_client):
    res = place(auth_client, [(variant(), 1)], promo_code="NOPE")

    assert res.data["code"] == "promo_not_found"


def test_blank_promo_is_ignored(auth_client):
    data = place(auth_client, [(variant(), 1)], promo_code="  ").json()

    assert data["promo_code"] is None


def test_promo_usage_limit(auth_client):
    PromoCodeFactory(code="ONCE", usage_limit=1)
    v = variant()

    first = place(auth_client, [(v, 1)], promo_code="ONCE")
    assert first.status_code == 201
    assert place(auth_client, [(v, 1)], promo_code="ONCE").data["code"] == "promo_exhausted"

    # отменённый заказ не расходует лимит
    auth_client.post(f"{URL}{first.data['number']}/cancel/")
    assert place(auth_client, [(v, 1)], promo_code="ONCE").status_code == 201


# ---------- Корзина после заказа ----------


def test_server_cart_is_cleared(auth_client, user):
    v = variant()
    auth_client.put(
        "/api/v1/cart/", {"items": [{"variant_id": v.id, "quantity": 2}]}, format="json"
    )

    place(auth_client, [(v, 1)])

    assert not CartItem.objects.filter(cart__user=user).exists()


def test_failed_order_keeps_server_cart(auth_client, user):
    v = variant(stock=1)
    auth_client.put(
        "/api/v1/cart/", {"items": [{"variant_id": v.id, "quantity": 1}]}, format="json"
    )

    assert place(auth_client, [(v, 5)]).status_code == 400

    assert CartItem.objects.filter(cart__user=user).exists()


# ---------- Валидация ----------


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"delivery_method": "drone"}, "delivery_method"),
        ({"payment_method": "crypto"}, "payment_method"),
        ({"items": [{"variant_id": 1, "quantity": 0}]}, "items.0.quantity"),
    ],
)
def test_create_validation(auth_client, payload, field):
    base = {"items": [], "delivery_method": "pickup", "payment_method": "cash"}

    res = auth_client.post(URL, {**base, **payload}, format="json")

    assert res.status_code == 400
    assert field in res.data["fields"]


# ---------- Список и детали ----------


def test_list_newest_first_and_only_own(auth_client):
    v = variant()
    first = place(auth_client, [(v, 1)]).data["number"]
    second = place(auth_client, [(v, 2)]).data["number"]
    place(bearer_client(UserFactory()), [(v, 1)])

    res = auth_client.get(URL, {"page_size": 50})

    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 2 and data["next"] is None
    assert [o["number"] for o in data["results"]] == [second, first]
    assert set(data["results"][0]) == ORDER_FIELDS


def test_list_query_count(auth_client, django_assert_max_num_queries):
    for _ in range(5):
        place(auth_client, [(variant(), 1), (variant(), 2)])

    # пользователь по JWT + COUNT + заказы + prefetch позиций
    with django_assert_max_num_queries(4):
        assert len(auth_client.get(URL).json()["results"]) == 5


def test_detail(auth_client):
    number = place(auth_client, [(variant(), 1)]).data["number"]

    res = auth_client.get(f"{URL}{number}/")

    assert res.status_code == 200
    assert res.data["number"] == number


def test_foreign_or_unknown_order_is_404(auth_client):
    foreign = place(bearer_client(UserFactory()), [(variant(), 1)]).data["number"]

    for number in (foreign, "VT-999999"):
        res = auth_client.get(f"{URL}{number}/")
        assert res.status_code == 404
        assert res.data == {"detail": "Заказ не найден.", "code": "not_found", "fields": {}}


@pytest.mark.parametrize(
    ("method", "url"),
    [("get", URL), ("post", URL), ("get", f"{URL}VT-100001/"), ("post", f"{URL}VT-100001/cancel/")],
)
def test_orders_require_auth(api_client, method, url):
    assert getattr(api_client, method)(url).status_code == 401


# ---------- Отмена ----------


def test_cancel_returns_stock(auth_client):
    a, b = variant(stock=5), variant(stock=5)
    number = place(auth_client, [(a, 2), (b, 1)]).data["number"]

    res = auth_client.post(f"{URL}{number}/cancel/")

    assert res.status_code == 200
    assert set(res.json()) == ORDER_FIELDS
    assert res.data["status"] == "cancelled"
    a.refresh_from_db()
    b.refresh_from_db()
    assert (a.stock, b.stock) == (5, 5)
    assert Order.objects.get(number=number).cancelled_at is not None


def test_cancel_paid_order_rolls_back_popularity(auth_client):
    v = variant(stock=5)
    number = place(auth_client, [(v, 2)]).data["number"]
    Order.objects.filter(number=number).update(status="paid")  # как после вебхука
    Product.objects.filter(pk=v.product_id).update(popularity=10)

    assert auth_client.post(f"{URL}{number}/cancel/").data["status"] == "cancelled"

    assert Product.objects.get(pk=v.product_id).popularity == 8


@pytest.mark.parametrize("status", ["assembling", "shipped", "delivered", "cancelled"])
def test_cancel_not_allowed(auth_client, status):
    v = variant(stock=5)
    number = place(auth_client, [(v, 1)]).data["number"]
    Order.objects.filter(number=number).update(status=status)

    res = auth_client.post(f"{URL}{number}/cancel/")

    assert res.status_code == 400
    assert res.data == {
        "detail": "Этот заказ уже нельзя отменить.",
        "code": "order_not_cancellable",
        "fields": {},
    }
    v.refresh_from_db()
    assert v.stock == 4  # остаток не вернули второй раз


def test_cancel_foreign_order_is_404(auth_client):
    v = variant()
    number = place(bearer_client(UserFactory()), [(v, 1)]).data["number"]

    assert auth_client.post(f"{URL}{number}/cancel/").status_code == 404
    assert Order.objects.get(number=number).status == "created"


# ---------- Без Stripe ----------


def test_card_order_rejected_without_stripe(auth_client, settings):
    settings.STRIPE_SECRET_KEY = ""
    v = variant(stock=5)

    res = place(auth_client, [(v, 1)], payment_method="card")

    assert res.status_code == 400
    assert res.data == {
        "detail": "Оплата картой онлайн сейчас недоступна. Выберите оплату при получении.",
        "code": "payment_method_unavailable",
        "fields": {},
    }
    v.refresh_from_db()
    assert v.stock == 5 and not Order.objects.exists()


def test_cash_order_works_without_stripe(auth_client, settings):
    settings.STRIPE_SECRET_KEY = ""
    settings.STRIPE_WEBHOOK_SECRET = ""

    assert place(auth_client, [(variant(), 1)], payment_method="cash").status_code == 201

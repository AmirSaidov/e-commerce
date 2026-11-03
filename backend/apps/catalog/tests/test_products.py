from decimal import Decimal

import pytest
from django.db import connection

from apps.catalog.models import Product
from apps.catalog.tests.factories import (
    BrandFactory,
    CategoryFactory,
    ProductVariantFactory,
    ReviewFactory,
    make_product,
)

pytestmark = pytest.mark.django_db

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
VARIANT_FIELDS = {"id", "sku", "name", "price", "old_price", "stock"}


def get_list(client, **params):
    res = client.get("/api/v1/products/", params)
    assert res.status_code == 200, res.data
    return res.json()


def slugs(data):
    results = data["results"] if isinstance(data, dict) else data
    return [item["slug"] for item in results]


# ---------- Форма ответа ----------


def test_list_item_shape(api_client):
    product = make_product(
        prices=("599990", "679990"), old_prices=("649990", None), slug="iphone", name="iPhone"
    )

    data = get_list(api_client)

    assert data["count"] == 1 and data["next"] is None and data["previous"] is None
    item = data["results"][0]
    assert set(item) == LIST_FIELDS
    assert item["id"] == product.id
    assert item["category"] == {
        "id": product.category.id,
        "name": product.category.name,
        "slug": product.category.slug,
    }
    assert set(item["brand"]) == {"id", "name", "slug"}
    assert item["price"] == "599990.00"
    assert item["old_price"] == "649990.00"
    assert set(item["default_variant"]) == VARIANT_FIELDS
    assert item["default_variant"]["price"] == "599990.00"
    assert item["variants_count"] == 2
    assert item["in_stock"] is True
    assert item["rating"] == 0.0 and isinstance(item["rating"], float)
    assert item["reviews_count"] == 0
    assert item["image"] == "http://testserver/media/products/iphone-0.svg"
    assert item["created_at"].endswith("+05:00")  # Asia/Almaty


def test_default_variant_is_cheapest_in_stock(api_client):
    make_product(prices=("100", "200", "300"), stocks=(0, 3, 1))

    item = get_list(api_client)["results"][0]

    assert item["default_variant"]["price"] == "200.00"
    assert item["price"] == "200.00"
    assert item["in_stock"] is True
    assert item["variants_count"] == 3


def test_default_variant_when_all_out_of_stock(api_client):
    make_product(prices=("300", "100"), stocks=(0, 0))

    item = get_list(api_client)["results"][0]

    assert item["default_variant"]["price"] == "100.00"
    assert item["in_stock"] is False


def test_product_without_image(api_client):
    make_product(images=0)

    assert get_list(api_client)["results"][0]["image"] is None


def test_inactive_and_variantless_products_are_hidden(api_client):
    make_product(slug="visible")
    make_product(slug="inactive", is_active=False)
    make_product(prices=(), slug="no-variants")

    assert slugs(get_list(api_client)) == ["visible"]


# ---------- Фильтры ----------


def test_category_filter_includes_all_subcategories(api_client):
    audio = CategoryFactory(slug="audio")
    headphones = CategoryFactory(slug="headphones", parent=audio)
    tws = CategoryFactory(slug="tws", parent=headphones)
    make_product(slug="speaker", category=audio)
    make_product(slug="studio", category=headphones)
    make_product(slug="airpods", category=tws)
    make_product(slug="phone")

    assert set(slugs(get_list(api_client, category="audio"))) == {"speaker", "studio", "airpods"}
    assert set(slugs(get_list(api_client, category="headphones"))) == {"studio", "airpods"}
    assert slugs(get_list(api_client, category="unknown")) == []


def test_brand_filter_accepts_comma_separated_list(api_client):
    apple, samsung, sony = (BrandFactory(slug=s) for s in ("apple", "samsung", "sony"))
    make_product(slug="iphone", brand=apple)
    make_product(slug="galaxy", brand=samsung)
    make_product(slug="xperia", brand=sony)

    assert set(slugs(get_list(api_client, brand="apple,samsung"))) == {"iphone", "galaxy"}
    assert slugs(get_list(api_client, brand="sony")) == ["xperia"]


def test_price_filter_uses_default_variant_price(api_client):
    # default = 50 000 (в наличии), хотя самый дешёвый вариант 10 000 закончился
    make_product(slug="a", prices=("10000", "50000"), stocks=(0, 1))
    make_product(slug="b", prices=("30000",))

    assert slugs(get_list(api_client, price_min=20000, price_max=40000)) == ["b"]
    assert set(slugs(get_list(api_client, price_min=40000))) == {"a"}


def test_rating_min_filter(api_client):
    make_product(slug="good", rating=Decimal("4.8"))
    make_product(slug="ok", rating=Decimal("4.4"))

    assert slugs(get_list(api_client, rating_min=4.5)) == ["good"]


def test_in_stock_and_on_sale_filters(api_client):
    make_product(slug="sale", old_prices=("120000",))
    make_product(slug="out", stocks=(0,))
    # old_price только у не-default варианта — это не скидка в карточке
    make_product(slug="other-variant-sale", prices=("100", "200"), old_prices=(None, "250"))

    assert "out" not in slugs(get_list(api_client, in_stock="true"))
    assert slugs(get_list(api_client, on_sale="true")) == ["sale"]
    assert len(get_list(api_client, in_stock="false")["results"]) == 3


def test_search_requires_every_word(api_client):
    watch = CategoryFactory(name="Смарт-часы", slug="watches")
    samsung = BrandFactory(name="Samsung", slug="samsung")
    make_product(slug="gw7", name="Galaxy Watch 7", brand=samsung, category=watch)
    make_product(slug="s25", name="Galaxy S25", brand=samsung)
    make_product(slug="pixel", name="Pixel 9", description="Камера galaxy-уровня")

    assert slugs(get_list(api_client, search="galaxy watch")) == ["gw7"]
    assert set(slugs(get_list(api_client, search="GALAXY"))) == {"gw7", "s25", "pixel"}
    assert slugs(get_list(api_client, search="samsung Смарт-часы")) == ["gw7"]
    assert slugs(get_list(api_client, search="gal wat")) == ["gw7"]  # недописанные слова


@pytest.mark.skipif(connection.vendor != "postgresql", reason="регистр кириллицы — на Postgres")
def test_search_cyrillic_case_insensitive(api_client):
    make_product(slug="buds", name="Наушники Buds")

    assert slugs(get_list(api_client, search="НАУШНИКИ")) == ["buds"]


# ---------- Сортировка и пагинация ----------


@pytest.fixture
def sortable():
    make_product(slug="cheap-old", prices=("1000",), popularity=5, rating=Decimal("4.1"))
    make_product(slug="mid-new", prices=("5000",), popularity=50, rating=Decimal("4.9"))
    make_product(slug="pricey", prices=("9000",), popularity=20, rating=Decimal("4.5"))
    Product.objects.filter(slug="cheap-old").update(created_at="2025-01-01T00:00:00Z")
    Product.objects.filter(slug="pricey").update(created_at="2025-06-01T00:00:00Z")


@pytest.mark.parametrize(
    ("ordering", "expected"),
    [
        (None, ["mid-new", "pricey", "cheap-old"]),
        ("-popularity", ["mid-new", "pricey", "cheap-old"]),
        ("price", ["cheap-old", "mid-new", "pricey"]),
        ("-price", ["pricey", "mid-new", "cheap-old"]),
        ("-created_at", ["mid-new", "pricey", "cheap-old"]),
        ("-rating", ["mid-new", "pricey", "cheap-old"]),
    ],
)
def test_ordering(api_client, sortable, ordering, expected):
    params = {"ordering": ordering} if ordering else {}

    assert slugs(get_list(api_client, **params)) == expected


def test_price_ordering_uses_default_variant(api_client):
    make_product(slug="a", prices=("100", "9000"), stocks=(0, 1))  # default 9000
    make_product(slug="b", prices=("5000",))

    assert slugs(get_list(api_client, ordering="price")) == ["b", "a"]


def test_invalid_ordering_is_400(api_client):
    res = api_client.get("/api/v1/products/", {"ordering": "name"})

    assert res.status_code == 400
    assert set(res.data) == {"detail", "code", "fields"}
    assert "ordering" in res.data["fields"]


def test_invalid_number_filter_is_400(api_client):
    res = api_client.get("/api/v1/products/", {"price_min": "abc"})

    assert res.status_code == 400
    assert "price_min" in res.data["fields"]


def test_pagination(api_client):
    for n in range(25):
        make_product(slug=f"p{n}", images=0)

    first = get_list(api_client)
    assert first["count"] == 25 and len(first["results"]) == 20
    assert first["next"].startswith("http://testserver/api/v1/products/?page=2")
    assert len(get_list(api_client, page=2)["results"]) == 5
    assert len(get_list(api_client, page_size=7)["results"]) == 7
    assert len(get_list(api_client, page_size=500)["results"]) == 25  # потолок 100


def test_page_out_of_range_is_404(api_client):
    make_product()

    res = api_client.get("/api/v1/products/", {"page": 5})

    assert res.status_code == 404
    assert res.data["code"] == "not_found"


def test_list_has_no_n_plus_one(api_client, django_assert_max_num_queries):
    for n in range(30):
        make_product(slug=f"p{n}", prices=("100", "200", "300"), images=3)

    # COUNT + SELECT товаров с аннотациями + prefetch вариантов
    with django_assert_max_num_queries(3):
        res = api_client.get("/api/v1/products/", {"page_size": 30, "category": ""})
    assert len(res.data["results"]) == 30


def test_list_queries_with_category_filter(api_client, django_assert_max_num_queries):
    category = CategoryFactory(slug="phones")
    for n in range(10):
        make_product(slug=f"p{n}", category=category)

    with django_assert_max_num_queries(4):  # +1 запрос на дерево категорий
        api_client.get("/api/v1/products/", {"category": "phones", "ordering": "price"})


# ---------- Карточка, похожие, поиск ----------


def test_detail_shape(api_client):
    product = make_product(prices=("200", "100"), images=3, slug="galaxy-s25")

    res = api_client.get("/api/v1/products/galaxy-s25/")

    assert res.status_code == 200
    data = res.json()
    assert set(data) == LIST_FIELDS | {"description", "specs", "images", "variants"}
    assert data["description"] == product.description
    assert data["specs"] == {"Экран": '6,1"'}
    assert [v["price"] for v in data["variants"]] == ["100.00", "200.00"]
    assert set(data["variants"][0]) == VARIANT_FIELDS
    assert [i["order"] for i in data["images"]] == [1, 2, 3]
    assert set(data["images"][0]) == {"id", "image", "alt", "order"}
    assert data["images"][0]["image"].startswith("http://testserver/media/products/")
    assert data["image"] == data["images"][0]["image"]


def test_detail_queries(api_client, django_assert_max_num_queries):
    make_product(prices=("1", "2", "3"), images=3, slug="x")

    with django_assert_max_num_queries(3):
        api_client.get("/api/v1/products/x/")


@pytest.mark.parametrize("slug", ["missing", "hidden"])
def test_detail_404(api_client, slug):
    make_product(slug="hidden", is_active=False)

    res = api_client.get(f"/api/v1/products/{slug}/")

    assert res.status_code == 404
    assert res.data["code"] == "not_found"


def test_detail_ignores_list_filters(api_client):
    make_product(slug="x", stocks=(0,))

    assert api_client.get("/api/v1/products/x/", {"in_stock": "true"}).status_code == 200


def test_related_same_category_first_then_siblings(api_client):
    audio = CategoryFactory(slug="audio")
    headphones = CategoryFactory(slug="headphones", parent=audio)
    speakers = CategoryFactory(slug="speakers", parent=audio)
    make_product(slug="main", category=headphones)
    for n in range(3):
        make_product(slug=f"hp{n}", category=headphones, popularity=n)
    for n in range(10):
        make_product(slug=f"sp{n}", category=speakers, popularity=n)
    make_product(slug="phone")

    data = api_client.get("/api/v1/products/main/related/").json()

    assert len(data) == 8
    assert slugs(data)[:3] == ["hp2", "hp1", "hp0"]
    assert set(slugs(data)[3:]) <= {f"sp{n}" for n in range(10)}
    assert "main" not in slugs(data) and "phone" not in slugs(data)
    assert set(data[0]) == LIST_FIELDS


def test_related_for_root_category_has_no_siblings(api_client):
    category = CategoryFactory(slug="watches")
    make_product(slug="main", category=category)
    make_product(slug="other", category=category)
    make_product(slug="unrelated")

    assert slugs(api_client.get("/api/v1/products/main/related/").json()) == ["other"]


def test_related_404(api_client):
    assert api_client.get("/api/v1/products/missing/related/").status_code == 404


def test_search_suggestions(api_client):
    for n in range(8):
        make_product(slug=f"galaxy-{n}", name=f"Galaxy {n}", popularity=n)
    make_product(slug="search", name="Pixel")  # slug «search» не мешает маршруту

    data = api_client.get("/api/v1/products/search/", {"q": "galaxy"}).json()

    assert isinstance(data, list)
    assert slugs(data) == [f"galaxy-{n}" for n in (7, 6, 5, 4, 3, 2)]
    assert set(data[0]) == LIST_FIELDS


@pytest.mark.parametrize("q", ["", "   "])
def test_search_empty_query(api_client, q):
    make_product()

    assert api_client.get("/api/v1/products/search/", {"q": q}).json() == []


def test_catalog_ignores_invalid_bearer_token(api_client):
    make_product(slug="x")
    api_client.credentials(HTTP_AUTHORIZATION="Bearer expired-garbage")

    assert api_client.get("/api/v1/products/").status_code == 200
    assert api_client.get("/api/v1/products/x/").status_code == 200
    assert api_client.get("/api/v1/categories/").status_code == 200


# ---------- Рейтинг ----------


def test_rating_recalculated_on_review_save_and_delete():
    product = make_product()
    ReviewFactory(product=product, rating=5)
    review = ReviewFactory(product=product, rating=4)
    ReviewFactory(product=product, rating=4)

    product.refresh_from_db()
    assert product.rating == Decimal("4.3") and product.reviews_count == 3

    review.delete()
    product.refresh_from_db()
    assert product.rating == Decimal("4.5") and product.reviews_count == 2


def test_extra_variant_does_not_change_default_when_pricier(api_client):
    product = make_product(prices=("100",))
    ProductVariantFactory(product=product, price=Decimal("50"), stock=0)

    item = get_list(api_client)["results"][0]

    assert item["price"] == "100.00"
    assert item["variants_count"] == 2

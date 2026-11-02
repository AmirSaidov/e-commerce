import json
import math
from decimal import Decimal

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.cart.models import PromoCode
from apps.catalog.management.commands.seed import DEFAULT_CATALOG
from apps.catalog.models import Category, Product, ProductImage, ProductVariant, Review
from apps.users.models import User

pytestmark = pytest.mark.django_db

MINI_CATALOG = {
    "categories": [
        # дочерняя категория раньше родителя — порядок строк не важен
        {"slug": "headphones", "name": "Наушники", "parent": "audio"},
        {"slug": "audio", "name": "Аудио", "parent": None},
    ],
    "brands": [{"slug": "sony", "name": "Sony"}],
    "products": [
        {
            "slug": "sony-wh-1000xm5",
            "name": "Sony WH-1000XM5",
            "brand": "sony",
            "category": "headphones",
            "price": 189990,
            "old_price": 219990,
            "rating": 4.7,
            "popularity": 60,
            "created": "2026-03-01",
            "description": "Шумоподавление",
            "specs": {"Тип": "накладные", "Вес": 250},
            "variants": [
                {"name": "Чёрный", "delta": 0, "stock": 4},
                {"name": "Серебристый", "delta": 5000, "stock": 0},
            ],
        }
    ],
}


@pytest.fixture
def frontend(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    root = tmp_path / "frontend"
    catalog = root / "src/lib/mock/catalog.json"
    catalog.parent.mkdir(parents=True)
    catalog.write_text(json.dumps(MINI_CATALOG, ensure_ascii=False), encoding="utf-8")
    for folder, names in {
        "categories": ["audio", "headphones"],
        "products": [f"sony-wh-1000xm5-{n}" for n in (1, 2, 3)],
    }.items():
        (root / "public/mock" / folder).mkdir(parents=True)
        for name in names:
            (root / "public/mock" / folder / f"{name}.svg").write_text("<svg/>")
    return catalog


def test_seed_creates_catalog(frontend, settings):
    call_command("seed", catalog=frontend)

    audio = Category.objects.get(slug="audio")
    assert Category.objects.get(slug="headphones").parent == audio
    assert audio.image.name == "categories/audio.svg"

    product = Product.objects.get(slug="sony-wh-1000xm5")
    assert product.specs == {"Тип": "накладные"}  # нестроковые значения отброшены, как в моке
    assert product.popularity == 60
    assert product.created_at.isoformat().startswith("2026-03-01T00:00:00")

    variants = list(product.variants.order_by("sku").values_list("sku", "price", "old_price"))
    assert variants == [
        ("SONY-WH-1000XM5-1", Decimal("189990.00"), Decimal("219990.00")),
        ("SONY-WH-1000XM5-2", Decimal("194990.00"), Decimal("224990.00")),
    ]
    assert [i.image.name for i in product.images.all()] == [
        f"products/sony-wh-1000xm5-{n}.svg" for n in (1, 2, 3)
    ]
    assert (settings.MEDIA_ROOT / "products/sony-wh-1000xm5-1.svg").is_file()

    # отзывы как в моке: max(2, round(60/12)) = 5 штук, round((4.7-4)*5) = 4 пятёрки
    assert product.reviews.count() == 5
    product.refresh_from_db()
    assert product.reviews_count == 5 and product.rating == Decimal("4.8")

    demo = User.objects.get(email="demo@voltra.kz")
    assert demo.is_email_verified and demo.is_active and demo.check_password("demo12345")
    assert (demo.first_name, demo.last_name, demo.phone) == ("Демо", "Покупатель", "")
    assert not User.objects.filter(email__startswith="reviewer", is_active=True).exists()

    promos = {p.code: p for p in PromoCode.objects.all()}
    assert set(promos) == {"WELCOME10", "VOLTRA5000", "SUMMER25"}
    assert (promos["WELCOME10"].type, promos["WELCOME10"].value) == ("percent", Decimal("10"))
    assert (promos["VOLTRA5000"].type, promos["VOLTRA5000"].value) == ("fixed", Decimal("5000"))
    assert promos["SUMMER25"].expires_at < timezone.now()
    assert promos["WELCOME10"].expires_at is None


def test_seed_is_idempotent(frontend):
    call_command("seed", catalog=frontend)
    Product.objects.update(name="изменено")
    call_command("seed", catalog=frontend)

    assert Product.objects.count() == 1
    assert ProductVariant.objects.count() == 2
    assert ProductImage.objects.count() == 3
    assert Review.objects.count() == 5
    assert User.objects.filter(email="demo@voltra.kz").count() == 1
    assert PromoCode.objects.count() == 3
    assert Product.objects.get().name == "Sony WH-1000XM5"


def test_seed_does_not_touch_source_images(frontend):
    source = frontend.parents[3] / "public/mock/products/sony-wh-1000xm5-1.svg"

    call_command("seed", catalog=frontend)

    assert source.read_text() == "<svg/>"


def test_seed_missing_catalog(tmp_path):
    with pytest.raises(CommandError, match="Не найден каталог"):
        call_command("seed", catalog=tmp_path / "nope.json")


@pytest.mark.skipif(not DEFAULT_CATALOG.is_file(), reason="нет клона фронта в ../frontend-readonly")
def test_seed_matches_frontend_mock(api_client, settings, tmp_path):
    """Сверка с моком фронта: те же slug, цены, default_variant и рейтинги, что в демо-режиме."""
    settings.MEDIA_ROOT = tmp_path / "media"
    call_command("seed")
    raw = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))

    assert Category.objects.count() == len(raw["categories"]) == 13
    assert Product.objects.count() == len(raw["products"]) == 36

    for row in raw["products"]:
        data = api_client.get(f"/api/v1/products/{row['slug']}/").json()
        prices = [(row["price"] + v["delta"], v["stock"]) for v in row["variants"]]
        by_price = sorted(prices, key=lambda p: p[0])
        expected_default = next((p for p in by_price if p[1] > 0), by_price[0])

        count = max(2, math.floor(row["popularity"] / 12 + 0.5))
        fives = min(count, math.floor((row["rating"] - 4) * count + 0.5))
        expected_rating = math.floor((5 * fives + 4 * (count - fives)) / count * 10 + 0.5) / 10

        assert data["price"] == f"{expected_default[0]}.00", row["slug"]
        assert data["in_stock"] is any(stock > 0 for _, stock in prices)
        assert data["variants_count"] == len(row["variants"])
        assert data["category"]["slug"] == row["category"]
        assert data["brand"]["slug"] == row["brand"]
        assert data["reviews_count"] == count
        assert data["rating"] == expected_rating, row["slug"]
        assert len(data["images"]) == 3


def test_seed_from_github_without_network(frontend, monkeypatch):
    """--github читает те же файлы, но по URL репозитория фронта; сеть в тесте подменена."""
    from apps.catalog.management.commands import seed as seed_module

    root = frontend.parents[3]
    base = seed_module.FRONTEND_REPO_RAW.format(ref=seed_module.FRONTEND_REF)
    requested = []

    def fake_download(url):
        requested.append(url)
        path = root / url.removeprefix(base + "/")
        return path.read_bytes() if path.is_file() else None

    monkeypatch.setattr(seed_module, "download", fake_download)

    call_command("seed", github=seed_module.FRONTEND_REF)

    assert requested[0] == f"{base}/src/lib/mock/catalog.json"
    assert f"{base}/public/mock/products/sony-wh-1000xm5-1.svg" in requested
    assert Product.objects.get().images.count() == 3
    assert base == (
        "https://raw.githubusercontent.com/AmirSaidov/e-commerce/"
        "6457c049b0722fb8ac88f33899f5e23ea72f65ea/frontend"
    )


def test_seed_from_github_missing_catalog(monkeypatch):
    from apps.catalog.management.commands import seed as seed_module

    monkeypatch.setattr(seed_module, "download", lambda url: None)

    with pytest.raises(CommandError, match="Не найден каталог"):
        call_command("seed", github="main")


def test_seed_if_empty(frontend, monkeypatch):
    call_command("seed", catalog=frontend)
    Product.objects.update(name="изменено вручную")

    # каталог не пуст — ничего не читаем и не трогаем (источник даже не открывается)
    call_command("seed", catalog="does-not-exist.json", if_empty=True)

    assert Product.objects.get().name == "изменено вручную"


def test_seed_if_empty_on_empty_database(frontend):
    call_command("seed", catalog=frontend, if_empty=True)

    assert Product.objects.count() == 1

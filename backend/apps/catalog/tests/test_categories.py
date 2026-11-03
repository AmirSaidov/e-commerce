import pytest

from apps.catalog.tests.factories import BrandFactory, CategoryFactory

pytestmark = pytest.mark.django_db


def test_categories_tree(api_client, django_assert_max_num_queries):
    audio = CategoryFactory(name="Аудио", slug="audio", order=2, image="categories/audio.svg")
    CategoryFactory(name="Колонки", slug="speakers", parent=audio, order=4)
    headphones = CategoryFactory(name="Наушники", slug="headphones", parent=audio, order=3)
    CategoryFactory(name="TWS", slug="tws", parent=headphones, order=5)
    CategoryFactory(name="Смартфоны", slug="smartphones", order=1)

    with django_assert_max_num_queries(1):
        res = api_client.get("/api/v1/categories/")

    assert res.status_code == 200
    tree = res.json()
    assert [c["slug"] for c in tree] == ["smartphones", "audio"]
    audio_node = tree[1]
    assert set(audio_node) == {"id", "name", "slug", "parent", "image", "children"}
    assert audio_node["parent"] is None
    assert audio_node["image"] == "http://testserver/media/categories/audio.svg"
    assert [c["slug"] for c in audio_node["children"]] == ["headphones", "speakers"]
    headphones_node = audio_node["children"][0]
    assert headphones_node["parent"] == audio.id
    assert headphones_node["image"] is None
    assert [c["slug"] for c in headphones_node["children"]] == ["tws"]
    assert headphones_node["children"][0]["children"] == []


def test_brands_without_pagination(api_client):
    BrandFactory(name="Sony", slug="sony")
    BrandFactory(name="Apple", slug="apple", logo="brands/apple.svg")

    res = api_client.get("/api/v1/brands/")

    assert res.status_code == 200
    assert res.json() == [
        {
            "id": res.json()[0]["id"],
            "name": "Apple",
            "slug": "apple",
            "logo": "http://testserver/media/brands/apple.svg",
        },
        {"id": res.json()[1]["id"], "name": "Sony", "slug": "sony", "logo": None},
    ]

import pytest

from apps.users.addresses import MAX_ADDRESSES
from apps.users.models import Address
from apps.users.tests.factories import UserFactory
from conftest import bearer_client

pytestmark = pytest.mark.django_db

URL = "/api/v1/users/me/addresses/"
HOME = {
    "city": "Алматы",
    "street": "пр. Абая",
    "building": "150",
    "apartment": "12",
    "postal_code": "050000",
}
OFFICE = {"city": "Астана", "street": "ул. Кенесары", "building": "40", "apartment": ""}


def create(client, data=None, **extra):
    res = client.post(URL, {**(data or HOME), **extra}, format="json")
    assert res.status_code == 201, res.data
    return res.json()


def defaults(user):
    return list(Address.objects.filter(user=user, is_default=True).values_list("id", flat=True))


def test_first_address_becomes_default(auth_client):
    data = create(auth_client, is_default=False)

    assert data == {"id": data["id"], **HOME, "is_default": True}


def test_list_without_pagination_in_creation_order(auth_client):
    first = create(auth_client)
    second = create(auth_client, OFFICE)

    res = auth_client.get(URL)

    assert res.status_code == 200
    assert [a["id"] for a in res.json()] == [first["id"], second["id"]]
    assert res.json()[1] == {"id": second["id"], **OFFICE, "postal_code": "", "is_default": False}


def test_new_default_resets_others(auth_client, user):
    first = create(auth_client)
    second = create(auth_client, OFFICE, is_default=True)

    assert defaults(user) == [second["id"]]
    assert auth_client.get(f"{URL}{first['id']}/").data["is_default"] is False


def test_patch_fields_and_make_default(auth_client, user):
    first = create(auth_client)
    second = create(auth_client, OFFICE)

    res = auth_client.patch(
        f"{URL}{second['id']}/", {"apartment": "5", "is_default": True}, format="json"
    )

    assert res.status_code == 200
    assert res.data["apartment"] == "5" and res.data["city"] == "Астана"
    assert defaults(user) == [second["id"]]
    assert first["id"] not in defaults(user)


def test_cannot_unset_the_only_default(auth_client, user):
    # как в моке фронта: основной адрес есть всегда, пока есть адреса
    first = create(auth_client)

    res = auth_client.patch(f"{URL}{first['id']}/", {"is_default": False}, format="json")

    assert res.status_code == 200
    assert res.data["is_default"] is True
    assert defaults(user) == [first["id"]]


def test_delete_default_promotes_oldest(auth_client, user):
    first = create(auth_client)
    second = create(auth_client, OFFICE)
    third = create(auth_client, OFFICE, is_default=True)

    assert auth_client.delete(f"{URL}{third['id']}/").status_code == 204

    assert defaults(user) == [first["id"]]
    assert Address.objects.filter(user=user).count() == 2
    assert second["id"] not in defaults(user)


def test_delete_last_address(auth_client, user):
    address = create(auth_client)

    assert auth_client.delete(f"{URL}{address['id']}/").status_code == 204
    assert auth_client.get(URL).json() == []


@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_foreign_address_is_404(auth_client, method):
    stranger = bearer_client(UserFactory())
    foreign = create(stranger)

    res = getattr(auth_client, method)(f"{URL}{foreign['id']}/", {"city": "X"}, format="json")

    assert res.status_code == 404
    assert res.data["code"] == "not_found"
    assert Address.objects.get(pk=foreign["id"]).city == "Алматы"


def test_list_shows_only_own_addresses(auth_client):
    create(bearer_client(UserFactory()))
    mine = create(auth_client)

    assert [a["id"] for a in auth_client.get(URL).json()] == [mine["id"]]


def test_each_user_has_own_default(auth_client, user):
    other = UserFactory()
    create(bearer_client(other))
    create(auth_client)

    assert len(defaults(user)) == 1 and len(defaults(other)) == 1


@pytest.mark.parametrize(
    ("payload", "fields"),
    [
        ({}, {"city", "street", "building"}),
        ({**HOME, "city": "  "}, {"city"}),
        ({**HOME, "postal_code": "05000"}, {"postal_code"}),
        ({**HOME, "postal_code": "abcdef"}, {"postal_code"}),
        ({**HOME, "apartment": "x" * 11}, {"apartment"}),
    ],
)
def test_validation(auth_client, payload, fields):
    res = auth_client.post(URL, payload, format="json")

    assert res.status_code == 400
    assert set(res.data["fields"]) == fields


def test_postal_code_error_text(auth_client):
    res = auth_client.post(URL, {**HOME, "postal_code": "123"}, format="json")

    assert res.data["fields"]["postal_code"] == ["Индекс — 6 цифр"]


def test_address_limit(auth_client, user):
    Address.objects.bulk_create(
        [Address(user=user, **HOME, is_default=i == 0) for i in range(MAX_ADDRESSES)]
    )

    res = auth_client.post(URL, OFFICE, format="json")

    assert res.status_code == 400
    assert res.data["code"] == "address_limit"


def test_put_not_allowed(auth_client):
    address = create(auth_client)

    assert auth_client.put(f"{URL}{address['id']}/", HOME, format="json").status_code == 405

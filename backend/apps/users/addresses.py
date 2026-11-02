"""Адреса пользователя. Правила совпадают с мок-бэкендом фронта (saveAddress / deleteAddress):

- первый адрес автоматически становится основным;
- is_default=true сбрасывает флаг у остальных адресов;
- снять флаг с основного адреса нельзя (основной адрес есть всегда, пока есть адреса);
- при удалении основного основным становится самый старый из оставшихся.
"""

from django.db import transaction

from apps.core.exceptions import ApiException

from .models import Address, User

MAX_ADDRESSES = 20


def _lock_user(user):
    # Блокируем строку пользователя, чтобы параллельные запросы не сделали два основных адреса.
    User.objects.select_for_update().filter(pk=user.pk).exists()


@transaction.atomic
def create_address(user, data):
    _lock_user(user)
    addresses = user.addresses.all()
    count = addresses.count()
    if count >= MAX_ADDRESSES:
        raise ApiException(
            f"Можно сохранить не больше {MAX_ADDRESSES} адресов.", code="address_limit"
        )
    is_default = data.pop("is_default", False) or count == 0
    if is_default:
        addresses.filter(is_default=True).update(is_default=False)
    return Address.objects.create(user=user, is_default=is_default, **data)


@transaction.atomic
def update_address(address, data):
    _lock_user(address.user)
    make_default = data.pop("is_default", False)
    if make_default and not address.is_default:
        address.user.addresses.filter(is_default=True).update(is_default=False)
        address.is_default = True
    for field, value in data.items():
        setattr(address, field, value)
    address.save()
    return address


@transaction.atomic
def delete_address(address):
    user = address.user
    _lock_user(user)
    was_default = address.is_default
    address.delete()
    if was_default:
        oldest = user.addresses.order_by("id").first()
        if oldest is not None:
            oldest.is_default = True
            oldest.save(update_fields=["is_default"])

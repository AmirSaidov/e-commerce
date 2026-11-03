import pytest
from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError

from apps.users.forms import UserCreationForm

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_create_user_by_email_without_username():
    user = User.objects.create_user(
        email="  Aibek@Voltra.KZ ", password="s3cret-pass", first_name="Айбек"
    )

    assert user.email == "aibek@voltra.kz"
    assert user.check_password("s3cret-pass")
    assert not user.is_staff and not user.is_superuser
    assert user.is_email_verified is False
    assert user.phone == ""
    assert not user.avatar
    assert user.username is None


def test_email_is_unique_case_insensitively():
    User.objects.create_user(email="a@voltra.kz", password="x")

    with pytest.raises(IntegrityError):
        User.objects.create_user(email="A@VOLTRA.KZ", password="x")


def test_email_required():
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="x")


def test_create_superuser():
    admin = User.objects.create_superuser(email="admin@voltra.kz", password="x")

    assert admin.is_staff and admin.is_superuser and admin.is_email_verified


def test_authenticate_by_email():
    User.objects.create_user(email="demo@voltra.kz", password="demo12345")

    assert authenticate(email="demo@voltra.kz", password="demo12345") is not None
    assert authenticate(email="demo@voltra.kz", password="wrong") is None


def test_admin_add_form_works_without_username():
    form = UserCreationForm(
        data={"email": "New@Voltra.kz", "password1": "Zx9!long-pass", "password2": "Zx9!long-pass"}
    )

    assert form.is_valid(), form.errors
    assert form.save().email == "new@voltra.kz"

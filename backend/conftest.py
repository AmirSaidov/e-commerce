import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _fast_password_hasher(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def _relaxed_throttling(settings):
    # Тестам авторизации лимиты не нужны; проверка самого лимита задаёт ставку явно.
    settings.AUTH_THROTTLE_RATES = dict.fromkeys(
        settings.AUTH_THROTTLE_RATES, settings.RELAXED_THROTTLE_RATE
    )


@pytest.fixture(autouse=True)
def _stripe_enabled(settings):
    # По умолчанию в тестах онлайн-оплата «включена» (заказы картой создаются). В Stripe тесты
    # не ходят: вызовы подменяются в apps/payments/tests; режим без ключей проверяется отдельно.
    settings.STRIPE_SECRET_KEY = "sk_test_not_used"


@pytest.fixture(autouse=True)
def _clear_cache():
    # Счётчики throttling и паузы между письмами живут в кэше — не тащим их между тестами.
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


def bearer_client(user):
    """Клиент с настоящим access-токеном, как у фронта (а не force_authenticate)."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@pytest.fixture
def auth_client(user):
    return bearer_client(user)

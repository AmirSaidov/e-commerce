from django.conf import settings
from rest_framework.permissions import BasePermission


class TrustedOrigin(BasePermission):
    """Для эндпоинтов, которые работают по cookie (refresh, logout).

    Cookie с SameSite=None браузер отправит с любого сайта, поэтому запрос с чужим заголовком
    Origin отклоняем. Запросы без Origin (curl, серверные компоненты Next) пропускаем:
    у них нет чужих cookie.
    """

    message = "Запрос с этого сайта не разрешён."
    code = "origin_not_allowed"

    def has_permission(self, request, view):
        origin = request.headers.get("Origin")
        if not origin:
            return True
        own_origin = f"{request.scheme}://{request.get_host()}"
        return origin == own_origin or origin in settings.CORS_ALLOWED_ORIGINS

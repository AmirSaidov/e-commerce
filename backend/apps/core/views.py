from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .exceptions import SERVER_ERROR_DETAIL, error_body


@extend_schema(responses=inline_serializer("Health", {"status": serializers.CharField()}))
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})


# Обработчики Django для ошибок вне DRF (несуществующий URL, падение middleware и т.п.).


def bad_request(request, exception=None):
    return _error("Некорректный запрос.", "bad_request", status=400)


def permission_denied(request, exception=None):
    return _error("Доступ запрещён.", "permission_denied", status=403)


def page_not_found(request, exception=None):
    return _error("Страница не найдена.", "not_found", status=404)


def server_error(request):
    return _error(SERVER_ERROR_DETAIL, "server_error", status=500)


def _error(detail, code, status):
    # ensure_ascii=False — кириллица как есть, как в ответах DRF.
    return JsonResponse(
        error_body(detail, code), status=status, json_dumps_params={"ensure_ascii": False}
    )

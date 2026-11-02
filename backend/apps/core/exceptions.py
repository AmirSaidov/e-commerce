"""Единый формат ошибок API: {"detail": "...", "code": "...", "fields": {"поле": ["..."]}}.

`detail` фронт показывает пользователю как есть, `fields` раскладывает по полям форм
(frontend/src/lib/form-errors.ts), поэтому общие ошибки валидации (non_field_errors)
поднимаются в `detail`, а вложенные ошибки получают ключи вида `items.0.quantity`.
"""

import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

VALIDATION_DETAIL = "Проверьте правильность заполнения полей."
SERVER_ERROR_DETAIL = "Внутренняя ошибка сервера. Попробуйте позже."
PARSE_ERROR_DETAIL = "Не удалось разобрать тело запроса."

# Код DRF по умолчанию для ValidationError — ничего не говорит фронту.
GENERIC_VALIDATION_CODES = {"invalid", None}


class ApiException(exceptions.APIException):
    """Ошибка с машинным кодом: raise ApiException("Текст", code="order_not_cancellable")."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Некорректный запрос."
    default_code = "bad_request"

    def __init__(self, detail=None, code=None, status_code=None):
        if status_code is not None:
            self.status_code = status_code
        super().__init__(detail, code)


class DetailedValidationError(exceptions.ValidationError):
    """Ошибки полей плюс свой текст в `detail` — для форм, где фронт показывает только `detail`."""

    def __init__(self, fields, summary):
        super().__init__(fields)
        self.summary = summary


def error_body(detail, code, fields=None):
    return {"detail": str(detail), "code": str(code), "fields": fields or {}}


def api_exception_handler(exc, context):
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        if settings.DEBUG:
            return None  # пусть Django покажет traceback
        logger.error("Необработанная ошибка API", exc_info=exc)
        return Response(
            error_body(SERVER_ERROR_DETAIL, "server_error"),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if isinstance(exc, exceptions.ValidationError):
        response.data = _validation_body(exc.detail, getattr(exc, "summary", None))
    else:
        response.data = _generic_body(exc)
    return response


def _generic_body(exc):
    detail = exc.detail
    code = exc.default_code
    if isinstance(detail, dict):
        # simplejwt кладёт сюда {"detail", "code", "messages"}
        code = detail.get("code", code)
        detail = detail.get("detail") or next(iter(detail.values()), "")
    if isinstance(detail, list):
        detail = detail[0] if detail else exc.default_detail
    code = getattr(detail, "code", None) or code
    if isinstance(exc, exceptions.ParseError):
        # У DRF здесь английский текст парсера: «JSON parse error - ...».
        detail = PARSE_ERROR_DETAIL
    return error_body(detail, code)


def _validation_body(data, summary=None):
    errors = _flatten(data)
    non_field = errors.pop(api_settings.NON_FIELD_ERRORS_KEY, None) or errors.pop("", None)

    detail = non_field[0] if non_field else summary or VALIDATION_DETAIL
    code = getattr(detail, "code", None)
    if code in GENERIC_VALIDATION_CODES:
        code = "validation_error"

    fields = {key: [str(message) for message in messages] for key, messages in errors.items()}
    return error_body(detail, code, fields)


def _flatten(data, prefix=""):
    """{"items": [{}, {"quantity": ["..."]}]} → {"items.1.quantity": ["..."]}."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            result.update(_flatten(value, f"{prefix}.{key}" if prefix else str(key)))
        return result
    if isinstance(data, list):
        if all(not isinstance(item, dict | list) for item in data):
            return {prefix: list(data)} if data else {}
        result = {}
        for index, item in enumerate(data):
            result.update(_flatten(item, f"{prefix}.{index}" if prefix else str(index)))
        return result
    return {prefix: [data]}


def validate_with_summary(serializer):
    """is_valid(), но первая ошибка ещё и в detail — для форм, где фронт показывает только тост."""
    if not serializer.is_valid():
        errors = _flatten(serializer.errors)
        first = next(iter(errors.values()))[0]
        raise DetailedValidationError(serializer.errors, summary=str(first))
    return serializer.validated_data

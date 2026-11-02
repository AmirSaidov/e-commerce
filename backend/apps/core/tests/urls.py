"""Тестовые view, которые бросают разные ошибки, — проверяем формат {detail, code, fields}."""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.urls import include, path
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.core.exceptions import ApiException


class LineSerializer(serializers.Serializer):
    variant_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class FormSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()
    items = LineSerializer(many=True, required=False)

    def validate(self, attrs):
        if attrs["password"] == "mismatch":
            raise ValidationError("Пароли не совпадают.", code="password_mismatch")
        return attrs


@api_view(["POST"])
@permission_classes([AllowAny])
def form_view(request):
    FormSerializer(data=request.data).is_valid(raise_exception=True)
    return Response({})


@api_view(["POST"])
@permission_classes([AllowAny])
def plain_validation_view(request):
    raise ValidationError("Промокод не найден", code="promo_not_found")


@api_view(["POST"])
@permission_classes([AllowAny])
def api_exception_view(request):
    raise ApiException("Заказ нельзя отменить.", code="order_not_cancellable")


@api_view(["POST"])
@permission_classes([AllowAny])
def forbidden_view(request):
    raise ApiException("Подтвердите email.", code="email_not_verified", status_code=403)


@api_view(["GET"])
@permission_classes([AllowAny])
def django_404_view(request):
    raise Http404


@api_view(["GET"])
@permission_classes([AllowAny])
def django_403_view(request):
    raise PermissionDenied


@api_view(["GET"])
@permission_classes([AllowAny])
def crash_view(request):
    raise RuntimeError("boom")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def private_view(request):
    return Response({})


api = [
    path("form/", form_view),
    path("plain/", plain_validation_view),
    path("api-exception/", api_exception_view),
    path("forbidden/", forbidden_view),
    path("django-404/", django_404_view),
    path("django-403/", django_403_view),
    path("crash/", crash_view),
    path("private/", private_view),
]

urlpatterns = [path("api/v1/", include(api))]

handler404 = "apps.core.views.page_not_found"
handler500 = "apps.core.views.server_error"

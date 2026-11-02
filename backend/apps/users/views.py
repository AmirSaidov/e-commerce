from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.exceptions import ApiException, DetailedValidationError, error_body
from apps.core.permissions import TrustedOrigin
from apps.core.throttling import AuthRateThrottle

from . import serializers
from .addresses import create_address, delete_address, update_address
from .cookies import delete_refresh_cookie, get_refresh_cookie, set_refresh_cookie
from .emails import resend_verification_email, send_password_reset_email, send_verification_email
from .models import Address, User
from .tokens import (
    blacklist_all_refresh_tokens,
    email_verification_token,
    password_reset_token,
    user_from_uid,
)

SESSION_EXPIRED = "Сессия истекла. Войдите снова."


class PublicAPIView(APIView):
    """Эндпоинты авторизации не читают заголовок Authorization: просроченный access-токен
    не должен мешать войти, обновить токен или выйти."""

    authentication_classes = []
    permission_classes = [AllowAny]


class ThrottledAPIView(PublicAPIView):
    throttle_classes = [AuthRateThrottle]


class RegisterView(ThrottledAPIView):
    throttle_scope = "register"

    @extend_schema(
        request=serializers.RegisterSerializer, responses={201: serializers.UserSerializer}
    )
    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        send_verification_email(user)
        data = serializers.UserSerializer(user, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)


class LoginView(ThrottledAPIView):
    throttle_scope = "login"

    @extend_schema(
        request=serializers.LoginSerializer, responses={200: serializers.AccessTokenSerializer}
    )
    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request, **serializer.validated_data)
        if user is None:
            raise ApiException(
                "Неверный email или пароль.", code="invalid_credentials", status_code=401
            )
        if settings.EMAIL_VERIFICATION_REQUIRED and not user.is_email_verified:
            # На фронте нет кнопки «отправить ещё раз», поэтому повторяем письмо здесь.
            resend_verification_email(user)
            raise ApiException(
                f"Email не подтверждён. Перейдите по ссылке из письма — мы отправили её "
                f"на {user.email}.",
                code="email_not_verified",
                status_code=403,
            )

        refresh = RefreshToken.for_user(user)
        update_last_login(None, user)
        response = Response({"access": str(refresh.access_token)})
        set_refresh_cookie(response, refresh)
        return response


class RefreshView(PublicAPIView):
    permission_classes = [AllowAny, TrustedOrigin]

    @extend_schema(request=None, responses={200: serializers.AccessTokenSerializer})
    def post(self, request):
        raw = get_refresh_cookie(request)
        if not raw:
            raise ApiException(SESSION_EXPIRED, code="not_authenticated", status_code=401)

        serializer = TokenRefreshSerializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed):
            response = Response(error_body(SESSION_EXPIRED, "token_not_valid"), status=401)
            delete_refresh_cookie(response)
            return response

        # ROTATE_REFRESH_TOKENS: старый refresh уже в blacklist, новый кладём в cookie.
        response = Response({"access": serializer.validated_data["access"]})
        set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


class LogoutView(PublicAPIView):
    permission_classes = [AllowAny, TrustedOrigin]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        raw = get_refresh_cookie(request)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass  # уже недействителен — выходим всё равно
        response = Response(status=status.HTTP_204_NO_CONTENT)
        delete_refresh_cookie(response)
        return response


class VerifyEmailView(PublicAPIView):
    @extend_schema(request=serializers.UidTokenSerializer, responses={204: None})
    def post(self, request):
        serializer = serializers.UidTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = user_from_uid(serializer.validated_data["uid"])
        if user is None or not email_verification_token.check_token(
            user, serializer.validated_data["token"]
        ):
            raise ApiException(
                "Ссылка недействительна или устарела. Войдите — мы отправим новую.",
                code="invalid_token",
            )
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetView(ThrottledAPIView):
    throttle_scope = "password_reset"

    @extend_schema(request=serializers.PasswordResetSerializer, responses={204: None})
    def post(self, request):
        serializer = serializers.PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = User.objects.normalize_email(serializer.validated_data["email"])
        user = User.objects.filter(email=email, is_active=True).first()
        if user is not None:
            send_password_reset_email(user)
        # Ответ одинаковый, есть такой email или нет.
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetConfirmView(PublicAPIView):
    @extend_schema(request=serializers.PasswordResetConfirmSerializer, responses={204: None})
    def post(self, request):
        serializer = serializers.PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = user_from_uid(data["uid"])
        if user is None or not password_reset_token.check_token(user, data["token"]):
            raise ApiException(
                "Ссылка недействительна или устарела. Запросите сброс пароля ещё раз.",
                code="invalid_token",
            )
        try:
            serializers.check_password_strength(data["password"], user)
        except ValidationError as exc:
            messages = [str(message) for message in exc.detail]
            # Страница подтверждения показывает только detail — дублируем туда первую ошибку.
            raise DetailedValidationError({"password": messages}, summary=messages[0]) from exc

        user.set_password(data["password"])
        user.is_email_verified = True  # ссылка пришла на почту — владение email подтверждено
        user.save(update_fields=["password", "is_email_verified"])
        blacklist_all_refresh_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------- Профиль: /users/me/ ----------


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserSerializer
    http_method_names = ["get", "patch", "options"]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    @extend_schema(request=serializers.ChangePasswordSerializer, responses={204: None})
    def post(self, request):
        serializer = serializers.ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])

        # Остальные устройства разлогиниваются, а этот браузер получает свежий refresh:
        # cookie с Path=/api/v1/auth/ можно выставить из ответа на любой URL.
        blacklist_all_refresh_tokens(user)
        response = Response(status=status.HTTP_204_NO_CONTENT)
        set_refresh_cookie(response, RefreshToken.for_user(user))
        return response


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AddressSerializer
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete", "options"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):  # генерация OpenAPI-схемы
            return Address.objects.none()
        # Чужой адрес не виден: на него 404, а не 403.
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.instance = create_address(self.request.user, dict(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.instance = update_address(serializer.instance, dict(serializer.validated_data))

    def perform_destroy(self, instance):
        delete_address(instance)

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import IntegrityError
from rest_framework import serializers

from .models import Address, User

EMAIL_TAKEN = "Пользователь с таким email уже зарегистрирован."
PHONE_RE = r"^\+?[\d\s()-]{10,20}$"


def check_password_strength(password, user):
    """Стандартные AUTH_PASSWORD_VALIDATORS; их русские тексты уходят в fields.password."""
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


class UserSerializer(serializers.ModelSerializer):
    """User для ответов и PATCH /users/me/ (меняются только first_name, last_name, phone)."""

    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "phone", "avatar", "is_email_verified")
        read_only_fields = ("id", "email", "avatar", "is_email_verified")
        extra_kwargs = {
            "first_name": {"allow_blank": False, "max_length": 50},
            "last_name": {"allow_blank": False, "max_length": 50},
            # Как profileSchema во frontend/src/lib/validation.ts; пустая строка — «без телефона».
            "phone": {
                "validators": [
                    RegexValidator(
                        PHONE_RE, "Введите телефон, например +7 700 123 45 67", code="invalid_phone"
                    )
                ]
            },
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, trim_whitespace=False)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError(
                "Текущий пароль указан неверно.", code="wrong_password"
            )
        return value

    def validate_new_password(self, value):
        check_password_strength(value, self.context["request"].user)
        return value


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ("id", "city", "street", "building", "apartment", "postal_code", "is_default")
        extra_kwargs = {
            # Как addressSchema во frontend/src/components/account/address-form.tsx.
            "postal_code": {
                "validators": [RegexValidator(r"^\d{6}$", "Индекс — 6 цифр", code="invalid_postal")]
            },
            "is_default": {"required": False},
        }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(EMAIL_TAKEN, code="email_taken")
        return email

    def validate_password(self, value):
        # Проверка на похожесть пароля на email/имя: пользователь ещё не создан, собираем черновик.
        data = self.initial_data
        draft = User(
            email=str(data.get("email", "")),
            first_name=str(data.get("first_name", "")),
            last_name=str(data.get("last_name", "")),
        )
        check_password_strength(value, draft)
        return value

    def create(self, validated_data):
        try:
            return User.objects.create_user(**validated_data)
        except IntegrityError as exc:  # параллельная регистрация с тем же email
            raise serializers.ValidationError({"email": [EMAIL_TAKEN]}) from exc


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField(max_length=254)
    password = serializers.CharField(max_length=128, trim_whitespace=False)

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class AccessTokenSerializer(serializers.Serializer):
    access = serializers.CharField()


class UidTokenSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=64)
    token = serializers.CharField(max_length=128)


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class PasswordResetConfirmSerializer(UidTokenSerializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False)

"""Письма отправляются синхронно из view (без Celery). Ссылки ведут на фронт."""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .tokens import email_verification_token, encode_uid, password_reset_token

logger = logging.getLogger(__name__)

# Не чаще одного письма подтверждения в 5 минут при попытках входа без подтверждения.
RESEND_VERIFICATION_COOLDOWN = 5 * 60


def send_verification_email(user):
    link = _frontend_link("/verify-email", user, email_verification_token)
    _send(user, "Подтвердите email", "users/emails/verify_email.txt", link)


def resend_verification_email(user):
    if cache.add(f"users:verify-resend:{user.pk}", True, RESEND_VERIFICATION_COOLDOWN):
        send_verification_email(user)


def send_password_reset_email(user):
    link = _frontend_link("/password-reset/confirm", user, password_reset_token)
    _send(user, "Сброс пароля", "users/emails/password_reset.txt", link)


def _frontend_link(path, user, generator):
    query = urlencode({"uid": encode_uid(user), "token": generator.make_token(user)})
    return f"{settings.FRONTEND_URL}{path}?{query}"


def _send(user, subject, template, link):
    body = render_to_string(
        template,
        {
            "user": user,
            "link": link,
            "site_name": settings.SITE_NAME,
            "valid_for": _days(settings.PASSWORD_RESET_TIMEOUT // 86400),
        },
    )
    try:
        send_mail(f"{subject} — {settings.SITE_NAME}", body, None, [user.email])
    except OSError:  # smtplib.SMTPException тоже наследник OSError
        logger.exception("Не удалось отправить письмо «%s» на %s", subject, user.email)


def _days(n):
    if n % 10 == 1 and n % 100 != 11:
        word = "день"
    elif 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        word = "дня"
    else:
        word = "дней"
    return f"{n} {word}"

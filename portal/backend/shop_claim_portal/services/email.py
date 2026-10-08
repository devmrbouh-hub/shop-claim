"""SMTP transactional email."""

from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage

from shop_claim_portal.config import get_settings

logger = logging.getLogger(__name__)


def _public_url() -> str:
    return get_settings().public_url.rstrip("/")


def _send_email(*, to_email: str, subject: str, body: str) -> bool:
    settings = get_settings()
    if not settings.smtp_host:
        logger.warning("SMTP not configured; email to %s skipped: %s", to_email, subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.from_email
    msg["To"] = to_email
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as smtp:
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return True


def send_invite_email(*, to_email: str, invite_code: str) -> bool:
    link = f"{_public_url()}/set-password?code={invite_code}"
    body = (
        f"Вас пригласили в личный кабинет ShopClaim.\n\n"
        f"1. Откройте ссылку (код подставится автоматически): {link}\n"
        f"   Или откройте {_public_url()}/set-password и введите код вручную.\n"
        f"2. Код: {invite_code}\n\n"
        f"Код действует {get_settings().invite_ttl_hours} ч.\n"
    )
    return _send_email(to_email=to_email, subject="ShopClaim — приглашение в личный кабинет", body=body)


def send_email_change_confirm(*, to_email: str, code: str) -> bool:
    link = f"{_public_url()}/confirm-email-change?code={code}"
    body = (
        f"Подтвердите смену email в ShopClaim.\n\n"
        f"Откройте ссылку: {link}\n"
        f"Или введите код на странице подтверждения: {code}\n\n"
        f"Ссылка действует {get_settings().action_token_ttl_hours} ч.\n"
        f"Если вы не запрашивали смену — проигнорируйте письмо.\n"
    )
    return _send_email(to_email=to_email, subject="ShopClaim — подтверждение нового email", body=body)


def send_email_change_requested_notice(*, to_email: str, new_email: str) -> bool:
    body = (
        f"Запрошена смена email в ShopClaim.\n\n"
        f"Новый адрес: {new_email}\n\n"
        f"Если это были не вы — войдите в личный кабинет и отмените смену в настройках аккаунта "
        f"или свяжитесь с поддержкой.\n"
    )
    return _send_email(to_email=to_email, subject="ShopClaim — запрос смены email", body=body)


def send_email_changed_notice(*, to_email: str, new_email: str) -> bool:
    body = (
        f"Email для входа в ShopClaim изменён.\n\n"
        f"Новый адрес: {new_email}\n\n"
        f"Если это были не вы — срочно свяжитесь с поддержкой.\n"
    )
    return _send_email(to_email=to_email, subject="ShopClaim — email изменён", body=body)


def send_password_reset_email(*, to_email: str, code: str) -> bool:
    link = f"{_public_url()}/reset-password?code={code}"
    body = (
        f"Сброс пароля ShopClaim.\n\n"
        f"Откройте ссылку: {link}\n"
        f"Или введите код: {code}\n\n"
        f"Ссылка действует {get_settings().action_token_ttl_hours} ч.\n"
        f"Если вы не запрашивали сброс — проигнорируйте письмо.\n"
    )
    return _send_email(to_email=to_email, subject="ShopClaim — сброс пароля", body=body)

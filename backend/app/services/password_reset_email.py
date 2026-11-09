from html import escape
from typing import TYPE_CHECKING
from urllib.parse import urlencode

import httpx

from app.core.provider_http import post_bounded_json

if TYPE_CHECKING:
    from app.core.config import Settings

_RESEND_EMAILS_URL = "https://api.resend.com/emails"
_REQUEST_TIMEOUT_SECONDS = 10
_MAX_RESPONSE_BYTES = 16 * 1024


class PasswordResetEmailError(RuntimeError):
    pass


def password_reset_email_is_configured(settings: "Settings") -> bool:
    return (
        settings.password_reset_email_provider == "resend"
        and settings.resend_api_key is not None
        and settings.password_reset_from_email is not None
    )


def create_password_reset_url(token: str, settings: "Settings") -> str:
    base_url = settings.password_reset_frontend_url.rstrip("/")
    query = urlencode({"token": token})
    return f"{base_url}/forgot-password#{query}"


def send_password_reset_email(
    recipient: str,
    reset_url: str,
    *,
    settings: "Settings",
) -> None:
    if not password_reset_email_is_configured(settings):
        raise PasswordResetEmailError("Password reset email is not configured.")

    api_key = settings.resend_api_key
    sender = settings.password_reset_from_email
    if api_key is None or sender is None:
        raise PasswordResetEmailError("Password reset email is not configured.")

    safe_url = escape(reset_url, quote=True)
    payload = {
        "from": str(sender),
        "to": [recipient],
        "subject": "Reset your LegalCheck password",
        "text": (
            "Use the following one-time link to reset your LegalCheck password. "
            f"The link expires in {settings.password_reset_token_expire_minutes} minutes:\n"
            f"{reset_url}\n\nIf you did not request this, you can ignore this email."
        ),
        "html": (
            "<p>Use this one-time link to reset your LegalCheck password. "
            f"The link expires in {settings.password_reset_token_expire_minutes} minutes.</p>"
            f'<p><a href="{safe_url}">Reset password</a></p>'
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
    }

    try:
        response = post_bounded_json(
            _RESEND_EMAILS_URL,
            payload=payload,
            headers={
                "Authorization": f"Bearer {api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            timeout=_REQUEST_TIMEOUT_SECONDS,
            max_response_bytes=_MAX_RESPONSE_BYTES,
        )
    except (httpx.HTTPError, ValueError) as exc:
        raise PasswordResetEmailError(
            "The password reset email provider could not deliver the message."
        ) from exc

    if not isinstance(response.get("id"), str) or not response["id"]:
        raise PasswordResetEmailError(
            "The password reset email provider returned an invalid response."
        )

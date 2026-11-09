import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services import password_reset_email
from app.services.password_reset_email import (
    PasswordResetEmailError,
    create_password_reset_url,
    send_password_reset_email,
)


def configured_settings() -> Settings:
    return Settings(
        password_reset_email_provider="resend",
        resend_api_key=SecretStr("test-api-key"),
        password_reset_from_email="no-reply@example.com",
        password_reset_frontend_url="https://legalcheck.example",
    )


def test_resend_request_is_bounded_and_contains_only_server_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_post(
        url: str,
        *,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout: float,
        max_response_bytes: int,
    ) -> dict[str, object]:
        captured.update(
            url=url,
            payload=payload,
            headers=headers,
            timeout=timeout,
            max_response_bytes=max_response_bytes,
        )
        return {"id": "email-id"}

    monkeypatch.setattr(password_reset_email, "post_bounded_json", fake_post)
    settings = configured_settings()
    reset_url = create_password_reset_url("one-time-token", settings)

    send_password_reset_email(
        "user@example.com",
        reset_url,
        settings=settings,
    )

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["timeout"] == 10
    assert captured["max_response_bytes"] == 16 * 1024
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer test-api-key"
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["to"] == ["user@example.com"]
    assert payload["from"] == "no-reply@example.com"
    assert reset_url.endswith("#token=one-time-token")


@pytest.mark.parametrize(
    "response",
    [{}, {"id": ""}, {"id": 123}],
)
def test_resend_rejects_invalid_provider_responses(
    monkeypatch: pytest.MonkeyPatch,
    response: dict[str, object],
) -> None:
    monkeypatch.setattr(
        password_reset_email,
        "post_bounded_json",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(PasswordResetEmailError):
        send_password_reset_email(
            "user@example.com",
            "https://legalcheck.example/forgot-password#token=x",
            settings=configured_settings(),
        )


def test_resend_timeout_is_reported_without_exposing_provider_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def timeout(*args: object, **kwargs: object) -> dict[str, object]:
        raise httpx.TimeoutException("provider-secret-detail")

    monkeypatch.setattr(password_reset_email, "post_bounded_json", timeout)

    with pytest.raises(PasswordResetEmailError) as error:
        send_password_reset_email(
            "user@example.com",
            "https://legalcheck.example/forgot-password#token=x",
            settings=configured_settings(),
        )

    assert "provider-secret-detail" not in str(error.value)


def test_resend_requires_explicit_configuration() -> None:
    with pytest.raises(PasswordResetEmailError):
        send_password_reset_email(
            "user@example.com",
            "https://legalcheck.example/forgot-password#token=x",
            settings=Settings(),
        )

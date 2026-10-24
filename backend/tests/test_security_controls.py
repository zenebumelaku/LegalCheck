import asyncio
import json
import logging
from typing import Optional

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.config import Settings
from app.core.logging import JsonFormatter, correlation_id_context
from app.core.rate_limit import RedisRateLimiter, get_rate_limiter
from app.core.request_context import RequestContextMiddleware
from app.main import app, unhandled_exception_handler


def _request(
    *,
    headers: Optional[list[tuple[bytes, bytes]]] = None,
    client: tuple[str, int] = ("192.0.2.11", 1234),
) -> Request:
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/api/v1/health",
            "raw_path": b"/api/v1/health",
            "query_string": b"",
            "headers": headers or [],
            "client": client,
            "server": ("testserver", 80),
            "state": {"correlation_id": "test-request-id"},
        }
    )


class FakeRedis:
    def __init__(self, result: list[int]) -> None:
        self.result = result
        self.call = None

    def eval(self, *args):
        self.call = args
        return self.result


class FailingRedis:
    def eval(self, *args):
        from redis.exceptions import ConnectionError

        raise ConnectionError("sensitive connection detail")


def test_rate_limiter_uses_direct_peer_address_and_returns_retry_after() -> None:
    limiter = RedisRateLimiter(Settings())
    fake_redis = FakeRedis([0, 37])
    limiter._redis = fake_redis
    request = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.99")],
    )

    with pytest.raises(HTTPException) as raised:
        limiter.check(request, "login", 10)

    assert raised.value.status_code == 429
    assert raised.value.headers["Retry-After"] == "37"
    assert "192.0.2.11" in fake_redis.call[2]
    assert "203.0.113.99" not in fake_redis.call[2]


def test_rate_limiter_fails_closed_without_leaking_redis_details() -> None:
    limiter = RedisRateLimiter(Settings())
    limiter._redis = FailingRedis()

    with pytest.raises(HTTPException) as raised:
        limiter.check(_request(), "audit-create", 5)

    assert raised.value.status_code == 503
    assert "sensitive connection detail" not in str(raised.value.detail)


def test_sensitive_auth_routes_apply_rate_limiting() -> None:
    buckets: list[str] = []

    class RejectingRateLimiter:
        def check(self, request: Request, bucket: str, limit: int) -> None:
            buckets.append(bucket)
            raise HTTPException(status_code=429, detail="rate limited")

    app.dependency_overrides[get_rate_limiter] = lambda: RejectingRateLimiter()
    try:
        with TestClient(app) as client:
            registration = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Rate Limited",
                    "email": "limited@example.com",
                    "password": "a-long-password",
                },
            )
            reset = client.post(
                "/api/v1/auth/password-reset-request",
                json={"email": "limited@example.com"},
            )
    finally:
        app.dependency_overrides.pop(get_rate_limiter, None)

    assert registration.status_code == 429
    assert reset.status_code == 429
    assert buckets == ["registration", "password-reset"]


def test_wildcard_cors_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="Wildcard CORS"):
        Settings(cors_origins=["*"])


def test_unhandled_api_errors_hide_internal_details() -> None:
    secret = "private-token-and-database-stack"
    response = asyncio.run(
        unhandled_exception_handler(
            _request(),
            RuntimeError(secret),
        )
    )
    body = json.loads(response.body)

    assert response.status_code == 500
    assert secret not in response.body.decode()
    assert body["error"]["message"] == "An unexpected error occurred."


def test_request_context_sets_and_returns_safe_correlation_id() -> None:
    observed: dict[str, str] = {}

    async def endpoint(scope, receive, send) -> None:
        observed["correlation_id"] = scope["state"]["correlation_id"]
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    app = RequestContextMiddleware(endpoint)
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(
        app(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [(b"x-request-id", b"client-request_42")],
                "state": {},
            },
            receive,
            send,
        )
    )

    assert observed["correlation_id"] == "client-request_42"
    response_headers = dict(messages[0]["headers"])
    assert response_headers[b"x-request-id"] == b"client-request_42"


def test_invalid_request_id_is_replaced() -> None:
    observed: dict[str, str] = {}

    async def endpoint(scope, receive, send) -> None:
        observed["correlation_id"] = scope["state"]["correlation_id"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        return None

    asyncio.run(
        RequestContextMiddleware(endpoint)(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": [(b"x-request-id", b"contains\nunsafe")],
                "state": {},
            },
            receive,
            send,
        )
    )

    assert observed["correlation_id"] != "contains\nunsafe"
    assert len(observed["correlation_id"]) == 36


def test_structured_logs_include_correlation_id_without_exception_trace() -> None:
    token = correlation_id_context.set("safe-request-id")
    try:
        record = logging.LogRecord(
            "legalcheck.test",
            logging.ERROR,
            __file__,
            1,
            "processing failed",
            (),
            None,
        )
        record.exc_info = (
            RuntimeError,
            RuntimeError("private traceback data"),
            None,
        )
        payload = json.loads(JsonFormatter().format(record))
    finally:
        correlation_id_context.reset(token)

    assert payload["correlation_id"] == "safe-request-id"
    assert "exception" not in payload
    assert "private traceback data" not in json.dumps(payload)

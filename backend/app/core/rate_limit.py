import time
from functools import lru_cache
from typing import Protocol
from uuid import uuid4

from fastapi import Depends, HTTPException, Request, status
from redis import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings

_WINDOW_SECONDS = 60
_RATE_LIMIT_SCRIPT = """
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, now - window)
redis.call('ZADD', KEYS[1], now, ARGV[4])
local count = redis.call('ZCARD', KEYS[1])
redis.call('EXPIRE', KEYS[1], window)
if count > limit then
  redis.call('ZREM', KEYS[1], ARGV[4])
  return {0, redis.call('TTL', KEYS[1])}
end
return {1, redis.call('TTL', KEYS[1])}
"""


class RateLimiter(Protocol):
    def check(self, request: Request, bucket: str, limit: int) -> None: ...


class RedisRateLimiter:
    def __init__(self, settings: Settings) -> None:
        self._redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def check(self, request: Request, bucket: str, limit: int) -> None:
        # Deliberately use the direct peer address; forwarded headers are trusted
        # only when a separately configured proxy boundary validates them.
        client_host = request.client.host if request.client else "unknown"
        key = f"legalcheck:rate-limit:{bucket}:{client_host}"
        try:
            allowed, retry_after = self._redis.eval(
                _RATE_LIMIT_SCRIPT,
                1,
                key,
                int(time.time()),
                _WINDOW_SECONDS,
                limit,
                str(uuid4()),
            )
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The request protection service is unavailable.",
            ) from exc
        if int(allowed) != 1:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Try again shortly.",
                headers={"Retry-After": str(max(1, int(retry_after)))},
            )


@lru_cache
def get_rate_limiter() -> RateLimiter:
    return RedisRateLimiter(get_settings())


def enforce_login_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    limiter.check(
        request,
        "login",
        get_settings().rate_limit_login_per_minute,
    )


def enforce_registration_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    limiter.check(
        request,
        "registration",
        get_settings().rate_limit_auth_per_minute,
    )


def enforce_password_reset_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    limiter.check(
        request,
        "password-reset",
        get_settings().rate_limit_auth_per_minute,
    )


def enforce_upload_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    limiter.check(
        request,
        "upload",
        get_settings().rate_limit_upload_per_minute,
    )


def enforce_audit_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    limiter.check(
        request,
        "audit-create",
        get_settings().rate_limit_audit_per_minute,
    )

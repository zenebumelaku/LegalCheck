import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.api.dependencies import require_roles
from app.db.models import User
from app.db.session import DatabaseConfigurationError, check_database_connection
from app.services.legal_question_cache import (
    get_legal_question_cache,
    legal_question_cache_metrics,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    try:
        check_database_connection()
    except (DatabaseConfigurationError, SQLAlchemyError) as exc:
        logger.warning(
            "Database readiness check failed",
            extra={"error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=503,
            detail="The service is not ready.",
        ) from exc

    return {"status": "ready"}


@router.get("/health/answer-cache", response_model=None)
def answer_cache_health(
    _admin: User = Depends(require_roles("admin")),
) -> JSONResponse:
    try:
        reachable = get_legal_question_cache().ping()
    except (RedisError, ValueError) as exc:
        legal_question_cache_metrics.record("errors")
        logger.warning(
            "Redis answer-cache health check failed",
            extra={"error_type": type(exc).__name__},
        )
        reachable = False

    if not reachable:
        return JSONResponse(
            status_code=503,
            content={
                "component": "redis_answer_cache",
                "redis_status": "unavailable",
                "ai_system_status": "not_assessed",
            },
        )
    return JSONResponse(
        content={
            "component": "redis_answer_cache",
            "redis_status": "reachable",
            "ai_system_status": "not_assessed",
        },
    )


@router.get("/admin/legal-question-cache/metrics")
def answer_cache_metrics(
    _admin: User = Depends(require_roles("admin")),
) -> dict[str, int | str]:
    return legal_question_cache_metrics.snapshot()

import logging

from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DatabaseConfigurationError, check_database_connection

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

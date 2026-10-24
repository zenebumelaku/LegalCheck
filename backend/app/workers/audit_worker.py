import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Audit
from app.db.session import get_session_factory
from app.services.compliance_analysis import (
    ComplianceAnalysisError,
    analyze_audit,
)
from app.services.llm_provider import LLMProvider
from app.services.audit_queue import AUDIT_QUEUE_NAME
from app.storage.interface import PrivateFileStorage, get_private_storage

logger = logging.getLogger(__name__)


def _claim_queued_audit(db: Session, audit_id: UUID) -> UUID | None:
    attempt_id = uuid4()
    result = db.execute(
        update(Audit)
        .where(Audit.id == audit_id, Audit.audit_status == "queued")
        .values(
            audit_status="extracting",
            processing_attempt_id=attempt_id,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            failure_code=None,
            failure_message=None,
        )
    )
    db.commit()
    return attempt_id if result.rowcount == 1 else None


def run_audit_job(
    audit_id: UUID,
    *,
    db: Session,
    storage: PrivateFileStorage,
    llm_provider: LLMProvider | None = None,
) -> bool:
    attempt_id = _claim_queued_audit(db, audit_id)
    if attempt_id is None:
        return False
    try:
        analyze_audit(
            audit_id,
            db=db,
            storage=storage,
            llm_provider=llm_provider,
            initial_status="extracting",
            attempt_id=attempt_id,
        )
    except ComplianceAnalysisError:
        return True
    except Exception as exc:
        db.rollback()
        try:
            db.execute(
                update(Audit)
                .where(
                    Audit.id == audit_id,
                    Audit.processing_attempt_id == attempt_id,
                    Audit.audit_status.in_(
                        {
                            "extracting",
                            "retrieving_sources",
                            "analyzing",
                            "generating_report",
                        }
                    ),
                )
                .values(
                    audit_status="failed",
                    processing_attempt_id=None,
                    completed_at=None,
                    failure_code="worker_failure",
                    failure_message=(
                        "The analysis worker failed. No completed legal review was produced."
                    ),
                )
            )
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.error(
                "Could not persist worker failure for audit %s",
                audit_id,
            )
        logger.error(
            "Audit worker failed for audit %s with error type %s",
            audit_id,
            type(exc).__name__,
        )
    return True


def process_audit_job(audit_id: str) -> None:
    parsed_id = UUID(audit_id)
    session_factory = get_session_factory()
    settings = get_settings()
    storage = get_private_storage(str(settings.private_storage_path))
    with session_factory() as db:
        run_audit_job(parsed_id, db=db, storage=storage)


def main() -> None:
    from redis import Redis
    from rq import Queue, Worker

    settings = get_settings()
    connection = Redis.from_url(settings.redis_url)
    queue = Queue(AUDIT_QUEUE_NAME, connection=connection)
    Worker([queue], connection=connection).work()


if __name__ == "__main__":
    main()

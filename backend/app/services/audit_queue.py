from uuid import UUID

from app.core.config import get_settings

AUDIT_QUEUE_NAME = "legalcheck-audits"


def enqueue_audit(audit_id: UUID) -> None:
    from redis import Redis
    from rq import Queue

    settings = get_settings()
    connection = Redis.from_url(
        settings.redis_url,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    queue = Queue(AUDIT_QUEUE_NAME, connection=connection)
    queue.enqueue(
        "app.workers.audit_worker.process_audit_job",
        str(audit_id),
        job_timeout=settings.audit_job_timeout_seconds,
        result_ttl=86400,
        failure_ttl=604800,
    )

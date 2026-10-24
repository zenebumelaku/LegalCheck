import logging
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_organization_membership
from app.core.config import settings
from app.core.rate_limit import enforce_audit_rate_limit
from app.db.models import (
    Audit,
    Document,
    Finding,
    LegalProvision,
    LegalSource,
    OrganizationMembership,
    User,
)
from app.db.session import get_db
from app.schemas.audits import (
    AuditCreateRequest,
    AuditFindingCitation,
    AuditFindingResponse,
    AuditFindingsResponse,
    AuditListResponse,
    AuditResponse,
    AuditReviewOptions,
    AuditStatusResponse,
)
from app.schemas.compliance_analysis import AnalysisLimitations
from app.services.audit_queue import enqueue_audit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audits", tags=["audits"])

_READABLE_ORGANIZATION_ROLES = {"member", "admin", "owner"}
_PROCESSING_STATES = {
    "extracting",
    "retrieving_sources",
    "analyzing",
    "generating_report",
}


def get_audit_enqueue() -> Callable[[UUID], None]:
    return enqueue_audit


def _audit_response(audit: Audit) -> AuditResponse:
    return AuditResponse(
        id=audit.id,
        document_id=audit.document_id,
        audit_status=audit.audit_status,
        review_options=AuditReviewOptions.model_validate(audit.review_options or {}),
        processing_warnings=list(audit.processing_warnings or []),
        analysis_version=audit.analysis_version,
        model_identifier=audit.model_identifier,
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        failure_code=audit.failure_code,
        failure_message=audit.failure_message,
        created_at=audit.created_at,
    )


def _get_accessible_audit(db: Session, user: User, audit_id: UUID) -> Audit:
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found.")
    document = db.get(Document, audit.document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Audit not found.")
    if document.organization_id is not None:
        get_organization_membership(
            db,
            user,
            document.organization_id,
            allowed_roles=_READABLE_ORGANIZATION_ROLES,
        )
    elif document.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Audit not found.")
    return audit


def _mark_queue_failure(db: Session, audit_id: UUID) -> None:
    audit = db.get(Audit, audit_id)
    if audit is None or audit.audit_status != "queued":
        return
    audit.audit_status = "failed"
    audit.failure_code = "queue_unavailable"
    audit.failure_message = (
        "The audit could not be queued. Retry when the processing service is available."
    )
    db.commit()


@router.post(
    "",
    response_model=AuditResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_audit_rate_limit)],
)
def create_audit(
    payload: AuditCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    enqueue: Callable[[UUID], None] = Depends(get_audit_enqueue),
) -> AuditResponse:
    document = db.scalar(
        select(Document).where(
            Document.id == payload.document_id,
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    if (
        document.document_type not in {"pdf", "docx"}
        or document.processing_status not in {"completed", "warning"}
    ):
        raise HTTPException(
            status_code=422,
            detail="Only successfully extracted PDF and DOCX documents can be audited.",
        )
    if document.organization_id is not None:
        get_organization_membership(
            db,
            user,
            document.organization_id,
            allowed_roles=_READABLE_ORGANIZATION_ROLES,
        )
    elif document.owner_user_id != user.id:
        raise HTTPException(status_code=404, detail="Document not found.")

    audit = Audit(
        document_id=document.id,
        requested_by=user.id,
        audit_status="queued",
        review_options=payload.review_options.model_dump(
            mode="json",
            exclude_none=True,
        ),
        processing_warnings=[],
        analysis_version="1",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    try:
        enqueue(audit.id)
    except Exception as exc:
        logger.warning("Audit queue unavailable for audit %s", audit.id)
        _mark_queue_failure(db, audit.id)
        raise HTTPException(
            status_code=503,
            detail="The audit could not be queued. Retry when the processing service is available.",
        ) from exc
    return _audit_response(audit)


@router.get("", response_model=AuditListResponse)
def list_audits(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=1_000_000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditListResponse:
    readable_organizations = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.membership_role.in_(_READABLE_ORGANIZATION_ROLES),
    )
    query = (
        select(Audit)
        .join(Document, Document.id == Audit.document_id)
        .where(
            (
                Document.organization_id.in_(readable_organizations)
                | (
                    Document.organization_id.is_(None)
                    & (Document.owner_user_id == user.id)
                )
            )
        )
        .order_by(Audit.created_at.desc(), Audit.id)
        .offset(offset)
        .limit(limit)
    )
    audits = db.scalars(query).all()
    return AuditListResponse(
        items=[_audit_response(audit) for audit in audits],
        limit=limit,
        offset=offset,
    )


@router.get("/{audit_id}", response_model=AuditResponse)
def get_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditResponse:
    return _audit_response(_get_accessible_audit(db, user, audit_id))


@router.get("/{audit_id}/status", response_model=AuditStatusResponse)
def get_audit_status(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditStatusResponse:
    audit = _get_accessible_audit(db, user, audit_id)
    return AuditStatusResponse(
        audit_id=audit.id,
        status=audit.audit_status,
        processing_warnings=list(audit.processing_warnings or []),
        started_at=audit.started_at,
        completed_at=audit.completed_at,
        failure_code=audit.failure_code,
        failure_message=audit.failure_message,
    )


@router.get("/{audit_id}/findings", response_model=AuditFindingsResponse)
def get_audit_findings(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AuditFindingsResponse:
    audit = _get_accessible_audit(db, user, audit_id)
    if audit.audit_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Findings are available only after the audit completes.",
        )
    findings = db.scalars(
        select(Finding)
        .where(Finding.audit_id == audit.id)
        .order_by(Finding.created_at, Finding.id)
    ).all()
    output: list[AuditFindingResponse] = []
    for finding in findings:
        categories = finding.finding_type.split(":")
        category = categories[0]
        clause_id = categories[2] if len(categories) > 2 else (
            categories[1] if len(categories) > 1 else "unknown"
        )
        citations = []
        for citation in finding.citations:
            provision = db.get(LegalProvision, citation.legal_provision_id)
            source = (
                db.get(LegalSource, provision.legal_source_id)
                if provision is not None
                else None
            )
            if provision is None or source is None:
                continue
            citations.append(
                AuditFindingCitation(
                    source_id=source.id,
                    source_title=source.title,
                    source_url=source.original_source_url,
                    version_label=source.version_label,
                    article_number=provision.article_number,
                    sub_article_reference=provision.sub_article_reference,
                    supporting_quote=citation.supporting_quote,
                    relevance_information=citation.relevance_information,
                )
            )
        output.append(
            AuditFindingResponse(
                id=finding.id,
                category=category,
                severity=finding.severity,
                clause_id=clause_id,
                clause_text=finding.clause_text,
                explanation=finding.explanation,
                recommended_action=finding.recommended_action,
                evidence_assessment=(
                    "supporting"
                    if finding.evidence_status == "supported"
                    else "insufficient"
                ),
                citations=citations,
                model_confidence=None,
                created_at=finding.created_at,
            )
        )
    limitations = [
        "This AI-assisted review is not legal advice and does not determine legal compliance.",
        "Review findings and their source applicability with a qualified Ethiopian legal professional.",
        *list(audit.processing_warnings or []),
    ]
    if audit.audit_status != "completed":
        limitations.append("Findings are not a completed audit result.")
    return AuditFindingsResponse(
        audit_id=audit.id,
        findings=output,
        limitations=AnalysisLimitations(items=limitations),
    )


@router.post(
    "/{audit_id}/retry",
    response_model=AuditResponse,
    status_code=202,
    dependencies=[Depends(enforce_audit_rate_limit)],
)
def retry_audit(
    audit_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    enqueue: Callable[[UUID], None] = Depends(get_audit_enqueue),
) -> AuditResponse:
    audit = _get_accessible_audit(db, user, audit_id)
    now = datetime.now(timezone.utc)
    is_stale = (
        audit.audit_status in _PROCESSING_STATES
        and audit.started_at is not None
        and (
            audit.started_at.replace(tzinfo=timezone.utc)
            if audit.started_at.tzinfo is None
            else audit.started_at
        )
        < now - timedelta(seconds=settings.audit_stale_after_seconds)
    )
    if audit.audit_status != "failed" and not is_stale:
        raise HTTPException(
            status_code=409,
            detail="Only failed or stale audits can be retried.",
        )
    existing_finding = db.scalar(
        select(Finding.id).where(Finding.audit_id == audit.id).limit(1)
    )
    if existing_finding is not None:
        raise HTTPException(
            status_code=409,
            detail="This audit has persisted findings and cannot be retried safely.",
        )
    expected_status = audit.audit_status
    warning = (
        "A stale worker attempt was recovered before retry."
        if is_stale
        else "A failed audit was explicitly retried."
    )
    retry_query = update(Audit).where(
        Audit.id == audit.id,
        Audit.audit_status == expected_status,
    )
    if is_stale:
        retry_query = retry_query.where(Audit.started_at == audit.started_at)
    updated = db.execute(
        retry_query
        .values(
            audit_status="queued",
            started_at=None,
            completed_at=None,
            failure_code=None,
            failure_message=None,
            processing_attempt_id=None,
            processing_warnings=list(audit.processing_warnings or []) + [warning],
        )
    )
    if updated.rowcount != 1:
        db.rollback()
        raise HTTPException(status_code=409, detail="The audit changed during retry.")
    db.commit()
    db.refresh(audit)
    try:
        enqueue(audit.id)
    except Exception as exc:
        logger.warning("Audit retry queue unavailable for audit %s", audit.id)
        _mark_queue_failure(db, audit.id)
        raise HTTPException(
            status_code=503,
            detail="The audit could not be queued. Retry when the processing service is available.",
        ) from exc
    return _audit_response(audit)

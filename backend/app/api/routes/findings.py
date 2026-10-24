from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.audit_access import get_accessible_audit
from app.api.dependencies import get_current_user
from app.db.models import Audit, Feedback, Finding, User
from app.db.session import get_db
from app.schemas.audits import FindingFeedbackCreate, FindingFeedbackResponse

router = APIRouter(prefix="/findings", tags=["findings"])


@router.post(
    "/{finding_id}/feedback",
    response_model=FindingFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_finding_feedback(
    finding_id: UUID,
    payload: FindingFeedbackCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FindingFeedbackResponse:
    finding = db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    audit = db.get(Audit, finding.audit_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="Finding not found.")
    get_accessible_audit(db, user, audit.id)
    if audit.audit_status != "completed":
        raise HTTPException(
            status_code=409,
            detail="Feedback is available only for completed audit findings.",
        )

    feedback = Feedback(
        finding_id=finding.id,
        submitted_by=user.id,
        feedback_type=payload.feedback_type,
        description=(
            payload.description.strip()
            if payload.description is not None
            else None
        ),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FindingFeedbackResponse(
        id=feedback.id,
        finding_id=feedback.finding_id,
        feedback_type=feedback.feedback_type,
        description=feedback.description,
        created_at=feedback.created_at,
    )

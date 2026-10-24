from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_organization_membership
from app.db.models import Audit, Document, User

_READABLE_ORGANIZATION_ROLES = {"member", "admin", "owner"}


def get_accessible_audit(db: Session, user: User, audit_id: UUID) -> Audit:
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

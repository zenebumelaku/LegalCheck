from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional, Set
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_access_token
from app.db.models import AuthSession, OrganizationMembership, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    auth_session: AuthSession


def unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()

    auth_session = db.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(
            AuthSession.token_hash == hash_access_token(credentials.credentials),
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > datetime.now(timezone.utc),
        )
    )
    if auth_session is None or not auth_session.user.is_active:
        raise unauthorized()

    return AuthContext(user=auth_session.user, auth_session=auth_session)


def get_current_user(
    auth: AuthContext = Depends(get_auth_context),
) -> User:
    return auth.user


def require_roles(*roles: str) -> Callable[..., User]:
    allowed_roles: Set[str] = set(roles)
    if not allowed_roles:
        raise ValueError("At least one role is required.")

    def role_dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return user

    return role_dependency


def get_organization_membership(
    db: Session,
    user: User,
    organization_id: UUID,
    allowed_roles: Optional[Set[str]] = None,
) -> OrganizationMembership:
    membership = db.scalar(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )
    if allowed_roles is not None and membership.membership_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return membership


def require_organization_membership(
    allowed_roles: Optional[Set[str]] = None,
) -> Callable[..., OrganizationMembership]:
    def membership_dependency(
        organization_id: UUID,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> OrganizationMembership:
        return get_organization_membership(
            db=db,
            user=user,
            organization_id=organization_id,
            allowed_roles=allowed_roles,
        )

    return membership_dependency

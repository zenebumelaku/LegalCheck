import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import AuthContext, get_auth_context, get_current_user
from app.core.config import settings
from app.core.rate_limit import (
    enforce_login_rate_limit,
    enforce_password_reset_rate_limit,
    enforce_registration_rate_limit,
)
from app.core.security import (
    create_access_token,
    hash_access_token,
    hash_password,
    verify_password,
    verify_unknown_user_password,
)
from app.db.models import AuthSession, User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    UserResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


def create_login_response(user: User, db: Session) -> LoginResponse:
    access_token = create_access_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_access_token(access_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return LoginResponse(
        access_token=access_token,
        expires_at=expires_at,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_registration_rate_limit)],
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    user = User(
        name=payload.name,
        email=str(payload.email),
        password_hash=hash_password(payload.password.get_secret_value()),
        role="user",
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        existing_user_id = db.scalar(
            select(User.id).where(
                func.lower(func.trim(User.email)) == str(payload.email)
            )
        )
        if existing_user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with that email already exists.",
            ) from exc
        logger.error("Database constraint rejected account registration")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The account could not be created.",
        ) from exc
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=LoginResponse,
    dependencies=[Depends(enforce_login_rate_limit)],
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(
        select(User).where(func.lower(User.email) == str(payload.email))
    )
    password = payload.password.get_secret_value()
    if user is None:
        verify_unknown_user_password(password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(user.password_hash, password) or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_login_response(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> Response:
    auth.auth_session.revoked_at = datetime.now(timezone.utc)
    db.commit()
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post(
    "/password-reset-request",
    response_model=PasswordResetResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_password_reset_rate_limit)],
)
def password_reset_request(
    payload: PasswordResetRequest,
) -> PasswordResetResponse:
    return PasswordResetResponse(
        message=(
            "If an account exists, reset instructions can be sent after email "
            "delivery is configured."
        )
    )

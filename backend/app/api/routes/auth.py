import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, update
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
from app.db.models import AuthSession, PasswordResetToken, User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    PasswordResetCompleteResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.password_reset_email import (
    PasswordResetEmailError,
    create_password_reset_url,
    password_reset_email_is_configured,
    send_password_reset_email,
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
    db: Session = Depends(get_db),
) -> PasswordResetResponse:
    if not password_reset_email_is_configured(settings):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Password reset email is not configured.",
        )

    generic_response = PasswordResetResponse(
        message=(
            "If an account exists and email delivery succeeds, password reset "
            "instructions will be sent."
        )
    )
    user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email)))
    if user is None:
        return generic_response

    now = datetime.now(timezone.utc)
    token = create_access_token()
    token_record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_access_token(token),
        expires_at=now + timedelta(minutes=settings.password_reset_token_expire_minutes),
    )
    db.add(token_record)
    db.commit()

    try:
        send_password_reset_email(
            user.email,
            create_password_reset_url(token, settings),
            settings=settings,
        )
    except PasswordResetEmailError as exc:
        token_record.revoked_at = datetime.now(timezone.utc)
        db.commit()
        logger.error(
            "Password reset email delivery failed",
            extra={
                "provider": settings.password_reset_email_provider,
                "error_type": type(exc).__name__,
            },
        )
        return generic_response

    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != token_record.id,
            PasswordResetToken.consumed_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()
    return generic_response


@router.post(
    "/password-reset-confirm",
    response_model=PasswordResetCompleteResponse,
    dependencies=[Depends(enforce_password_reset_rate_limit)],
)
def password_reset_confirm(
    payload: PasswordResetConfirmRequest,
    db: Session = Depends(get_db),
) -> PasswordResetCompleteResponse:
    now = datetime.now(timezone.utc)
    token_record = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_access_token(payload.token))
        .with_for_update()
    )
    expires_at = token_record.expires_at if token_record is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if (
        token_record is None
        or token_record.consumed_at is not None
        or token_record.revoked_at is not None
        or expires_at is None
        or expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset token is invalid or expired.",
        )

    user = db.get(User, token_record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The password reset token is invalid or expired.",
        )

    token_record.consumed_at = now
    user.password_hash = hash_password(payload.password.get_secret_value())
    db.execute(
        update(AuthSession)
        .where(
            AuthSession.user_id == user.id,
            AuthSession.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.id != token_record.id,
            PasswordResetToken.consumed_at.is_(None),
            PasswordResetToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )
    db.commit()
    return PasswordResetCompleteResponse(
        message="Your password has been reset. Sign in with your new password."
    )

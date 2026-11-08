from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.legal_questions import LegalQuestionAnswer, LegalQuestionRequest
from app.services.legal_question_answering import (
    LegalQuestionProviderFailed,
    LegalQuestionProviderRateLimited,
    LegalQuestionProviderUnavailable,
    answer_legal_question,
)

router = APIRouter(prefix="/legal-questions", tags=["legal questions"])


@router.post(
    "/answer",
    response_model=LegalQuestionAnswer,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "AI provider rate limit reached."},
        status.HTTP_502_BAD_GATEWAY: {"description": "AI provider failed or returned an invalid response."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "AI answer generation is unavailable."},
    },
)
def ask_legal_question(
    payload: LegalQuestionRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegalQuestionAnswer:
    try:
        return answer_legal_question(
            payload.question,
            payload.review_context,
            db=db,
        )
    except LegalQuestionProviderRateLimited as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except LegalQuestionProviderUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LegalQuestionProviderFailed as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

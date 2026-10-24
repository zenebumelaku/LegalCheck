import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import require_roles
from app.core.config import settings
from app.db.models import LegalProvision, LegalSource, User
from app.db.session import get_db
from app.schemas.legal_sources import (
    LegalProvisionIngestion,
    LegalProvisionPage,
    LegalProvisionResponse,
    LegalSourceIngestionMetadata,
    LegalSourceIngestionResponse,
    LegalSourcePage,
    LegalSourceResponse,
    LegalSourceReviewRequest,
)
from app.services.legal_source_ingestion import (
    DuplicateLegalSourceFileError,
    DuplicateLegalSourceVersionError,
    ingest_legal_source,
    review_legal_source,
)
from app.storage.interface import PrivateFileStorage, get_private_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/legal-sources", tags=["legal sources"])


def get_legal_source_storage() -> PrivateFileStorage:
    return get_private_storage(str(settings.private_storage_path))


def _source_query(
    *,
    q: Optional[str],
    title: Optional[str],
    law_number: Optional[str],
    language: Optional[str],
    source_type: Optional[str],
    legal_status: Optional[str],
    article_number: Optional[str],
):
    query = select(LegalSource).where(LegalSource.verification_status != "rejected")
    if q:
        term = f"%{q.strip()}%"
        query = query.where(
            or_(
                LegalSource.title.ilike(term),
                LegalSource.law_number.ilike(term),
            )
        )
    if title:
        query = query.where(LegalSource.title.ilike(f"%{title.strip()}%"))
    if law_number:
        query = query.where(LegalSource.law_number.ilike(f"%{law_number.strip()}%"))
    if language:
        query = query.where(LegalSource.language.ilike(language.strip()))
    if source_type:
        query = query.where(LegalSource.source_type.ilike(source_type.strip()))
    if legal_status:
        query = query.where(LegalSource.legal_status == legal_status)
    if article_number:
        query = query.join(LegalSource.provisions).where(
            LegalProvision.article_number == article_number.strip()
        )
        query = query.distinct()
    return query


def _source_page(
    db: Session,
    *,
    q: Optional[str],
    title: Optional[str],
    law_number: Optional[str],
    language: Optional[str],
    source_type: Optional[str],
    legal_status: Optional[str],
    article_number: Optional[str],
    limit: int,
    offset: int,
) -> LegalSourcePage:
    query = _source_query(
        q=q,
        title=title,
        law_number=law_number,
        language=language,
        source_type=source_type,
        legal_status=legal_status,
        article_number=article_number,
    )
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = db.scalar(count_query) or 0
    sources = db.scalars(
        query.order_by(LegalSource.title, LegalSource.version_label)
        .offset(offset)
        .limit(limit)
    ).all()
    return LegalSourcePage(
        items=[LegalSourceResponse.model_validate(source) for source in sources],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get("/search", response_model=LegalSourcePage)
def search_legal_sources(
    q: Optional[str] = Query(default=None, min_length=1, max_length=200),
    title: Optional[str] = Query(default=None, min_length=1, max_length=500),
    law_number: Optional[str] = Query(default=None, min_length=1, max_length=100),
    article_number: Optional[str] = Query(default=None, min_length=1, max_length=100),
    language: Optional[str] = Query(default=None, min_length=1, max_length=50),
    source_type: Optional[str] = Query(default=None, min_length=1, max_length=100),
    legal_status: Optional[str] = Query(
        default=None,
        pattern="^(unknown|current|amended|repealed|superseded)$",
    ),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LegalSourcePage:
    return _source_page(
        db,
        q=q,
        title=title,
        law_number=law_number,
        language=language,
        source_type=source_type,
        legal_status=legal_status,
        article_number=article_number,
        limit=limit,
        offset=offset,
    )


@router.get("", response_model=LegalSourcePage)
def list_legal_sources(
    q: Optional[str] = Query(default=None, min_length=1, max_length=200),
    title: Optional[str] = Query(default=None, min_length=1, max_length=500),
    law_number: Optional[str] = Query(default=None, min_length=1, max_length=100),
    language: Optional[str] = Query(default=None, min_length=1, max_length=50),
    source_type: Optional[str] = Query(default=None, min_length=1, max_length=100),
    legal_status: Optional[str] = Query(
        default=None,
        pattern="^(unknown|current|amended|repealed|superseded)$",
    ),
    article_number: Optional[str] = Query(default=None, min_length=1, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LegalSourcePage:
    return _source_page(
        db,
        q=q,
        title=title,
        law_number=law_number,
        language=language,
        source_type=source_type,
        legal_status=legal_status,
        article_number=article_number,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/ingest",
    response_model=LegalSourceIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_source(
    metadata_json: str = Form(...),
    provisions_json: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
    storage: PrivateFileStorage = Depends(get_legal_source_storage),
) -> LegalSourceIngestionResponse:
    try:
        metadata = LegalSourceIngestionMetadata.model_validate_json(metadata_json)
        provisions = TypeAdapter(list[LegalProvisionIngestion]).validate_json(
            provisions_json
        )
    except (ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source metadata or provision data is invalid.",
        ) from exc

    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Legal source files must be PDF documents.",
        )
    if (file.content_type or "").split(";", maxsplit=1)[0].lower() != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file content type must be application/pdf.",
        )
    content = file.file.read(settings.max_upload_size_bytes + 1)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded source file is empty.",
        )
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The source file exceeds the configured upload size limit.",
        )
    if b"%PDF-" not in content[:1024] or b"%%EOF" not in content[-2048:]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded file does not appear to be a complete PDF.",
        )

    try:
        source, provision_count = ingest_legal_source(
            db=db,
            storage=storage,
            ingested_by=admin.id,
            metadata=metadata,
            provisions=provisions,
            file_content=content,
        )
    except DuplicateLegalSourceFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This PDF is already registered as source {exc.source_id}.",
        ) from exc
    except DuplicateLegalSourceVersionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except OSError as exc:
        logger.error("Private legal source storage failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The legal source file could not be stored.",
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Database rejected legal source ingestion")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The legal source version conflicts with an existing record.",
        ) from exc

    return LegalSourceIngestionResponse(
        source=LegalSourceResponse.model_validate(source),
        provisions_created=provision_count,
    )


@router.get("/{source_id}/provisions", response_model=LegalProvisionPage)
def list_source_provisions(
    source_id: UUID,
    article_number: Optional[str] = Query(default=None, min_length=1, max_length=100),
    sub_article_reference: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    language: Optional[str] = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> LegalProvisionPage:
    source_exists = db.scalar(
        select(LegalSource.id).where(
            LegalSource.id == source_id,
            LegalSource.verification_status != "rejected",
        )
    )
    if source_exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legal source not found.",
        )

    query = select(LegalProvision).where(LegalProvision.legal_source_id == source_id)
    if article_number:
        query = query.where(LegalProvision.article_number == article_number.strip())
    if sub_article_reference:
        query = query.where(
            LegalProvision.sub_article_reference == sub_article_reference.strip()
        )
    if language:
        query = query.where(LegalProvision.language.ilike(language.strip()))
    total = db.scalar(
        select(func.count()).select_from(query.order_by(None).subquery())
    ) or 0
    provisions = db.scalars(
        query.order_by(LegalProvision.article_number, LegalProvision.sub_article_reference)
        .offset(offset)
        .limit(limit)
    ).all()
    return LegalProvisionPage(
        items=[
            LegalProvisionResponse.model_validate(provision)
            for provision in provisions
        ],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.post("/{source_id}/verify", response_model=LegalSourceResponse)
def verify_legal_source(
    source_id: UUID,
    payload: LegalSourceReviewRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_roles("admin")),
) -> LegalSourceResponse:
    source = db.get(LegalSource, source_id)
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legal source not found.",
        )
    try:
        source = review_legal_source(
            db=db,
            source=source,
            reviewer_id=reviewer.id,
            decision=payload.decision,
            legal_status=payload.legal_status,
            verification_notes=payload.verification_notes,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The source ingester cannot verify the same source.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return LegalSourceResponse.model_validate(source)


@router.get("/{source_id}", response_model=LegalSourceResponse)
def get_legal_source(
    source_id: UUID,
    db: Session = Depends(get_db),
) -> LegalSourceResponse:
    source = db.scalar(
        select(LegalSource).where(
            LegalSource.id == source_id,
            LegalSource.verification_status != "rejected",
        )
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Legal source not found.",
        )
    return LegalSourceResponse.model_validate(source)

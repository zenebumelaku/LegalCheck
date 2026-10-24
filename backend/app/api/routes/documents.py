import hashlib
import logging
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_organization_membership
from app.core.config import settings
from app.db.models import Document, OrganizationMembership, User
from app.db.session import get_db
from app.schemas.documents import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
    ExtractedPageResponse,
    ExtractedParagraphResponse,
)
from app.services.document_extraction import (
    CorruptedDocumentError,
    EncryptedDocumentError,
    UnsupportedDocumentError,
    extract_document,
)
from app.storage.interface import PrivateFileStorage, get_private_storage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED_FORMATS = {
    ".pdf": ("application/pdf", "pdf"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
}
_READABLE_ORGANIZATION_ROLES = {"member", "admin", "owner"}
_MANAGE_ORGANIZATION_ROLES = {"admin", "owner"}


def get_document_storage() -> PrivateFileStorage:
    return get_private_storage(str(settings.private_storage_path))


def _safe_filename(filename: Optional[str]) -> str:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A filename is required.",
        )
    normalized = unicodedata.normalize("NFC", filename.replace("\\", "/"))
    basename = PurePosixPath(normalized).name
    basename = "".join(character for character in basename if character.isprintable())
    if not basename or len(basename) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The filename is invalid.",
        )
    return basename


def _read_upload(file: UploadFile, max_size: int) -> bytes:
    content = bytearray()
    while True:
        chunk = file.file.read(min(64 * 1024, max_size + 1 - len(content)))
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The uploaded file exceeds the configured size limit.",
            )
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )
    return bytes(content)


def _validate_file_type(filename: str, content_type: Optional[str], content: bytes) -> str:
    extension = PurePosixPath(filename).suffix.lower()
    allowed = _ALLOWED_FORMATS.get(extension)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF and DOCX files are supported.",
        )
    expected_mime, document_type = allowed
    if (content_type or "").split(";", maxsplit=1)[0].strip().lower() != expected_mime:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file content type does not match a supported document type.",
        )

    if document_type == "pdf":
        if b"%PDF-" not in content[:1024]:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="The file content does not match its extension.",
            )
    elif content.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Encrypted or legacy Office documents are not supported.",
        )
    elif not content.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The file content does not match its extension.",
        )
    return document_type


def _get_accessible_document(
    db: Session,
    user: User,
    document_id: uuid.UUID,
) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.deleted_at.is_(None),
        )
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    if document.organization_id is not None:
        get_organization_membership(
            db,
            user,
            document.organization_id,
            allowed_roles=_READABLE_ORGANIZATION_ROLES,
        )
        return document

    if document.owner_user_id == user.id:
        return document

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Document not found.",
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    organization_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: PrivateFileStorage = Depends(get_document_storage),
) -> DocumentUploadResponse:
    if organization_id is not None:
        get_organization_membership(
            db,
            user,
            organization_id,
            allowed_roles=_READABLE_ORGANIZATION_ROLES,
        )

    filename = _safe_filename(file.filename)
    content = _read_upload(file, settings.max_upload_size_bytes)
    document_type = _validate_file_type(filename, file.content_type, content)

    try:
        extraction = extract_document(
            content,
            document_type,
            settings.max_docx_uncompressed_size_bytes,
            settings.ocr_enabled,
        )
    except EncryptedDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password-protected documents are not supported.",
        ) from exc
    except CorruptedDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The uploaded document is corrupted or cannot be read.",
        ) from exc
    except UnsupportedDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The document structure is unsupported or exceeds safe processing limits.",
        ) from exc

    storage_key = f"{uuid.uuid4().hex}{PurePosixPath(filename).suffix.lower()}"
    try:
        storage.store(storage_key, content)
    except OSError as exc:
        logger.error("Private document storage failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document could not be stored.",
        ) from exc

    document = Document(
        owner_user_id=user.id,
        organization_id=organization_id,
        original_filename=filename,
        storage_key=storage_key,
        content_type=_ALLOWED_FORMATS[PurePosixPath(filename).suffix.lower()][0],
        file_size=len(content),
        checksum=hashlib.sha256(content).hexdigest(),
        document_type=document_type,
        processing_status="warning" if extraction.warnings else "completed",
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            storage.delete(storage_key)
        except OSError:
            logger.error("Failed to clean up an uncommitted private document")
        raise

    return DocumentUploadResponse(
        **DocumentResponse.model_validate(document).model_dump(),
        pages=[
            ExtractedPageResponse(
                page_number=page.page_number,
                paragraphs=[
                    ExtractedParagraphResponse(
                        paragraph_number=paragraph.paragraph_number,
                        text=paragraph.text,
                    )
                    for paragraph in page.paragraphs
                ],
            )
            for page in extraction.pages
        ],
        warnings=extraction.warnings,
        extracted_characters=extraction.extracted_characters,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    organization_id: Optional[uuid.UUID] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentListResponse:
    query = select(Document).where(Document.deleted_at.is_(None))
    if organization_id is not None:
        get_organization_membership(
            db,
            user,
            organization_id,
            allowed_roles=_READABLE_ORGANIZATION_ROLES,
        )
        query = query.where(Document.organization_id == organization_id)
    else:
        member_ids = select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.membership_role.in_(_READABLE_ORGANIZATION_ROLES),
        )
        query = query.where(
            (
                (Document.owner_user_id == user.id)
                & Document.organization_id.is_(None)
            )
            | Document.organization_id.in_(member_ids)
        )

    documents = db.scalars(
        query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(document) for document in documents],
        limit=limit,
        offset=offset,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentResponse:
    document = _get_accessible_document(db, user, document_id)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    storage: PrivateFileStorage = Depends(get_document_storage),
) -> None:
    document = _get_accessible_document(db, user, document_id)
    if document.owner_user_id != user.id:
        if document.organization_id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )
        get_organization_membership(
            db,
            user,
            document.organization_id,
            allowed_roles=_MANAGE_ORGANIZATION_ROLES,
        )

    storage_key = document.storage_key
    document.deleted_at = datetime.now(timezone.utc)
    document.processing_status = "deleted"
    db.commit()
    try:
        storage.delete(storage_key)
    except OSError as exc:
        logger.error("Private document cleanup failed", extra={"document_id": str(document.id)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The document was deleted from the account but private storage cleanup is pending.",
        ) from exc

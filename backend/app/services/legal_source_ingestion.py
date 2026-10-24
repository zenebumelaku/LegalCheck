import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LegalProvision, LegalSource
from app.schemas.legal_sources import (
    LegalProvisionIngestion,
    LegalSourceIngestionMetadata,
)
from app.storage.interface import PrivateFileStorage

logger = logging.getLogger(__name__)


class DuplicateLegalSourceFileError(ValueError):
    def __init__(self, source_id: uuid.UUID) -> None:
        self.source_id = source_id
        super().__init__("This file is already registered.")


class DuplicateLegalSourceVersionError(ValueError):
    pass


def is_eligible_for_production_findings(source: LegalSource) -> bool:
    return source.eligible_for_findings


def ingest_legal_source(
    db: Session,
    storage: PrivateFileStorage,
    ingested_by: uuid.UUID,
    metadata: LegalSourceIngestionMetadata,
    provisions: Sequence[LegalProvisionIngestion],
    file_content: bytes,
) -> tuple[LegalSource, int]:
    checksum = hashlib.sha256(file_content).hexdigest()
    duplicate = db.scalar(
        select(LegalSource).where(LegalSource.file_checksum == checksum)
    )
    if duplicate is not None:
        raise DuplicateLegalSourceFileError(duplicate.id)

    if not provisions:
        raise ValueError("At least one provision is required.")

    provision_keys: set[tuple[str, str | None, str | None]] = set()
    for provision in provisions:
        key = (
            provision.article_number,
            provision.sub_article_reference,
            provision.section_title,
        )
        if key in provision_keys:
            raise ValueError("Duplicate article references were supplied.")
        provision_keys.add(key)

    existing_version = db.scalar(
        select(LegalSource.id).where(
            LegalSource.law_number == metadata.law_number,
            LegalSource.version_label == metadata.version_label,
        )
    )
    if existing_version is not None:
        raise DuplicateLegalSourceVersionError(
            "That law number and version label are already registered."
        )

    storage_key = f"legal-sources/{uuid.uuid4().hex}.pdf"
    storage.store(storage_key, file_content)
    source = LegalSource(
        title=metadata.title,
        law_number=metadata.law_number,
        source_type=metadata.source_type,
        jurisdiction=metadata.jurisdiction,
        language=metadata.language,
        publication_date=metadata.publication_date,
        effective_date=metadata.effective_date,
        end_date=metadata.end_date,
        legal_status="unknown",
        version_label=metadata.version_label,
        original_source_url=str(metadata.original_source_url),
        file_checksum=checksum,
        source_file_storage_key=storage_key,
        ingested_by=ingested_by,
        verification_status="pending",
    )
    for provision in provisions:
        source.provisions.append(
            LegalProvision(
                article_number=provision.article_number,
                sub_article_reference=provision.sub_article_reference,
                section_title=provision.section_title,
                text=provision.text,
                page_number=provision.page_number,
                language=provision.language or metadata.language,
                metadata_json={},
            )
        )
    db.add(source)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            storage.delete(storage_key)
        except OSError:
            logger.error(
                "Failed to clean up uncommitted legal source after %s",
                type(exc).__name__,
            )
        raise
    db.refresh(source)
    return source, len(provisions)


def review_legal_source(
    db: Session,
    source: LegalSource,
    reviewer_id: uuid.UUID,
    decision: str,
    legal_status: str,
    verification_notes: str,
) -> LegalSource:
    if source.verification_status != "pending":
        raise ValueError("Only pending sources can be reviewed.")
    if source.source_file_storage_key is None or source.file_checksum is None:
        raise ValueError("The source has no retained file provenance.")
    if source.ingested_by == reviewer_id:
        raise PermissionError("The ingester cannot review their own source.")

    source.verification_status = decision
    source.legal_status = legal_status if decision == "verified" else "unknown"
    source.verification_notes = verification_notes
    if decision == "verified":
        source.verified_by = reviewer_id
        source.verified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(source)
    return source

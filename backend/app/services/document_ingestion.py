import hashlib
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Document,
    LegalProvision,
    LegalProvisionChunk,
    LegalSource,
)
from app.services.document_extraction import ExtractionResult
from app.services.embeddings import get_embedding_provider
from app.services.legal_chunking import chunk_legal_provision
from app.services.legal_question_cache import get_legal_question_cache

logger = logging.getLogger(__name__)


def ingest_document_to_vector_store(
    db: Session,
    document: Document,
    extraction: ExtractionResult,
    provider: Optional[object] = None,
) -> int:
    """
    Ingests an extracted document into the RAG knowledge base:
    1. Creates or updates a verified LegalSource entry for the document.
    2. Creates LegalProvision records for the document pages/sections.
    3. Chunks the text into meaningful overlapping units.
    4. Computes 384-dimensional dense embeddings using the local embedding model.
    5. Saves LegalProvisionChunk rows in the database.
    6. Invalidates existing Redis question cache keys so the document is searchable immediately.
    """
    if not extraction.pages:
        logger.warning("Document %s contains no extracted pages; skipping vector indexing", document.id)
        return 0

    # Ensure document has a checksum
    checksum = document.checksum or hashlib.sha256(str(document.id).encode("utf-8")).hexdigest()

    # Check if a LegalSource already exists for this storage key or checksum
    source = db.scalar(
        select(LegalSource).where(
            (LegalSource.source_file_storage_key == document.storage_key)
            | (LegalSource.file_checksum == checksum)
        )
    )

    if source is None:
        source = LegalSource(
            id=uuid.uuid4(),
            title=document.original_filename,
            law_number=f"DOC-{document.id.hex[:8]}",
            source_type="uploaded_document",
            jurisdiction="ET",
            language=document.detected_language or "en",
            publication_date=date.today(),
            effective_date=date.today(),
            end_date=None,
            legal_status="current",
            version_label="v1",
            original_source_url=f"document://{document.original_filename}",
            file_checksum=checksum,
            source_file_storage_key=document.storage_key,
            ingested_by=document.owner_user_id,
            verified_by=document.owner_user_id,
            verification_notes=f"User uploaded document: {document.original_filename}",
            verification_status="verified",
            verified_at=datetime.now(timezone.utc),
        )
        db.add(source)
        db.flush()
    else:
        # Ensure it is verified and current
        source.verification_status = "verified"
        source.legal_status = "current"
        source.effective_date = source.effective_date or date.today()
        if source.verified_by is None:
            source.verified_by = document.owner_user_id
            source.verified_at = datetime.now(timezone.utc)
        db.flush()

    # Create provisions for each page with non-empty text
    provisions: list[LegalProvision] = []
    for page in extraction.pages:
        page_text = "\n\n".join(
            p.text.strip() for p in page.paragraphs if p.text and p.text.strip()
        ).strip()
        if not page_text:
            continue

        # Check if provision already exists for this page
        article_num = f"Page {page.page_number}"
        provision = db.scalar(
            select(LegalProvision).where(
                LegalProvision.legal_source_id == source.id,
                LegalProvision.article_number == article_num,
            )
        )
        if provision is None:
            provision = LegalProvision(
                id=uuid.uuid4(),
                legal_source_id=source.id,
                article_number=article_num,
                sub_article_reference=None,
                section_title=f"{document.original_filename} - Page {page.page_number}",
                text=page_text,
                page_number=page.page_number,
                language=document.detected_language or "en",
                metadata_json={"document_id": str(document.id)},
            )
            db.add(provision)
            db.flush()
        else:
            provision.text = page_text
            db.flush()

        provisions.append(provision)

    if not provisions:
        logger.warning("No non-empty text provisions created for document %s", document.id)
        return 0

    # Load embedding provider
    if provider is None:
        settings = get_settings()
        provider = get_embedding_provider(settings)

    if provider is None:
        from pathlib import Path
        local_path = Path("var/models/all-MiniLM-L6-v2")
        if not local_path.is_dir():
            local_path = Path(__file__).resolve().parent.parent.parent / "var" / "models" / "all-MiniLM-L6-v2"
        if local_path.is_dir():
            from app.services.embeddings import SentenceTransformersEmbeddingProvider
            provider = SentenceTransformersEmbeddingProvider(
                model_path=local_path,
                model_version="v1",
            )

    if provider is None:
        logger.warning("No embedding provider available for indexing document %s", document.id)
        return 0

    total_chunks_created = 0
    all_chunks_to_embed: list[tuple[LegalProvisionChunk, str]] = []

    for provision in provisions:
        text_chunks = chunk_legal_provision(
            source,
            provision,
            max_characters=1500,
            overlap_characters=200,
        )

        existing_chunks = db.scalars(
            select(LegalProvisionChunk).where(
                LegalProvisionChunk.provision_id == provision.id,
                LegalProvisionChunk.embedding_model == provider.model_name,
                LegalProvisionChunk.embedding_version == provider.model_version,
            )
        ).all()
        existing_by_index = {c.chunk_index: c for c in existing_chunks}

        for chunk in text_chunks:
            chunk_hash = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            existing = existing_by_index.get(chunk.chunk_index)

            if existing is not None:
                if existing.embedding is not None and existing.content_checksum == chunk_hash:
                    continue
                row = existing
                row.chunk_text = chunk.text
                row.content_checksum = chunk_hash
            else:
                row = LegalProvisionChunk(
                    id=uuid.uuid4(),
                    provision_id=provision.id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    content_checksum=chunk_hash,
                    page_number=chunk.page_number,
                    source_version_label=source.version_label,
                    embedding_model=provider.model_name,
                    embedding_version=provider.model_version,
                )
                db.add(row)

            all_chunks_to_embed.append((row, chunk.text))

    if all_chunks_to_embed:
        batch_size = 32
        for i in range(0, len(all_chunks_to_embed), batch_size):
            batch = all_chunks_to_embed[i : i + batch_size]
            texts = [t for _, t in batch]
            vectors = provider.embed(texts)
            for (row, _), vec in zip(batch, vectors):
                row.embedding = vec
            total_chunks_created += len(batch)

    db.flush()

    # Invalidate Redis question cache so any prior queries about this topic are refreshed
    try:
        cache = get_legal_question_cache()
        deleted_count = cache.invalidate_all()
        logger.info(
            "Document %s ingested into RAG: %d chunks created/updated, %d cache entries invalidated",
            document.id,
            total_chunks_created,
            deleted_count,
        )
    except Exception as exc:
        logger.warning("Could not invalidate Redis cache after document ingestion: %s", exc)

    return total_chunks_created

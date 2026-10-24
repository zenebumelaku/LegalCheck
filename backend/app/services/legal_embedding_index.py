import hashlib
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import LegalProvision, LegalProvisionChunk, LegalSource
from app.schemas.legal_retrieval import StoredEmbeddingInfo
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
    validate_embedding,
)
from app.services.legal_chunking import chunk_legal_provision

EMBEDDING_BATCH_SIZE = 32


def generate_embeddings_for_source(
    db: Session,
    source: LegalSource,
    provider: EmbeddingProvider,
    *,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> StoredEmbeddingInfo:
    if source.verification_status != "verified":
        raise ValueError("Embeddings are generated only for verified legal sources.")
    if provider.dimensions != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"The configured vector column requires {EMBEDDING_DIMENSIONS} dimensions."
        )
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero.")

    provisions = db.scalars(
        select(LegalProvision)
        .where(LegalProvision.legal_source_id == source.id)
        .order_by(LegalProvision.article_number, LegalProvision.sub_article_reference)
    ).all()
    missing: list[tuple[LegalProvisionChunk, str]] = []
    for provision in provisions:
        chunks = chunk_legal_provision(source, provision)
        existing_rows = db.scalars(
            select(LegalProvisionChunk).where(
                LegalProvisionChunk.provision_id == provision.id,
                LegalProvisionChunk.embedding_model == provider.model_name,
                LegalProvisionChunk.embedding_version == provider.model_version,
            )
        ).all()
        existing_by_index = {row.chunk_index: row for row in existing_rows}
        expected_indices = {chunk.chunk_index for chunk in chunks}
        if existing_by_index.keys() - expected_indices:
            raise ValueError(
                "Stored chunks no longer match the source text; create a new "
                "source or embedding version rather than replacing indexed content."
            )
        for chunk in chunks:
            checksum = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            existing = existing_by_index.get(chunk.chunk_index)
            if existing is not None:
                if existing.content_checksum != checksum:
                    raise ValueError(
                        "Chunk content changed for an existing model version; "
                        "create a new legal source version or embedding version."
                    )
                if existing.embedding is not None:
                    continue
                row = existing
            else:
                row = LegalProvisionChunk(
                    provision_id=provision.id,
                    chunk_index=chunk.chunk_index,
                    chunk_text=chunk.text,
                    content_checksum=checksum,
                    page_number=chunk.page_number,
                    source_version_label=chunk.version_label,
                    embedding_model=provider.model_name,
                    embedding_version=provider.model_version,
                )
            missing.append((row, chunk.text))

    for start in range(0, len(missing), batch_size):
        batch = missing[start : start + batch_size]
        vectors = provider.embed([text for _, text in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding provider returned an unexpected vector count.")
        for (row, _), vector in zip(batch, vectors):
            row.embedding = validate_embedding(
                vector,
                expected_dimensions=provider.dimensions,
            )
            db.add(row)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return StoredEmbeddingInfo(
        model=provider.model_name,
        version=provider.model_version,
        dimensions=EMBEDDING_DIMENSIONS,
        chunks_created=len(missing),
    )


def generate_embeddings_for_verified_sources(
    db: Session,
    provider: EmbeddingProvider,
    *,
    source_id: Optional[UUID] = None,
    batch_size: int = EMBEDDING_BATCH_SIZE,
) -> list[StoredEmbeddingInfo]:
    query = select(LegalSource).options(joinedload(LegalSource.provisions)).where(
        LegalSource.verification_status == "verified"
    )
    if source_id is not None:
        query = query.where(LegalSource.id == source_id)
    sources = db.scalars(query.order_by(LegalSource.created_at)).unique().all()
    if source_id is not None and not sources:
        raise LookupError("No verified legal source matched the requested ID.")
    return [
        generate_embeddings_for_source(
            db,
            source,
            provider,
            batch_size=batch_size,
        )
        for source in sources
    ]

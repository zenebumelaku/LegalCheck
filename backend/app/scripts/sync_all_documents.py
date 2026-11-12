import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import logging
from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models import Document, LegalSource
from app.storage.interface import get_private_storage
from app.core.config import settings
from app.services.document_extraction import extract_document
from app.services.document_ingestion import ingest_document_to_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sync_all_documents")

def sync_all_documents():
    db = get_session_factory()()
    storage = get_private_storage(str(settings.private_storage_path))
    
    docs = db.scalars(
        select(Document).where(Document.deleted_at.is_(None))
    ).all()
    
    logger.info("Found %d active documents in database", len(docs))
    synced_count = 0
    
    for doc in docs:
        # Check if already indexed
        existing_source = db.scalar(
            select(LegalSource).where(
                (LegalSource.source_file_storage_key == doc.storage_key)
                | (LegalSource.file_checksum == doc.checksum)
            )
        )
        if existing_source is not None:
            logger.info("Document '%s' already indexed as LegalSource %s", doc.original_filename, existing_source.id)
            continue
            
        logger.info("Ingesting un-indexed document: '%s' (ID: %s)", doc.original_filename, doc.id)
        try:
            content = storage.read(doc.storage_key)
            extraction = extract_document(
                content,
                doc.document_type or "pdf",
                settings.max_docx_uncompressed_size_bytes,
                settings.ocr_enabled,
            )
            chunks_created = ingest_document_to_vector_store(db, doc, extraction)
            db.commit()
            logger.info("✓ Successfully ingested '%s': %d chunks created", doc.original_filename, chunks_created)
            synced_count += 1
        except FileNotFoundError:
            db.rollback()
            from datetime import datetime, timezone
            doc.deleted_at = datetime.now(timezone.utc)
            doc.processing_status = "deleted"
            db.commit()
            logger.warning("Cleaned up orphaned document '%s' (storage file missing)", doc.original_filename)
        except Exception as exc:
            db.rollback()
            logger.error("Failed to ingest '%s': %s", doc.original_filename, exc)

    logger.info("Sync complete. Ingested %d documents.", synced_count)
    db.close()

if __name__ == "__main__":
    sync_all_documents()

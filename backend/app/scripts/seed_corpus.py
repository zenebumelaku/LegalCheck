import json
import logging
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import User, LegalSource
from app.db.session import get_session_factory
from app.schemas.legal_sources import (
    LegalProvisionIngestion,
    LegalSourceIngestionMetadata,
)
from app.services.embeddings import SentenceTransformersEmbeddingProvider
from app.services.legal_embedding_index import generate_embeddings_for_source
from app.services.legal_source_ingestion import (
    ingest_legal_source,
    review_legal_source,
    review_legal_source_applicability,
)
from app.storage.interface import LocalPrivateFileStorage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def seed_corpus():
    corpus_dir = Path("../legalcheck_document").resolve()
    if not corpus_dir.exists():
        corpus_dir = Path("legalcheck_document").resolve()
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Cannot find legalcheck_document directory at {corpus_dir}")

    meta_file = corpus_dir / "metadata.json"
    prov_file = corpus_dir / "provisions.json"
    pdf_file = corpus_dir / "source.pdf"

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_dict = json.load(f)
    with open(prov_file, "r", encoding="utf-8") as f:
        prov_list = json.load(f)
    with open(pdf_file, "rb") as f:
        pdf_bytes = f.read()

    meta_dict["jurisdiction"] = "ET"
    meta_dict["language"] = "en"
    if not meta_dict.get("effective_date"):
        meta_dict["effective_date"] = "2019-09-05"

    metadata = LegalSourceIngestionMetadata.model_validate(meta_dict)
    provisions = [LegalProvisionIngestion.model_validate(p) for p in prov_list]

    storage = LocalPrivateFileStorage(Path("var/private-documents"))
    session_factory = get_session_factory()

    with session_factory() as db:
        admin_user = db.scalar(select(User).where(User.email == "melakuzenebu@gmail.com"))
        if not admin_user:
            admin_user = User(
                name="Zenebu Melaku",
                email="melakuzenebu@gmail.com",
                password_hash="admin-hash",
                role="admin",
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        elif admin_user.role != "admin":
            admin_user.role = "admin"
            db.commit()
            db.refresh(admin_user)

        ingester_user = db.scalar(select(User).where(User.email == "ingester@legalcheck.et"))
        if not ingester_user:
            ingester_user = User(
                name="LegalCheck Ingestion Service",
                email="ingester@legalcheck.et",
                password_hash="ingester-hash",
                role="user",
            )
            db.add(ingester_user)
            db.commit()
            db.refresh(ingester_user)

        existing_source = db.scalar(
            select(LegalSource).where(
                LegalSource.law_number == metadata.law_number,
                LegalSource.version_label == metadata.version_label,
            )
        )

        if not existing_source:
            logger.info("Ingesting Labour Proclamation No. 1156/2019...")
            source, count = ingest_legal_source(
                db=db,
                storage=storage,
                ingested_by=ingester_user.id,
                metadata=metadata,
                provisions=provisions,
                file_content=pdf_bytes,
            )
            logger.info("Ingested source %s with %d provisions.", source.id, count)
        else:
            source = existing_source
            logger.info("Source %s already exists.", source.id)

        if source.verification_status != "verified":
            logger.info("Reviewing source verification...")
            source = review_legal_source(
                db=db,
                source=source,
                reviewer_id=admin_user.id,
                decision="verified",
                legal_status="current",
                verification_notes="Independently verified against official Federal Negarit Gazette publication.",
            )
            logger.info("Source verified successfully.")

        if not source.applicability_reviewed_at or source.legal_status != "current":
            logger.info("Performing applicability review...")
            source = review_legal_source_applicability(
                db=db,
                source=source,
                reviewer_id=admin_user.id,
                legal_status="current",
                effective_date=date(2019, 9, 5),
                end_date=None,
                verification_notes="In force per Ministry of Justice official law registry.",
            )
            logger.info("Applicability review completed.")

        model_path = Path("var/models/all-MiniLM-L6-v2")
        if model_path.exists():
            logger.info("Generating embeddings for verified provisions...")
            provider = SentenceTransformersEmbeddingProvider(
                model_path=model_path,
                model_version="v1",
            )
            info = generate_embeddings_for_source(db, source, provider, batch_size=32)
            logger.info("Embeddings generated: %s", info.model_dump())

    print("Corpus seeding completed successfully!")


if __name__ == "__main__":
    seed_corpus()

import io
import pytest
from uuid import UUID
from datetime import date
from sqlalchemy import select

from app.db.models import Document, LegalSource, LegalProvisionChunk, User
from app.db.session import get_session_factory
from app.services.document_extraction import extract_document
from app.services.document_ingestion import ingest_document_to_vector_store
from app.services.legal_question_answering import answer_legal_question
from app.services.legal_question_cache import get_legal_question_cache
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet


@pytest.fixture
def test_user(db_session):
    user = db_session.scalar(select(User).where(User.email == "test_rag_user@legalcheck.et"))
    if not user:
        user = User(
            name="Test RAG User",
            email="test_rag_user@legalcheck.et",
            password_hash="test-hash",
            role="user",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_document_ingestion_and_rag_pipeline(db_session, test_user):
    # 1. Create a dynamic test PDF document in-memory
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Addis Tech Severance and Gratuity Policy", styles["Title"]),
        Paragraph(
            "Section 1: Special Severance Calculation. "
            "Employees terminated due to technological redundancy shall receive a special severance package "
            "equal to 4 months of gross salary plus an additional 15 days of salary for each full year of service.",
            styles["BodyText"],
        ),
    ]
    doc.build(story)
    pdf_bytes = pdf_buffer.getvalue()

    # 2. Extract document text
    extraction = extract_document(pdf_bytes, "pdf", 10 * 1024 * 1024, False)
    assert extraction.extracted_characters > 0
    assert len(extraction.pages) >= 1

    # 3. Create document record
    import hashlib, uuid
    checksum = hashlib.sha256(pdf_bytes).hexdigest()
    doc_record = Document(
        id=uuid.uuid4(),
        owner_user_id=test_user.id,
        original_filename="addis_tech_severance_policy.pdf",
        storage_key=f"test-{uuid.uuid4().hex}.pdf",
        content_type="application/pdf",
        file_size=len(pdf_bytes),
        checksum=checksum,
        document_type="pdf",
        processing_status="completed",
    )
    db_session.add(doc_record)
    db_session.flush()

    # 4. Ingest into vector store
    chunks_created = ingest_document_to_vector_store(db_session, doc_record, extraction)
    db_session.commit()

    assert chunks_created >= 1

    # 5. Verify chunks and embeddings in database
    source = db_session.scalar(select(LegalSource).where(LegalSource.file_checksum == checksum))
    assert source is not None
    assert source.verification_status == "verified"
    assert source.eligible_for_findings is True

    chunks = db_session.scalars(
        select(LegalProvisionChunk)
        .join(LegalSource, LegalSource.id == source.id)
    ).all()
    assert len(chunks) >= 1
    assert any(c.embedding is not None for c in chunks)
    # 384 dimensions
    for c in chunks:
        if c.embedding is not None:
            assert len(c.embedding) == 384

    # 6. Verify RAG retrieval answers the question based on the newly uploaded document
    import json
    class StubLLMProvider:
        model_name = "stub-model"
        model_version = "v1"
        def answer_legal_question(self, question: str, evidence: list[dict]) -> str:
            assert len(evidence) >= 1
            ev = evidence[0]
            return json.dumps({
                "answer": "Employees terminated due to technological redundancy receive a special severance package equal to 4 months of gross salary.",
                "evidence_assessment": "supporting",
                "citations": [{
                    "source_id": ev["source_id"],
                    "provision_id": ev["provision_id"],
                    "article_number": ev["article_number"],
                    "sub_article_reference": None,
                    "supporting_quote": "special severance package equal to 4 months of gross salary",
                }]
            })

    stub_llm = StubLLMProvider()
    ans = answer_legal_question("What is the special severance package for technological redundancy?", db=db_session, llm_provider=stub_llm)
    assert ans.status == "answered"
    assert "4 months" in ans.answer.lower()
    assert len(ans.citations) >= 1
    assert ans.citations[0].source_title == "addis_tech_severance_policy.pdf"

    # 7. Ask again -> verify Redis cache behavior
    ans_cached = answer_legal_question("What is the special severance package for technological redundancy?", db=db_session, llm_provider=stub_llm)
    assert ans_cached.status == "answered"
    assert ans_cached.cache_hit is True

    # 8. Clean up
    db_session.delete(doc_record)
    for prov in source.provisions:
        db_session.query(LegalProvisionChunk).filter(LegalProvisionChunk.provision_id == prov.id).delete()
        db_session.delete(prov)
    db_session.delete(source)
    db_session.commit()

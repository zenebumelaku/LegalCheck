from datetime import date, datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import (
    LegalProvision,
    LegalProvisionChunk,
    LegalSource,
    User,
)
from app.schemas.legal_retrieval import LegalReviewContext
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    get_embedding_provider,
)
from app.services.legal_chunking import chunk_legal_provision
from app.services.legal_embedding_index import generate_embeddings_for_source
from app.services.legal_retrieval import retrieve_legal_evidence


class SyntheticTestEmbeddingProvider:
    """Explicitly synthetic vectors used only to test ranking behavior."""

    model_name = "synthetic-fixture-model"
    model_version = "fixture-v1"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            normalized = text.lower()
            vector = [0.0] * self.dimensions
            vector[0 if "wage" in normalized or "fixture" in normalized else 1] = 1.0
            vectors.append(vector)
        return vectors


def _add_source(
    db: Session,
    *,
    version: str,
    verification_status: str = "verified",
    legal_status: str = "current",
    effective_date: date | None = date(2020, 1, 1),
    end_date: date | None = None,
    provisions: list[tuple[str, str]],
) -> LegalSource:
    reviewer = db.scalar(select(User).where(User.email == "retrieval-reviewer@example.test"))
    if reviewer is None:
        reviewer = User(
            name="Synthetic Test Reviewer",
            email="retrieval-reviewer@example.test",
            password_hash="test-only",
            role="admin",
        )
        db.add(reviewer)
        db.flush()

    source = LegalSource(
        title=f"Synthetic employment fixture {version}",
        law_number="TEST-FIXTURE-NO-LAW",
        source_type="fixture",
        jurisdiction="ET",
        language="en",
        publication_date=date(2019, 1, 1),
        effective_date=effective_date,
        end_date=end_date,
        legal_status=legal_status,
        version_label=version,
        original_source_url="https://example.test/synthetic-fixture-only.pdf",
        file_checksum=(version.encode().hex() + "0" * 64)[:64],
        source_file_storage_key=f"synthetic-fixtures/{version}.pdf",
        verification_status=verification_status,
        verified_at=datetime.now(timezone.utc) if verification_status == "verified" else None,
        verified_by=reviewer.id if verification_status == "verified" else None,
    )
    source.provisions = [
        LegalProvision(
            article_number=article,
            section_title=f"Synthetic heading {article}",
            text=text,
            page_number=4,
            language="en",
        )
        for article, text in provisions
    ]
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def test_chunking_preserves_article_version_page_and_exception_context(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-v1",
        provisions=[
            (
                "fixture-article",
                (
                    "The synthetic fixture rule establishes a wage calculation. "
                    "Provided that the synthetic exception applies only to this test fixture. "
                    + ("Synthetic supporting text. " * 40)
                ),
            )
        ],
    )
    provision = source.provisions[0]

    chunks = chunk_legal_provision(
        source,
        provision,
        max_characters=300,
        overlap_characters=80,
    )

    assert len(chunks) > 1
    assert all(chunk.source_id == source.id for chunk in chunks)
    assert all(chunk.provision_id == provision.id for chunk in chunks)
    assert all(chunk.article_number == "fixture-article" for chunk in chunks)
    assert all(chunk.version_label == "synthetic-v1" for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)
    rule_and_exception = [
        chunk
        for chunk in chunks
        if "establishes a wage calculation" in chunk.text
        and "Provided that the synthetic exception" in chunk.text
    ]
    assert rule_and_exception


def test_embedding_generation_is_provider_versioned_and_idempotent(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-index-v1",
        provisions=[("fixture-article", "Synthetic fixture wage provision.")],
    )
    provider = SyntheticTestEmbeddingProvider()

    first = generate_embeddings_for_source(db_session, source, provider)
    second = generate_embeddings_for_source(db_session, source, provider)
    second_model_version = SyntheticTestEmbeddingProvider()
    second_model_version.model_version = "fixture-v2"
    regenerated = generate_embeddings_for_source(
        db_session,
        source,
        second_model_version,
    )
    rows = db_session.scalars(
        select(LegalProvisionChunk).where(
            LegalProvisionChunk.provision_id == source.provisions[0].id
        )
    ).all()

    assert first.chunks_created == 1
    assert second.chunks_created == 0
    assert regenerated.chunks_created == 1
    assert {(row.embedding_model, row.embedding_version) for row in rows} == {
        ("synthetic-fixture-model", "fixture-v1"),
        ("synthetic-fixture-model", "fixture-v2"),
    }
    assert all(len(row.embedding) == EMBEDDING_DIMENSIONS for row in rows)
    assert len(provider.calls) == 1


def test_embedding_reindex_refuses_silent_source_content_replacement(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-immutable-index-v1",
        provisions=[("fixture-article", "Synthetic fixture original text.")],
    )
    provider = SyntheticTestEmbeddingProvider()
    generate_embeddings_for_source(db_session, source, provider)
    provision = source.provisions[0]
    provision.text = "Synthetic fixture revised text."
    db_session.commit()

    with pytest.raises(ValueError, match="create a new legal source version"):
        generate_embeddings_for_source(db_session, source, provider)


def test_hybrid_retrieval_combines_article_keyword_and_mock_semantics(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-retrieval-v1",
        provisions=[
            ("17", "Synthetic fixture provision about wage calculations."),
            ("18", "Synthetic fixture provision about leave planning."),
        ],
    )
    provider = SyntheticTestEmbeddingProvider()
    generate_embeddings_for_source(db_session, source, provider)

    response = retrieve_legal_evidence(
        "Article 17 wage",
        LegalReviewContext(
            review_date=date(2024, 5, 1),
            jurisdiction="ET",
            language="en",
        ),
        5,
        db=db_session,
        embedding_provider=provider,
    )

    assert response.results
    result = response.results[0]
    assert result.provision_id == source.provisions[0].id
    assert result.source_id == source.id
    assert result.article_number == "17"
    assert result.source_url == "https://example.test/synthetic-fixture-only.pdf"
    assert result.version_label == "synthetic-retrieval-v1"
    assert result.review_date == date(2024, 5, 1)
    assert result.verification_status == "verified"
    assert result.authoritative is True
    assert result.applicability_uncertain is False
    assert result.retrieval_scores.exact_article == 1.0
    assert result.retrieval_scores.keyword > 0
    assert result.retrieval_scores.semantic > 0


def test_unverified_sources_excluded_by_default_and_unknown_status_retained_as_uncertain(
    db_session: Session,
) -> None:
    verified = _add_source(
        db_session,
        version="synthetic-unknown-status",
        legal_status="unknown",
        effective_date=None,
        provisions=[("fixture-unknown", "Synthetic fixture unknown status text.")],
    )
    _add_source(
        db_session,
        version="synthetic-unverified",
        verification_status="pending",
        legal_status="unknown",
        provisions=[("fixture-pending", "Synthetic fixture pending status text.")],
    )

    response = retrieve_legal_evidence(
        "synthetic fixture",
        LegalReviewContext(jurisdiction="ET"),
        10,
        db=db_session,
        embedding_provider=None,
    )
    included_unverified = retrieve_legal_evidence(
        "synthetic fixture",
        LegalReviewContext(jurisdiction="ET", include_unverified=True),
        10,
        db=db_session,
        embedding_provider=None,
    )

    assert [result.source_id for result in response.results] == [verified.id]
    unknown_result = response.results[0]
    assert unknown_result.legal_status == "unknown"
    assert unknown_result.authoritative is False
    assert unknown_result.applicability_uncertain is True
    assert len(included_unverified.results) == 2
    assert all(
        result.verification_status in {"verified", "pending"}
        for result in included_unverified.results
    )
    assert all(
        not result.authoritative
        for result in included_unverified.results
        if result.verification_status == "pending"
    )


def test_review_date_excludes_versions_outside_stated_effective_period(
    db_session: Session,
) -> None:
    _add_source(
        db_session,
        version="synthetic-expired",
        legal_status="repealed",
        effective_date=date(2010, 1, 1),
        end_date=date(2020, 12, 31),
        provisions=[("fixture-old", "Synthetic fixture historical text.")],
    )
    current = _add_source(
        db_session,
        version="synthetic-review-period",
        provisions=[("fixture-current", "Synthetic fixture review period text.")],
    )

    response = retrieve_legal_evidence(
        "synthetic fixture historical text",
        LegalReviewContext(review_date=date(2024, 1, 1), jurisdiction="ET"),
        10,
        db=db_session,
        embedding_provider=None,
    )

    assert all(result.source_id == current.id for result in response.results)


def test_chunk_rejects_invalid_dimensions_and_mock_is_only_test_provider(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-no-provisions",
        provisions=[("fixture-article", "Synthetic fixture text.")],
    )
    provider = SyntheticTestEmbeddingProvider()
    provider.dimensions -= 1

    with pytest.raises(ValueError, match="requires 384 dimensions"):
        generate_embeddings_for_source(
            db_session,
            source,
            provider,
        )


def test_disabled_embedding_provider_needs_no_external_credentials() -> None:
    assert get_embedding_provider(Settings(embedding_provider="disabled")) is None


def test_embedding_generation_refuses_unverified_sources(db_session: Session) -> None:
    source = _add_source(
        db_session,
        version="synthetic-pending-index",
        verification_status="pending",
        legal_status="unknown",
        provisions=[("fixture-article", "Synthetic fixture pending text.")],
    )

    with pytest.raises(ValueError, match="only for verified"):
        generate_embeddings_for_source(
            db_session,
            source,
            SyntheticTestEmbeddingProvider(),
        )

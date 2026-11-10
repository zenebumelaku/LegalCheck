from datetime import date, datetime, timezone
from typing import Optional

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
from app.services.legal_question_cache import legal_knowledge_base_version
from app.services.legal_embedding_index import (
    LegalEmbeddingIndexingError,
    generate_embeddings_for_source,
)
from app.services.legal_retrieval import _rrf_score, retrieve_legal_evidence
import app.services.legal_reranking as legal_reranking

pytestmark = pytest.mark.unit


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
    effective_date: Optional[date] = date(2020, 1, 1),
    end_date: Optional[date] = None,
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
            sub_article_reference=f"sub-{article}",
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
    assert all(chunk.sub_article_reference == "sub-fixture-article" for chunk in chunks)
    assert all(chunk.heading == "Synthetic heading fixture-article" for chunk in chunks)
    assert all(chunk.version_label == "synthetic-v1" for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)
    assert all("Sub-article sub-fixture-article" in chunk.text for chunk in chunks)
    assert all("Synthetic heading fixture-article" in chunk.text for chunk in chunks)
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
    initial_kb_version = legal_knowledge_base_version(db_session)

    first = generate_embeddings_for_source(db_session, source, provider)
    indexed_kb_version = legal_knowledge_base_version(db_session)
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
    assert first.status == "indexed"
    assert first.source_id == source.id
    assert second.chunks_created == 0
    assert second.status == "unchanged"
    assert regenerated.chunks_created == 1
    assert {(row.embedding_model, row.embedding_version) for row in rows} == {
        ("synthetic-fixture-model", "fixture-v1"),
        ("synthetic-fixture-model", "fixture-v2"),
    }
    assert all(len(row.embedding) == EMBEDDING_DIMENSIONS for row in rows)
    assert all(row.page_number == 4 for row in rows)
    assert all(row.source_version_label == "synthetic-index-v1" for row in rows)
    assert all("Article fixture-article" in row.chunk_text for row in rows)
    assert all("Sub-article sub-fixture-article" in row.chunk_text for row in rows)
    assert all(
        "Synthetic heading fixture-article" in row.chunk_text
        for row in rows
    )
    assert all(row.provision.legal_source_id == source.id for row in rows)
    assert indexed_kb_version != initial_kb_version
    assert len(provider.calls) == 1


def test_indexing_refuses_to_reuse_chunk_when_page_metadata_changed(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-page-metadata-v1",
        provisions=[("fixture-article", "Synthetic fixture indexed text.")],
    )
    provider = SyntheticTestEmbeddingProvider()
    generate_embeddings_for_source(db_session, source, provider)
    provision = source.provisions[0]
    provision.page_number = 5
    db_session.commit()

    with pytest.raises(ValueError, match="Stored chunk metadata"):
        generate_embeddings_for_source(db_session, source, provider)

    chunk = db_session.scalar(
        select(LegalProvisionChunk).where(
            LegalProvisionChunk.provision_id == provision.id
        )
    )
    assert chunk is not None
    assert chunk.page_number == 4
    assert len(provider.calls) == 1


def test_provider_failure_does_not_commit_partial_embedding_chunks(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-provider-failure-v1",
        provisions=[
            ("fixture-article-1", "Synthetic first fixture provision."),
            ("fixture-article-2", "Synthetic second fixture provision."),
        ],
    )

    class FailingProvider(SyntheticTestEmbeddingProvider):
        def __init__(self) -> None:
            super().__init__()
            self.call_count = 0

        def embed(self, texts: list[str]) -> list[list[float]]:
            self.call_count += 1
            if self.call_count == 1:
                return super().embed(texts)
            raise RuntimeError("synthetic provider outage")

    with pytest.raises(LegalEmbeddingIndexingError, match="no new chunk changes"):
        generate_embeddings_for_source(
            db_session,
            source,
            FailingProvider(),
            batch_size=1,
        )

    assert db_session.scalars(
        select(LegalProvisionChunk).where(
            LegalProvisionChunk.provision_id.in_(
                [provision.id for provision in source.provisions]
            )
        )
    ).all() == []

    recovery_provider = SyntheticTestEmbeddingProvider()
    result = generate_embeddings_for_source(db_session, source, recovery_provider)
    assert result.status == "indexed"
    assert result.chunks_created == 2


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


def test_bm25_retrieval_prefers_repeated_shorter_keyword_match(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-bm25-v1",
        provisions=[
            ("bm25-strong", "wage wage wage wage calculation."),
            ("bm25-weak", "wage " + ("unrelated fixture text " * 40)),
        ],
    )

    response = retrieve_legal_evidence(
        "wage",
        LegalReviewContext(jurisdiction="ET"),
        5,
        db=db_session,
        settings=Settings(embedding_provider="disabled", legal_retrieval_mode="hybrid"),
    )

    assert [result.provision_id for result in response.results] == [
        provision.id for provision in source.provisions
    ]
    assert response.results[0].retrieval_scores.keyword > (
        response.results[1].retrieval_scores.keyword
    )


def test_rrf_combines_keyword_and_vector_ranks_and_deduplicates_provisions(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-rrf-v1",
        provisions=[
            (
                "rrf-wage",
                "wage wage wage calculation. " + ("wage support. " * 30),
            ),
            ("rrf-salary", "salary calculation."),
        ],
    )

    class ComplementaryEmbeddingProvider(SyntheticTestEmbeddingProvider):
        def embed(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            return [
                [1.0] + [0.0] * (self.dimensions - 1)
                if text.strip().lower() == "wage" or "salary" in text.lower()
                else [0.0, 1.0] + [0.0] * (self.dimensions - 2)
                for text in texts
            ]

    provider = ComplementaryEmbeddingProvider()
    generate_embeddings_for_source(db_session, source, provider)
    response = retrieve_legal_evidence(
        "wage",
        LegalReviewContext(jurisdiction="ET"),
        5,
        db=db_session,
        embedding_provider=provider,
        settings=Settings(legal_retrieval_mode="hybrid"),
    )

    result_ids = [result.provision_id for result in response.results]
    assert response.results[0].article_number == "rrf-wage"
    assert len(result_ids) == len(set(result_ids))
    assert {result.provision_id for result in response.results} == {
        provision.id for provision in source.provisions
    }


def test_hybrid_retrieval_keeps_keyword_evidence_when_vector_selects_other_chunk(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-mixed-evidence-v1",
        provisions=[
            (
                "mixed-evidence",
                "The employer may deduct amounts for documented damage only. "
                + ("First passage background. " * 80)
                + "\n\n"
                + "Second passage contains unrelated leave details. "
                + ("Unrelated schedule information. " * 80),
            )
        ],
    )

    class MismatchedEmbeddingProvider(SyntheticTestEmbeddingProvider):
        def embed(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(list(texts))
            vectors = []
            for text in texts:
                vector = [0.0] * self.dimensions
                if text.strip() == "employer may deduct amounts" or (
                    "Second passage contains unrelated leave details" in text
                ):
                    vector[0] = 1.0
                else:
                    vector[1] = 1.0
                vectors.append(vector)
            return vectors

    provider = MismatchedEmbeddingProvider()
    generate_embeddings_for_source(db_session, source, provider)
    provision = source.provisions[0]
    chunks = db_session.scalars(
        select(LegalProvisionChunk)
        .where(LegalProvisionChunk.provision_id == provision.id)
        .order_by(LegalProvisionChunk.chunk_index)
    ).all()
    assert len(chunks) == 2
    assert "deduct amounts" in chunks[0].chunk_text
    assert "deduct amounts" not in chunks[1].chunk_text

    response = retrieve_legal_evidence(
        "employer may deduct amounts",
        LegalReviewContext(jurisdiction="ET"),
        5,
        db=db_session,
        embedding_provider=provider,
        settings=Settings(legal_retrieval_mode="hybrid"),
    )

    result = next(item for item in response.results if item.provision_id == provision.id)
    assert result.retrieval_scores.keyword > 0
    assert result.retrieval_scores.semantic > 0
    assert result.chunk_id == chunks[1].id
    assert "The employer may deduct amounts for documented damage only." in result.text


def test_rrf_score_uses_reciprocal_ranks() -> None:
    assert _rrf_score(
        exact_rank=1,
        keyword_rank=2,
        semantic_rank=3,
        offset=60,
    ) == pytest.approx(2 / 61 + 1 / 62 + 1 / 63)


def test_cross_encoder_reranks_candidate_set_and_preserves_metadata(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-rerank-v1",
        provisions=[
            ("rerank-first", "wage wage wage calculation."),
            ("rerank-second", "wage calculation."),
        ],
    )

    class ReverseReranker:
        def rerank(self, query, results):
            assert query == "wage"
            assert len(results) == 2
            return list(reversed(results))

    response = retrieve_legal_evidence(
        "wage",
        LegalReviewContext(jurisdiction="ET"),
        1,
        db=db_session,
        reranker=ReverseReranker(),
        settings=Settings(embedding_provider="disabled"),
    )

    assert response.reranker_applied is True
    assert response.results[0].provision_id == source.provisions[1].id
    assert response.results[0].source_id == source.id
    assert response.results[0].article_number == "rerank-second"
    assert response.results[0].source_url == "https://example.test/synthetic-fixture-only.pdf"


def test_reranker_failure_falls_back_to_fused_order(
    db_session: Session,
) -> None:
    source = _add_source(
        db_session,
        version="synthetic-rerank-fallback-v1",
        provisions=[
            ("fallback-first", "wage wage wage calculation."),
            ("fallback-second", "wage calculation."),
        ],
    )

    class FailingReranker:
        def rerank(self, query, results):
            raise RuntimeError(
                f"synthetic reranker unavailable for {query} ({len(results)} candidates)"
            )

    response = retrieve_legal_evidence(
        "wage",
        LegalReviewContext(jurisdiction="ET"),
        1,
        db=db_session,
        reranker=FailingReranker(),
        settings=Settings(embedding_provider="disabled"),
    )

    assert response.reranker_applied is False
    assert response.results[0].provision_id == source.provisions[0].id


def test_configured_reranker_is_initialized_once(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model_path = tmp_path / "synthetic-cross-encoder"
    model_path.mkdir()
    initializations: list[str] = []

    class SyntheticReranker:
        def __init__(self, path):
            initializations.append(str(path))

        def rerank(self, query, results):
            assert query
            return results

    monkeypatch.setattr(
        legal_reranking,
        "CrossEncoderLegalEvidenceReranker",
        SyntheticReranker,
    )
    settings = Settings(
        legal_reranker_enabled=True,
        legal_reranker_model_path=model_path,
        legal_reranker_model_version="test-single-load-v1",
    )

    first = legal_reranking.get_legal_evidence_reranker(settings)
    second = legal_reranking.get_legal_evidence_reranker(settings)

    assert first is second
    assert initializations == [str(model_path.resolve())]


def test_unavailable_reranker_model_returns_none_without_download(
    tmp_path,
) -> None:
    reranker = legal_reranking.get_legal_evidence_reranker(
        Settings(
            legal_reranker_enabled=True,
            legal_reranker_model_path=tmp_path / "missing-model",
            legal_reranker_model_version="test-missing-v1",
        )
    )

    assert reranker is None


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

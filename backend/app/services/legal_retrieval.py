import math
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional, Protocol
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import Select, func, or_, select, type_coerce
from sqlalchemy.orm import Session

from app.db.models import LegalProvision, LegalProvisionChunk, LegalSource
from app.schemas.legal_retrieval import (
    LegalEvidenceResult,
    LegalRetrievalResponse,
    LegalRetrievalScores,
    LegalReviewContext,
)
from app.services.embeddings import (
    EMBEDDING_DIMENSIONS,
    EmbeddingProvider,
    get_embedding_provider,
    validate_embedding,
)

_ARTICLE_PATTERN = re.compile(r"\b(?:article|art\.?)\s+([0-9]+[a-zA-Z]?(?:\([^)]+\))?)", re.I)
_TOKEN_PATTERN = re.compile(r"[\w'-]+", re.UNICODE)
_RRF_OFFSET = 60
_MAX_CANDIDATES = 250


class LegalEvidenceReranker(Protocol):
    def rerank(
        self,
        query: str,
        results: list[LegalEvidenceResult],
    ) -> list[LegalEvidenceResult]: ...


@dataclass
class _EvidenceCandidate:
    provision: LegalProvision
    source: LegalSource
    text: str
    page_number: Optional[int]
    chunk_id: Optional[UUID] = None
    exact_rank: Optional[int] = None
    keyword_rank: Optional[int] = None
    keyword_score: float = 0.0
    semantic_rank: Optional[int] = None
    semantic_score: float = 0.0
    combined_score: float = 0.0


def _apply_context(
    statement: Select,
    context: LegalReviewContext,
) -> Select:
    statement = statement.where(LegalSource.verification_status != "rejected")
    if not context.include_unverified:
        statement = statement.where(LegalSource.verification_status == "verified")
    if context.jurisdiction:
        statement = statement.where(
            func.lower(LegalSource.jurisdiction) == context.jurisdiction.strip().lower()
        )
    if context.language:
        statement = statement.where(
            func.lower(LegalProvision.language) == context.language.strip().lower()
        )
    if context.source_type:
        statement = statement.where(
            func.lower(LegalSource.source_type) == context.source_type.strip().lower()
        )
    if context.law_number:
        statement = statement.where(
            LegalSource.law_number.ilike(f"%{context.law_number.strip()}%")
        )
    if context.review_date:
        statement = statement.where(
            or_(
                LegalSource.effective_date.is_(None),
                LegalSource.effective_date <= context.review_date,
            ),
            or_(
                LegalSource.end_date.is_(None),
                LegalSource.end_date >= context.review_date,
            ),
        )
    return statement


def _base_query(
    context: LegalReviewContext,
) -> Select:
    return select(LegalProvision, LegalSource).join(
        LegalSource,
        LegalSource.id == LegalProvision.legal_source_id,
    )


def _query_article_number(
    query: str,
    context: LegalReviewContext,
) -> Optional[str]:
    if context.article_number:
        return context.article_number.strip()
    match = _ARTICLE_PATTERN.search(query)
    return match.group(1) if match else None


def _candidate(
    candidates: dict[UUID, _EvidenceCandidate],
    provision: LegalProvision,
    source: LegalSource,
) -> _EvidenceCandidate:
    existing = candidates.get(provision.id)
    if existing is None:
        existing = _EvidenceCandidate(
            provision=provision,
            source=source,
            text=provision.text,
            page_number=provision.page_number,
        )
        candidates[provision.id] = existing
    return existing


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _collect_exact_article(
    db: Session,
    candidates: dict[UUID, _EvidenceCandidate],
    context: LegalReviewContext,
    article_number: Optional[str],
) -> None:
    if not article_number:
        return
    statement = _apply_context(
        _base_query(context).where(LegalProvision.article_number == article_number),
        context,
    ).limit(_MAX_CANDIDATES)
    for provision, source in db.execute(statement):
        candidate = _candidate(candidates, provision, source)
        candidate.exact_rank = 1


def _collect_keyword_matches(
    db: Session,
    candidates: dict[UUID, _EvidenceCandidate],
    context: LegalReviewContext,
    query: str,
) -> None:
    dialect_name = db.get_bind().dialect.name
    base = _base_query(context)
    if dialect_name == "postgresql":
        document = func.to_tsvector("simple", LegalProvision.text)
        query_vector = func.plainto_tsquery("simple", query)
        rank = func.ts_rank_cd(document, query_vector)
        statement = (
            _apply_context(base.where(document.op("@@")(query_vector)), context)
            .add_columns(rank)
            .order_by(rank.desc(), LegalProvision.article_number)
            .limit(_MAX_CANDIDATES)
        )
        for provision, source, score in db.execute(statement):
            candidate = _candidate(candidates, provision, source)
            if candidate.keyword_rank is None:
                candidate.keyword_score = float(score)
    else:
        terms = list(dict.fromkeys(_TOKEN_PATTERN.findall(query.lower())))
        if not terms:
            return
        match_conditions = [
            LegalProvision.text.ilike(f"%{term}%") for term in terms[:12]
        ]
        statement = _apply_context(base.where(or_(*match_conditions)), context).limit(
            _MAX_CANDIDATES
        )
        matches = list(db.execute(statement))
        matches.sort(
            key=lambda pair: sum(
                term in pair[0].text.lower() for term in terms
            ),
            reverse=True,
        )
        for provision, source in matches:
            candidate = _candidate(candidates, provision, source)
            hit_count = sum(term in provision.text.lower() for term in terms)
            candidate.keyword_score = hit_count / len(terms)

    matched = [
        candidate
        for candidate in candidates.values()
        if candidate.keyword_score > 0
        and candidate.keyword_rank is None
    ]
    matched.sort(key=lambda item: item.keyword_score, reverse=True)
    for rank, candidate in enumerate(matched, start=1):
        candidate.keyword_rank = rank


def _collect_semantic_matches(
    db: Session,
    candidates: dict[UUID, _EvidenceCandidate],
    context: LegalReviewContext,
    query: str,
    provider: EmbeddingProvider,
) -> None:
    if provider.dimensions != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Embedding provider must return {EMBEDDING_DIMENSIONS}-dimension vectors."
        )
    query_vectors = provider.embed([query])
    if len(query_vectors) != 1:
        raise ValueError("Embedding provider returned an unexpected vector count.")
    query_embedding = validate_embedding(
        query_vectors[0],
        expected_dimensions=provider.dimensions,
    )
    statement = (
        select(LegalProvisionChunk, LegalProvision, LegalSource)
        .join(
            LegalProvision,
            LegalProvision.id == LegalProvisionChunk.provision_id,
        )
        .join(
            LegalSource,
            LegalSource.id == LegalProvision.legal_source_id,
        )
        .where(
            LegalProvisionChunk.embedding_model == provider.model_name,
            LegalProvisionChunk.embedding_version == provider.model_version,
            LegalProvisionChunk.embedding.is_not(None),
        )
    )
    statement = _apply_context(statement, context)
    if db.get_bind().dialect.name == "postgresql":
        distance = type_coerce(
            LegalProvisionChunk.embedding,
            Vector(EMBEDDING_DIMENSIONS),
        ).cosine_distance(query_embedding)
        rows = db.execute(
            statement.add_columns(distance)
            .order_by(distance.asc())
            .limit(_MAX_CANDIDATES)
        )
        semantic_hits = [
            (chunk, provision, source, 1.0 - float(distance))
            for chunk, provision, source, distance in rows
        ]
    else:
        rows = db.execute(statement.limit(_MAX_CANDIDATES))
        semantic_hits = []
        for chunk, provision, source in rows:
            if chunk.embedding is None:
                continue
            score = _cosine_similarity(query_embedding, chunk.embedding)
            semantic_hits.append((chunk, provision, source, score))
        semantic_hits.sort(key=lambda hit: hit[3], reverse=True)

    for rank, (chunk, provision, source, score) in enumerate(
        semantic_hits[:_MAX_CANDIDATES],
        start=1,
    ):
        candidate = _candidate(candidates, provision, source)
        if candidate.semantic_rank is None or score > candidate.semantic_score:
            candidate.semantic_rank = rank
            candidate.semantic_score = max(-1.0, min(1.0, score))
            candidate.chunk_id = chunk.id
            candidate.text = chunk.chunk_text
            candidate.page_number = chunk.page_number


def _make_results(
    candidates: dict[UUID, _EvidenceCandidate],
    review_context: LegalReviewContext,
) -> list[LegalEvidenceResult]:
    results: list[LegalEvidenceResult] = []
    for candidate in candidates.values():
        source = candidate.source
        combined_score = 0.0
        if candidate.exact_rank is not None:
            combined_score += 2.0 / (_RRF_OFFSET + candidate.exact_rank)
        if candidate.keyword_rank is not None:
            combined_score += 1.0 / (_RRF_OFFSET + candidate.keyword_rank)
        if candidate.semantic_rank is not None:
            combined_score += 1.0 / (_RRF_OFFSET + candidate.semantic_rank)

        status_is_uncertain = source.legal_status != "current"
        date_is_uncertain = source.effective_date is None
        if review_context.review_date is None and source.end_date is not None:
            date_is_uncertain = True
        uncertain = status_is_uncertain or date_is_uncertain
        results.append(
            LegalEvidenceResult(
                provision_id=candidate.provision.id,
                chunk_id=candidate.chunk_id,
                source_id=source.id,
                article_number=candidate.provision.article_number,
                sub_article_reference=candidate.provision.sub_article_reference,
                heading=candidate.provision.section_title,
                text=candidate.text,
                page_number=candidate.page_number,
                source_url=source.original_source_url,
                version_label=source.version_label,
                publication_date=source.publication_date,
                effective_date=source.effective_date,
                end_date=source.end_date,
                review_date=review_context.review_date,
                legal_status=source.legal_status,
                verification_status=source.verification_status,
                authoritative=source.eligible_for_findings,
                applicability_uncertain=uncertain,
                retrieval_scores=LegalRetrievalScores(
                    exact_article=1.0 if candidate.exact_rank is not None else 0.0,
                    keyword=candidate.keyword_score,
                    semantic=candidate.semantic_score,
                    combined=combined_score,
                ),
            )
        )
    return sorted(
        results,
        key=lambda result: (
            result.retrieval_scores.combined,
            result.retrieval_scores.semantic,
            result.article_number,
        ),
        reverse=True,
    )


def retrieve_legal_evidence(
    query: str,
    review_context: Optional[LegalReviewContext] = None,
    top_k: int = 5,
    *,
    db: Session,
    embedding_provider: Optional[EmbeddingProvider] = None,
    reranker: Optional[LegalEvidenceReranker] = None,
) -> LegalRetrievalResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be blank.")
    if top_k < 1 or top_k > 100:
        raise ValueError("top_k must be between 1 and 100.")

    context = review_context or LegalReviewContext()
    candidates: dict[UUID, _EvidenceCandidate] = {}
    article_number = _query_article_number(normalized_query, context)
    _collect_exact_article(db, candidates, context, article_number)
    _collect_keyword_matches(db, candidates, context, normalized_query)

    provider = embedding_provider or get_embedding_provider()
    if provider is not None:
        _collect_semantic_matches(
            db,
            candidates,
            context,
            normalized_query,
            provider,
        )

    results = _make_results(candidates, context)
    if reranker is not None and results:
        results = reranker.rerank(normalized_query, results)
    return LegalRetrievalResponse(
        query=normalized_query,
        review_context=context,
        embedding_model=provider.model_name if provider else None,
        embedding_version=provider.model_version if provider else None,
        results=results[:top_k],
    )

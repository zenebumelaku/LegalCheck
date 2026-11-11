import json
import hashlib
import logging
from datetime import date
from typing import Optional, Protocol
from uuid import UUID

from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import LegalProvision, LegalSource
from app.schemas.citations import CitationReference
from app.schemas.legal_questions import (
    LegalQuestionAnswer,
    LegalQuestionCitation,
    LegalQuestionLLMResponse,
)
from app.schemas.legal_retrieval import LegalEvidenceResult, LegalReviewContext
from app.services.embeddings import EmbeddingProvider
from app.services.legal_question_cache import (
    LegalQuestionCache,
    get_legal_question_cache,
    legal_knowledge_base_version,
    legal_question_cache_key,
    legal_question_cache_metrics,
    normalize_legal_question,
)
from app.services.legal_retrieval import retrieve_legal_evidence
from app.services.llm_provider import (
    LLMProviderError,
    LLMProviderRateLimitError,
    LLMProviderUnavailableError,
    get_llm_provider,
)

logger = logging.getLogger(__name__)

_INSUFFICIENT_ANSWER = (
    "I could not find verified, currently applicable legal evidence that "
    "supports an answer to this question."
)
_INVALID_SUPPORT_ANSWER = (
    "The retrieved evidence did not support a validated answer to this question."
)


class LegalQuestionProviderUnavailable(RuntimeError):
    pass


class LegalQuestionProviderRateLimited(RuntimeError):
    pass


class LegalQuestionProviderFailed(RuntimeError):
    pass


class LegalQuestionLLMProvider(Protocol):
    model_name: str
    model_version: str

    def answer_legal_question(self, question: str, evidence: list[dict]) -> str: ...


def _get_legal_question_provider() -> LegalQuestionLLMProvider:
    settings = get_settings()
    if settings.legal_qa_llm_provider is None:
        return get_llm_provider()
    return get_llm_provider(
        settings.model_copy(update={"llm_provider": settings.legal_qa_llm_provider})
    )


def _evidence_payload(result: LegalEvidenceResult) -> dict:
    return {
        "source_id": str(result.source_id),
        "provision_id": str(result.provision_id),
        "article_number": result.article_number,
        "sub_article_reference": result.sub_article_reference,
        "heading": result.heading,
        "text": result.text,
        "page_number": result.page_number,
        "source_url": result.source_url,
        "version_label": result.version_label,
        "verification_status": result.verification_status,
        "legal_status": result.legal_status,
    }


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _normalize_ref(value: Optional[str]) -> str:
    if not value:
        return ""
    import re
    return re.sub(r"[^0-9a-zA-Z]", "", str(value)).lower().replace("page", "").replace("article", "").replace("section", "")


def _quote_in_text(quote: str, text: str) -> bool:
    if not quote or not text:
        return False
    norm_q = _normalized_text(quote).lower().strip("\"'.,;:")
    norm_t = _normalized_text(text).lower()
    if norm_q in norm_t:
        return True
    words = norm_q.split()
    if len(words) >= 4:
        prefix = " ".join(words[:4])
        if prefix in norm_t:
            return True
        suffix = " ".join(words[-4:])
        if suffix in norm_t:
            return True
    return False


def _result_is_eligible(db: Session, result: LegalEvidenceResult) -> bool:
    source = db.scalar(
        select(LegalSource)
        .where(LegalSource.id == result.source_id)
        .execution_options(populate_existing=True)
    )
    provision = db.scalar(
        select(LegalProvision)
        .where(LegalProvision.id == result.provision_id)
        .execution_options(populate_existing=True)
    )
    if source is None or provision is None:
        return False
    if provision.legal_source_id != source.id:
        return False
    if not result.authoritative or result.applicability_uncertain:
        return False
    if source.legal_status != "current" or not source.eligible_for_findings:
        return False
    if source.verification_status != "verified":
        return False
    return True


def _validate_citations(
    citations: list[CitationReference],
    retrieved: dict[UUID, LegalEvidenceResult],
    db: Session,
    review_date: date,
) -> list[LegalQuestionCitation]:
    validated: list[LegalQuestionCitation] = []
    seen: set[UUID] = set()

    for citation in citations:
        result = retrieved.get(citation.provision_id)
        if result is None:
            continue
        if citation.source_id != result.source_id:
            continue
        if citation.provision_id != result.provision_id:
            continue
        if not _result_is_eligible(db, result):
            continue

        quote_matches = _quote_in_text(citation.supporting_quote, result.text)
        provision = db.scalar(
            select(LegalProvision)
            .where(LegalProvision.id == result.provision_id)
            .execution_options(populate_existing=True)
        )
        if provision is None:
            continue
        art_matches = (
            result.article_number == citation.article_number
            or _normalize_ref(result.article_number) == _normalize_ref(citation.article_number)
            or not citation.article_number
        )
        sub_article_matches = (
            not citation.sub_article_reference
            or citation.sub_article_reference == provision.sub_article_reference
            or _normalize_ref(citation.sub_article_reference)
            == _normalize_ref(provision.sub_article_reference)
        )
        if not quote_matches or not art_matches or not sub_article_matches:
            continue

        source = db.scalar(
            select(LegalSource)
            .where(LegalSource.id == result.source_id)
            .execution_options(populate_existing=True)
        )
        if provision is None or source is None or provision.legal_source_id != source.id:
            continue
        if provision.id in seen:
            continue

        validated.append(
            LegalQuestionCitation(
                source_id=source.id,
                source_title=source.title,
                source_version_label=result.version_label,
                law_number=source.law_number,
                source_url=source.original_source_url,
                provision_id=provision.id,
                article_number=provision.article_number,
                sub_article_reference=citation.sub_article_reference
                or provision.sub_article_reference,
                page_number=result.page_number or provision.page_number,
                supporting_quote=citation.supporting_quote,
            )
        )
        seen.add(provision.id)

    if not validated and citations:
        raise ValueError("None of the citations matched eligible retrieved evidence.")

    return validated


def answer_legal_question(
    question: str,
    review_context: Optional[LegalReviewContext] = None,
    *,
    db: Session,
    llm_provider: Optional[LegalQuestionLLMProvider] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    answer_cache: Optional[LegalQuestionCache] = None,
    settings: Optional[Settings] = None,
    top_k: Optional[int] = None,
    generation_context: Optional[str] = None,
    cache_scope: Optional[str] = None,
) -> LegalQuestionAnswer:
    current_settings = settings or get_settings()
    answer_top_k = top_k if top_k is not None else current_settings.legal_qa_top_k
    normalized_question = normalize_legal_question(question)
    if not normalized_question:
        raise ValueError("question must not be blank.")
    if generation_context and not cache_scope:
        raise ValueError(
            "Private conversation context requires a scoped answer cache key."
        )
    review_date = (review_context.review_date if review_context else None) or date.today()
    context = (review_context or LegalReviewContext()).model_copy(
        update={"review_date": review_date, "include_unverified": False}
    )
    if not 1 <= answer_top_k <= 100:
        raise ValueError("top_k must be between 1 and 100.")

    cache_available = False
    cache = answer_cache
    cache_key: Optional[str] = None
    if current_settings.legal_qa_cache_ttl_seconds > 0:
        try:
            cache = cache or get_legal_question_cache()
            knowledge_base_version = legal_knowledge_base_version(db)
            legal_question_cache_metrics.observe_knowledge_base_version(
                knowledge_base_version
            )
            cache_key = legal_question_cache_key(
                question=normalized_question,
                context={
                    "review_context": context.model_dump(mode="json"),
                    "top_k": answer_top_k,
                    "cache_scope": cache_scope,
                    "private_context_digest": (
                        hashlib.sha256(generation_context.encode("utf-8")).hexdigest()
                        if generation_context
                        else None
                    ),
                },
                knowledge_base_version=knowledge_base_version,
                settings=current_settings,
            )
            cached_answer = cache.get(cache_key)
            cache_available = True
            if cached_answer is not None:
                legal_question_cache_metrics.record("hits")
                legal_question_cache_metrics.record("provider_calls_avoided")
                return cached_answer.model_copy(
                    update={"question": normalized_question, "cache_hit": True}
                )
            legal_question_cache_metrics.record("misses")
        except RedisError as exc:
            legal_question_cache_metrics.record("errors")
            logger.warning(
                "Legal-question answer cache is unavailable; continuing without cache",
                extra={"error_type": type(exc).__name__},
            )

    contextual_question = (
        f"{generation_context}\n\nCurrent question: {normalized_question}"
        if generation_context
        else normalized_question
    )
    retrieval = retrieve_legal_evidence(
        contextual_question,
        context,
        current_settings.legal_retrieval_candidate_k,
        db=db,
        embedding_provider=embedding_provider,
        settings=current_settings,
    )
    eligible_results = [
        result
        for result in retrieval.results
        if result.authoritative and not result.applicability_uncertain
    ][:answer_top_k]

    if not eligible_results:
        return LegalQuestionAnswer(
            status="insufficient_evidence",
            question=normalized_question,
            answer=_INSUFFICIENT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=None,
            model_version=None,
        )

    try:
        provider = llm_provider or _get_legal_question_provider()
    except LLMProviderError as exc:
        raise LegalQuestionProviderUnavailable(
            f"AI answer generation is unavailable: {exc}"
        ) from exc

    try:
        legal_question_cache_metrics.record("provider_calls")
        raw_response = provider.answer_legal_question(
            contextual_question,
            [_evidence_payload(result) for result in eligible_results],
        )
    except LLMProviderUnavailableError as exc:
        raise LegalQuestionProviderUnavailable(
            f"The configured AI provider is unavailable: {exc}"
        ) from exc
    except LLMProviderRateLimitError as exc:
        raise LegalQuestionProviderRateLimited(
            "The configured AI provider rate limit was reached; retry later."
        ) from exc
    except LLMProviderError as exc:
        logger.warning(
            "Legal question answer generation failed",
            extra={"error_type": type(exc).__name__},
        )
        raise LegalQuestionProviderFailed(
            "The AI provider could not produce a valid legal-question response."
        ) from exc

    try:
        parsed = LegalQuestionLLMResponse.model_validate(json.loads(raw_response))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        logger.warning(
            "Legal question answer generation failed",
            extra={"error_type": type(exc).__name__},
        )
        raise LegalQuestionProviderFailed(
            "The AI provider could not produce a valid legal-question response."
        ) from exc

    if parsed.evidence_assessment != "supporting" or not parsed.citations:
        return LegalQuestionAnswer(
            status="insufficient_evidence",
            question=normalized_question,
            answer=_INVALID_SUPPORT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=provider.model_name,
            model_version=provider.model_version,
        )

    if not all(_result_is_eligible(db, result) for result in eligible_results):
        return LegalQuestionAnswer(
            status="insufficient_evidence",
            question=normalized_question,
            answer=_INVALID_SUPPORT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=provider.model_name,
            model_version=provider.model_version,
        )

    try:
        citations = _validate_citations(
            parsed.citations,
            {result.provision_id: result for result in eligible_results},
            db,
            review_date,
        )
    except ValueError as exc:
        logger.warning(
            "Legal question answer included an invalid citation",
            extra={"error_type": type(exc).__name__},
        )
        return LegalQuestionAnswer(
            status="insufficient_evidence",
            question=normalized_question,
            answer=_INVALID_SUPPORT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=provider.model_name,
            model_version=provider.model_version,
        )

    answer = LegalQuestionAnswer(
        status="answered",
        question=normalized_question,
        answer=parsed.answer,
        review_date=review_date,
        citations=citations,
        model_name=provider.model_name,
        model_version=provider.model_version,
    )
    if cache_available and cache is not None and cache_key is not None:
        try:
            cache.set(
                cache_key,
                answer,
                current_settings.legal_qa_cache_ttl_seconds,
            )
        except RedisError as exc:
            legal_question_cache_metrics.record("errors")
            logger.warning(
                "Legal-question answer could not be cached",
                extra={"error_type": type(exc).__name__},
            )
    return answer

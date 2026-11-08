import json
import logging
from datetime import date
from typing import Optional, Protocol
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LegalProvision, LegalSource
from app.schemas.compliance_analysis import CitationReference
from app.schemas.legal_questions import (
    LegalQuestionAnswer,
    LegalQuestionCitation,
    LegalQuestionLLMResponse,
)
from app.schemas.legal_retrieval import LegalEvidenceResult, LegalReviewContext
from app.services.embeddings import EmbeddingProvider
from app.services.legal_retrieval import retrieve_legal_evidence
from app.services.llm_provider import LLMProviderError, get_llm_provider

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


class LegalQuestionProviderFailed(RuntimeError):
    pass


class LegalQuestionLLMProvider(Protocol):
    model_name: str
    model_version: str

    def answer_legal_question(self, question: str, evidence: list[dict]) -> str: ...


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
        if (
            result is None
            or result.source_id != citation.source_id
            or result.article_number != citation.article_number
            or result.sub_article_reference != citation.sub_article_reference
            or not result.authoritative
            or result.applicability_uncertain
            or _normalized_text(citation.supporting_quote)
            not in _normalized_text(result.text)
        ):
            raise ValueError("Citation does not match eligible retrieved evidence.")

        provision = db.scalar(
            select(LegalProvision)
            .where(LegalProvision.id == citation.provision_id)
            .execution_options(populate_existing=True)
        )
        source = db.scalar(
            select(LegalSource)
            .where(LegalSource.id == citation.source_id)
            .execution_options(populate_existing=True)
        )
        if (
            provision is None
            or source is None
            or provision.legal_source_id != source.id
            or provision.article_number != citation.article_number
            or provision.sub_article_reference != citation.sub_article_reference
            or _normalized_text(citation.supporting_quote)
            not in _normalized_text(provision.text)
            or not source.eligible_for_findings
            or source.verification_status != "verified"
            or source.legal_status != "current"
            or source.effective_date is None
            or source.effective_date > review_date
            or (source.end_date is not None and source.end_date < review_date)
        ):
            raise ValueError("Citation source or provision is not eligible.")

        if provision.id in seen:
            continue
        validated.append(
            LegalQuestionCitation(
                source_id=source.id,
                source_title=source.title,
                law_number=source.law_number,
                source_url=source.original_source_url,
                provision_id=provision.id,
                article_number=provision.article_number,
                sub_article_reference=provision.sub_article_reference,
                page_number=result.page_number or provision.page_number,
                supporting_quote=citation.supporting_quote,
            )
        )
        seen.add(provision.id)

    return validated


def answer_legal_question(
    question: str,
    review_context: Optional[LegalReviewContext] = None,
    *,
    db: Session,
    llm_provider: Optional[LegalQuestionLLMProvider] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    top_k: int = 5,
) -> LegalQuestionAnswer:
    review_date = (review_context.review_date if review_context else None) or date.today()
    context = (review_context or LegalReviewContext()).model_copy(
        update={"review_date": review_date, "include_unverified": False}
    )
    if not 1 <= top_k <= 100:
        raise ValueError("top_k must be between 1 and 100.")
    retrieval = retrieve_legal_evidence(
        question,
        context,
        100,
        db=db,
        embedding_provider=embedding_provider,
    )
    eligible_results = [
        result
        for result in retrieval.results
        if result.authoritative and not result.applicability_uncertain
    ][:top_k]

    if not eligible_results:
        return LegalQuestionAnswer(
            status="insufficient_evidence",
            question=question,
            answer=_INSUFFICIENT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=None,
            model_version=None,
        )

    try:
        provider = llm_provider or get_llm_provider()
    except LLMProviderError as exc:
        raise LegalQuestionProviderUnavailable(
            "AI answer generation is unavailable. Configure an LLM provider and try again."
        ) from exc

    try:
        raw_response = provider.answer_legal_question(
            question,
            [_evidence_payload(result) for result in eligible_results],
        )
        parsed = LegalQuestionLLMResponse.model_validate(json.loads(raw_response))
    except (LLMProviderError, json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
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
            question=question,
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
            question=question,
            answer=_INVALID_SUPPORT_ANSWER,
            review_date=review_date,
            citations=[],
            model_name=provider.model_name,
            model_version=provider.model_version,
        )

    return LegalQuestionAnswer(
        status="answered",
        question=question,
        answer=parsed.answer,
        review_date=review_date,
        citations=citations,
        model_name=provider.model_name,
        model_version=provider.model_version,
    )

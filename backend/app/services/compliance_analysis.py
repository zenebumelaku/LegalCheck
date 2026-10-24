import json
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import (
    Audit,
    Document,
    Finding,
    FindingCitation,
    LegalProvision,
    LegalSource,
)
from app.schemas.compliance_analysis import (
    AnalysisLimitations,
    CitationReference,
    ComplianceFinding,
    ExtractedClause,
    FinalAuditAnalysis,
    LLMClauseAnalysis,
    SupportingEvidence,
)
from app.schemas.legal_retrieval import LegalEvidenceResult, LegalReviewContext
from app.services.document_extraction import ExtractedPage, extract_document
from app.services.legal_retrieval import retrieve_legal_evidence
from app.services.llm_provider import LLMProvider, LLMProviderError, get_llm_provider
from app.storage.interface import PrivateFileStorage

logger = logging.getLogger(__name__)

_CLAUSE_TERMS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "duration",
        re.compile(r"\b(duration|fixed[- ]term|term of employment|contract period)\b", re.I),
    ),
    (
        "compensation",
        re.compile(r"\b(salary|wage|remuneration|compensation|allowance|payable)\b", re.I),
    ),
    (
        "working_hours",
        re.compile(r"\b(working hours?|work hours?|overtime|weekly hours?|shift)\b", re.I),
    ),
    (
        "leave",
        re.compile(r"\b(leave|annual leave|sick leave|maternity|holiday)\b", re.I),
    ),
    ("probation", re.compile(r"\bprobation(?:ary)?\b", re.I)),
    ("termination", re.compile(r"\b(termination|terminate|dismissal|dismiss)\b", re.I)),
    ("notice", re.compile(r"\bnotice period\b|\bnotice of termination\b", re.I)),
    (
        "confidentiality",
        re.compile(r"\b(confidentiality|confidential|non[- ]disclosure)\b", re.I),
    ),
    (
        "signatures",
        re.compile(r"\b(signature|signed by|signing date|witness signature)\b", re.I),
    ),
)
_UNSUPPORTED_EXPLANATION = (
    "The model's legal conclusion was not retained because its evidence could "
    "not be independently validated as authoritative and applicable."
)
_UNCALIBRATED_CONFIDENCE_LIMITATION = (
    "Model confidence, when present, is uncalibrated self-assessment and is "
    "not a probability of legal correctness."
)


class ComplianceAnalysisError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def extract_candidate_clauses(pages: list[ExtractedPage]) -> list[ExtractedClause]:
    clauses: list[ExtractedClause] = []
    seen: set[tuple[str, str, Optional[int], Optional[int]]] = set()
    for page in pages:
        for paragraph in page.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            for category, matcher in _CLAUSE_TERMS:
                if not matcher.search(text):
                    continue
                key = (category, text, page.page_number, paragraph.paragraph_number)
                if key in seen:
                    continue
                seen.add(key)
                clauses.append(
                    ExtractedClause(
                        clause_id=f"clause-{len(clauses) + 1}",
                        category=category,
                        original_text=text,
                        page_number=page.page_number,
                        paragraph_number=paragraph.paragraph_number,
                    )
                )
    return clauses


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


def _validate_citations(
    citations: list[CitationReference],
    retrieved: dict[UUID, LegalEvidenceResult],
    db: Session,
) -> list[tuple[CitationReference, LegalProvision]]:
    validated: list[tuple[CitationReference, LegalProvision]] = []
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
        ):
            raise ValueError("Citation is not an authoritative retrieved provision.")
        provision = db.get(LegalProvision, citation.provision_id)
        if (
            provision is None
            or provision.legal_source_id != citation.source_id
            or provision.article_number != citation.article_number
            or provision.sub_article_reference != citation.sub_article_reference
        ):
            raise ValueError("Citation does not match the saved provision.")
        source = db.get(LegalSource, citation.source_id)
        if source is None or not source.eligible_for_findings:
            raise ValueError("Citation source is not eligible for findings.")
        if _normalized_text(citation.supporting_quote) not in _normalized_text(provision.text):
            raise ValueError("Citation quotation does not match the saved provision.")
        if provision.id not in seen:
            validated.append((citation, provision))
            seen.add(provision.id)
    return validated


def _review_context(audit: Audit, review_date: date) -> LegalReviewContext:
    options = audit.review_options or {}
    configured_date = options.get("review_date")
    if configured_date:
        review_date = date.fromisoformat(configured_date)
    return LegalReviewContext(
        review_date=review_date,
        jurisdiction=options.get("jurisdiction", "ET"),
        language=options.get("language"),
        source_type=options.get("source_type"),
        law_number=options.get("law_number"),
    )


def _evidence_payload(result: LegalEvidenceResult) -> dict:
    return {
        "source_id": str(result.source_id),
        "provision_id": str(result.provision_id),
        "article_number": result.article_number,
        "sub_article_reference": result.sub_article_reference,
        "heading": result.heading,
        "text": result.text,
        "source_url": result.source_url,
        "version_label": result.version_label,
        "verification_status": result.verification_status,
        "legal_status": result.legal_status,
        "authoritative": result.authoritative,
        "applicability_uncertain": result.applicability_uncertain,
    }


def _make_uncertain(parsed: LLMClauseAnalysis) -> LLMClauseAnalysis:
    return parsed.model_copy(
        update={
            "category": "insufficient_evidence",
            "severity": "informational",
            "explanation": _UNSUPPORTED_EXPLANATION,
            "recommended_action": (
                "Have a qualified Ethiopian legal professional verify the "
                "applicable law and source version."
            ),
            "evidence_assessment": "insufficient",
            "citations": [],
        }
    )


def _persist_finding(
    db: Session,
    audit: Audit,
    clause: ExtractedClause,
    parsed: LLMClauseAnalysis,
    validated: list[tuple[CitationReference, LegalProvision]],
) -> ComplianceFinding:
    evidence_status = "supported" if validated else "unverified"
    finding = Finding(
        audit_id=audit.id,
        finding_type=f"{parsed.category}:{clause.category}",
        severity=parsed.severity,
        # The legacy column is not populated: the model score is uncalibrated,
        # and must not be exposed as a probability of legal correctness.
        confidence=None,
        clause_text=clause.original_text,
        explanation=parsed.explanation,
        recommended_action=parsed.recommended_action,
        evidence_status=evidence_status,
    )
    db.add(finding)
    db.flush()
    for citation, provision in validated:
        db.add(
            FindingCitation(
                finding_id=finding.id,
                legal_provision_id=provision.id,
                supporting_quote=citation.supporting_quote,
                relevance_information=parsed.category,
            )
        )
    return ComplianceFinding(
        category=parsed.category,
        severity=parsed.severity,
        clause_id=clause.clause_id,
        clause_text=clause.original_text,
        explanation=parsed.explanation,
        recommended_action=parsed.recommended_action,
        evidence_assessment=parsed.evidence_assessment,
        citations=parsed.citations,
        model_confidence=parsed.model_confidence,
    )


def _mark_failed(db: Session, audit_id: UUID, code: str) -> None:
    db.rollback()
    failed_audit = db.get(Audit, audit_id)
    if failed_audit is None:
        return
    failed_audit.audit_status = "failed"
    failed_audit.completed_at = None
    failed_audit.failure_code = code
    failed_audit.failure_message = (
        "The analysis could not be completed. No completed legal review was produced."
    )
    db.commit()


def analyze_audit(
    audit_id: UUID,
    *,
    db: Session,
    storage: PrivateFileStorage,
    llm_provider: Optional[LLMProvider] = None,
) -> FinalAuditAnalysis:
    audit = db.get(Audit, audit_id)
    if audit is None:
        raise ComplianceAnalysisError("audit_not_found", "Audit was not found.")
    if audit.audit_status not in {"pending", "processing"}:
        raise ComplianceAnalysisError("audit_not_pending", "Audit is not pending analysis.")
    audit.audit_status = "processing"
    audit.started_at = datetime.now(timezone.utc)
    audit.failure_code = None
    audit.failure_message = None
    audit.model_identifier = None
    audit.analysis_version = "1"
    db.commit()

    try:
        provider = llm_provider or get_llm_provider()
        audit.model_identifier = f"{provider.model_name}:{provider.model_version}"
        db.commit()
        document = db.get(Document, audit.document_id)
        if document is None or document.deleted_at is not None:
            raise ValueError("Document is unavailable for analysis.")
        content = storage.read(document.storage_key)
        settings = get_settings()
        extraction = extract_document(
            content,
            document.document_type or "",
            settings.max_docx_uncompressed_size_bytes,
            ocr_enabled=settings.ocr_enabled,
        )
        if extraction.extracted_characters > settings.max_contract_analysis_characters:
            raise ValueError("Extracted contract exceeds configured analysis limits.")

        clauses = extract_candidate_clauses(extraction.pages)
        review_date = date.today()
        context = _review_context(audit, review_date)
        review_date = context.review_date or review_date
        output_findings: list[ComplianceFinding] = []
        output_evidence: list[SupportingEvidence] = []

        for clause in clauses:
            retrieval = retrieve_legal_evidence(
                clause.original_text,
                context,
                top_k=5,
                db=db,
            )
            retrieved = {result.provision_id: result for result in retrieval.results}
            output_evidence.extend(
                SupportingEvidence(
                    clause_id=clause.clause_id,
                    source_id=result.source_id,
                    provision_id=result.provision_id,
                    article_number=result.article_number,
                    sub_article_reference=result.sub_article_reference,
                    heading=result.heading,
                    source_url=result.source_url,
                    version_label=result.version_label,
                    verification_status=result.verification_status,
                    legal_status=result.legal_status,
                    page_number=result.page_number,
                    text=result.text,
                    retrieval_scores=result.retrieval_scores.model_dump(),
                )
                for result in retrieval.results
            )
            try:
                raw_response = provider.analyze_clause(
                    clause.model_dump(mode="json"),
                    [_evidence_payload(result) for result in retrieval.results],
                )
                parsed = LLMClauseAnalysis.model_validate(json.loads(raw_response))
            except (LLMProviderError, TypeError, ValueError) as exc:
                raise LLMProviderError(
                    "The configured analysis provider returned an invalid response."
                ) from exc

            validated: list[tuple[CitationReference, LegalProvision]] = []
            try:
                validated = _validate_citations(parsed.citations, retrieved, db)
            except ValueError:
                parsed = _make_uncertain(parsed)

            has_authoritative_evidence = any(
                item.authoritative and not item.applicability_uncertain
                for item in retrieval.results
            )
            if (
                parsed.evidence_assessment != "supporting"
                or not has_authoritative_evidence
                or (parsed.category != "informational_observation" and not validated)
            ):
                parsed = _make_uncertain(parsed)
                validated = []
            output_findings.append(
                _persist_finding(db, audit, clause, parsed, validated)
            )

        db.flush()
        audit.audit_status = "completed"
        audit.completed_at = datetime.now(timezone.utc)
        audit.failure_code = None
        audit.failure_message = None
        limitations = list(extraction.warnings)
        limitations.append(
            "Clause extraction uses English keyword patterns and may miss clauses, "
            "including clauses written in other languages or unusual wording."
        )
        limitations.append(_UNCALIBRATED_CONFIDENCE_LIMITATION)
        limitations.append(
            "No deterministic Ethiopian employment-law checks are enabled because "
            "no verified, versioned rule set is configured."
        )
        if not clauses:
            limitations.append(
                "No clauses in the configured categories were detected; this does "
                "not mean the document contains none."
            )
        result = FinalAuditAnalysis(
            audit_id=audit.id,
            document_id=document.id,
            analysis_status="completed",
            clauses=clauses,
            findings=output_findings,
            supporting_evidence=output_evidence,
            limitations=AnalysisLimitations(items=limitations),
            model_name=provider.model_name,
            model_version=provider.model_version,
            review_date=review_date,
        )
        db.commit()
        return result
    except (LLMProviderError, OSError, TypeError, ValueError, SQLAlchemyError) as exc:
        failure_code = (
            "llm_provider_failure"
            if isinstance(exc, LLMProviderError)
            else "analysis_failed"
        )
        try:
            _mark_failed(db, audit_id, failure_code)
        except SQLAlchemyError:
            logger.exception("Could not persist failed audit status for audit %s", audit_id)
        logger.warning(
            "Compliance analysis failed for audit %s with code %s",
            audit_id,
            failure_code,
        )
        raise ComplianceAnalysisError(
            failure_code,
            "The analysis could not be completed. No completed legal review was produced.",
        ) from exc

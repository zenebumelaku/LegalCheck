from datetime import date
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ClauseCategory = Literal[
    "duration",
    "compensation",
    "working_hours",
    "leave",
    "probation",
    "termination",
    "notice",
    "confidentiality",
    "signatures",
]
FindingCategory = Literal[
    "potential_legal_conflict",
    "missing_information",
    "ambiguous_clause",
    "outdated_legal_reference",
    "informational_observation",
    "insufficient_evidence",
]
Severity = Literal["informational", "low", "medium", "high", "critical"]
EvidenceAssessment = Literal["supporting", "contradictory", "insufficient"]


class ExtractedClause(BaseModel):
    clause_id: str
    category: ClauseCategory
    original_text: str
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None


class CitationReference(BaseModel):
    source_id: UUID
    provision_id: UUID
    article_number: str
    sub_article_reference: Optional[str] = None
    supporting_quote: str = Field(min_length=1, max_length=5000)


class SupportingEvidence(BaseModel):
    clause_id: str
    source_id: UUID
    provision_id: UUID
    article_number: str
    sub_article_reference: Optional[str]
    heading: Optional[str]
    source_url: Optional[str]
    version_label: Optional[str]
    verification_status: str
    legal_status: str
    page_number: Optional[int]
    text: str
    retrieval_scores: dict[str, float]


class ComplianceFinding(BaseModel):
    category: FindingCategory
    severity: Severity
    clause_id: str
    clause_text: str
    explanation: str = Field(min_length=1, max_length=10_000)
    recommended_action: Optional[str] = Field(default=None, max_length=10_000)
    evidence_assessment: EvidenceAssessment
    citations: list[CitationReference] = Field(default_factory=list, max_length=20)
    model_confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)


class AnalysisLimitations(BaseModel):
    items: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "This AI-assisted review is not legal advice and does not determine "
        "legal compliance. Have a qualified Ethiopian legal professional "
        "review the contract and cited sources."
    )


class FinalAuditAnalysis(BaseModel):
    audit_id: UUID
    document_id: UUID
    analysis_status: Literal["completed", "failed"]
    clauses: list[ExtractedClause]
    findings: list[ComplianceFinding]
    supporting_evidence: list[SupportingEvidence]
    limitations: AnalysisLimitations
    model_name: Optional[str]
    model_version: Optional[str]
    review_date: date


class LLMClauseAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: FindingCategory
    severity: Severity
    explanation: str = Field(min_length=1, max_length=10_000)
    recommended_action: Optional[str] = Field(default=None, max_length=10_000)
    evidence_assessment: EvidenceAssessment
    citations: list[CitationReference] = Field(default_factory=list, max_length=20)
    model_confidence: Optional[Decimal] = Field(default=None, ge=0, le=1)

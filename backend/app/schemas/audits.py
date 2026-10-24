from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.compliance_analysis import AnalysisLimitations, ComplianceFinding

AuditState = Literal[
    "queued",
    "extracting",
    "retrieving_sources",
    "analyzing",
    "generating_report",
    "completed",
    "failed",
]


class AuditReviewOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_date: Optional[date] = None
    jurisdiction: Literal["ET"] = "ET"
    language: Optional[str] = Field(default=None, max_length=50)
    source_type: Optional[str] = Field(default=None, max_length=100)
    law_number: Optional[str] = Field(default=None, max_length=100)


class AuditCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: UUID
    review_options: AuditReviewOptions = Field(default_factory=AuditReviewOptions)


class AuditResponse(BaseModel):
    id: UUID
    document_id: UUID
    audit_status: AuditState
    review_options: AuditReviewOptions
    processing_warnings: list[str]
    analysis_version: Optional[str]
    model_identifier: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failure_code: Optional[str]
    failure_message: Optional[str]
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditResponse]
    limit: int
    offset: int


class AuditStatusResponse(BaseModel):
    audit_id: UUID
    status: AuditState
    processing_warnings: list[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    failure_code: Optional[str]
    failure_message: Optional[str]


class AuditFindingCitation(BaseModel):
    source_id: UUID
    source_title: str
    source_url: Optional[str]
    version_label: Optional[str]
    article_number: str
    sub_article_reference: Optional[str]
    supporting_quote: Optional[str]
    relevance_information: Optional[str]


class AuditFindingResponse(ComplianceFinding):
    id: UUID
    citations: list[AuditFindingCitation]
    created_at: datetime


class AuditFindingsResponse(BaseModel):
    audit_id: UUID
    findings: list[AuditFindingResponse]
    limitations: AnalysisLimitations


class AuditReportDocument(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    document_type: Optional[str]
    file_size: int
    detected_language: Optional[str]
    created_at: datetime


class AuditReportCitation(BaseModel):
    source_id: UUID
    provision_id: UUID
    source_title: str
    source_version: Optional[str]
    source_url: Optional[str]
    article_number: str
    sub_article_reference: Optional[str]
    provision_text: str
    supporting_quote: Optional[str]
    relevance_information: Optional[str]


class AuditReportFinding(BaseModel):
    id: UUID
    finding_type: str
    severity: str
    clause_excerpt: str
    explanation: str
    recommended_next_steps: Optional[str]
    evidence_status: str
    citations: list[AuditReportCitation]
    created_at: datetime


class AuditReportSummary(BaseModel):
    finding_count: int
    severity_counts: dict[str, int]
    finding_type_counts: dict[str, int]


class AuditReportResponse(BaseModel):
    audit_id: UUID
    audit_created_at: datetime
    audit_completed_at: datetime
    document: AuditReportDocument
    review_scope: AuditReviewOptions
    analysis_version: Optional[str]
    model_identifier: Optional[str]
    summary: AuditReportSummary
    findings: list[AuditReportFinding]
    processing_warnings: list[str]
    limitations: AnalysisLimitations


FeedbackType = Literal[
    "incorrect_finding",
    "incorrect_citation",
    "missing_issue",
    "other",
]


class FindingFeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_type: FeedbackType
    description: Optional[str] = Field(default=None, max_length=5000)

    @model_validator(mode="after")
    def require_other_description(self) -> "FindingFeedbackCreate":
        if self.feedback_type == "other" and not (self.description or "").strip():
            raise ValueError("A description is required for 'other' feedback.")
        return self


class FindingFeedbackResponse(BaseModel):
    id: UUID
    finding_id: UUID
    feedback_type: FeedbackType
    description: Optional[str]
    created_at: datetime

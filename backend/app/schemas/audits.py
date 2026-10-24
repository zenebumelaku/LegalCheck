from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    jurisdiction: str = Field(default="ET", min_length=1, max_length=200)
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

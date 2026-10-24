from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
)


LegalStatus = Literal["unknown", "current", "amended", "repealed", "superseded"]
VerificationStatus = Literal["unverified", "pending", "verified", "rejected"]


class LegalSourceIngestionMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=500)
    law_number: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=100)
    jurisdiction: str = Field(min_length=1, max_length=200)
    language: str = Field(min_length=1, max_length=50)
    publication_date: Optional[date] = None
    effective_date: Optional[date] = None
    end_date: Optional[date] = None
    version_label: str = Field(min_length=1, max_length=100)
    original_source_url: AnyHttpUrl

    @field_validator(
        "title",
        "law_number",
        "source_type",
        "jurisdiction",
        "language",
        "version_label",
    )
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value must not be blank.")
        return normalized


class LegalProvisionIngestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_number: str = Field(min_length=1, max_length=100)
    sub_article_reference: Optional[str] = Field(default=None, max_length=100)
    section_title: Optional[str] = Field(default=None, max_length=500)
    text: str = Field(min_length=1, max_length=100_000)
    page_number: Optional[int] = Field(default=None, gt=0)
    language: Optional[str] = Field(default=None, min_length=1, max_length=50)

    @field_validator("article_number", "sub_article_reference", "section_title", "language")
    @classmethod
    def trim_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("This value must not be blank.")
        return normalized

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Provision text must not be blank.")
        return normalized


class LegalSourceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["verified", "rejected"]
    legal_status: LegalStatus = "unknown"
    verification_notes: str = Field(min_length=10, max_length=10_000)

    @field_validator("verification_notes")
    @classmethod
    def trim_notes(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 10:
            raise ValueError("Review notes must contain at least 10 characters.")
        return normalized


class LegalSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    law_number: Optional[str]
    source_type: str
    jurisdiction: str
    language: str
    publication_date: Optional[date]
    effective_date: Optional[date]
    end_date: Optional[date]
    legal_status: str
    version_label: Optional[str]
    original_source_url: Optional[str]
    file_checksum: Optional[str]
    source_file_storage_key: Optional[str] = Field(default=None, exclude=True)
    verification_status: str
    verified_at: Optional[datetime]
    ingested_by: Optional[UUID]
    verified_by: Optional[UUID]
    verification_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def eligible_for_findings(self) -> bool:
        return (
            self.verification_status == "verified"
            and self.legal_status == "current"
            and self.file_checksum is not None
            and self.source_file_storage_key is not None
            and self.verified_by is not None
            and self.verified_at is not None
            and self.original_source_url is not None
        )


class LegalProvisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    legal_source_id: UUID
    article_number: str
    sub_article_reference: Optional[str]
    section_title: Optional[str]
    text: str
    page_number: Optional[int]
    language: str
    metadata: dict = Field(validation_alias="metadata_json")


class LegalSourcePage(BaseModel):
    items: list[LegalSourceResponse]
    limit: int
    offset: int
    total: int


class LegalProvisionPage(BaseModel):
    items: list[LegalProvisionResponse]
    limit: int
    offset: int
    total: int


class LegalSourceIngestionResponse(BaseModel):
    source: LegalSourceResponse
    provisions_created: int

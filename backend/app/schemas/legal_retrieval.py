from datetime import date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LegalReviewContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_date: Optional[date] = None
    jurisdiction: Optional[str] = "ET"
    language: Optional[str] = None
    source_type: Optional[str] = None
    law_number: Optional[str] = None
    article_number: Optional[str] = None
    include_unverified: bool = False


class LegalRetrievalScores(BaseModel):
    exact_article: float = 0.0
    keyword: float = 0.0
    semantic: float = 0.0
    combined: float = 0.0


class LegalEvidenceResult(BaseModel):
    provision_id: UUID
    chunk_id: Optional[UUID]
    source_id: UUID
    article_number: str
    sub_article_reference: Optional[str]
    heading: Optional[str]
    text: str
    page_number: Optional[int]
    source_url: Optional[str]
    version_label: Optional[str]
    publication_date: Optional[date]
    effective_date: Optional[date]
    end_date: Optional[date]
    review_date: Optional[date]
    legal_status: str
    verification_status: str
    authoritative: bool
    applicability_uncertain: bool
    retrieval_scores: LegalRetrievalScores


class LegalRetrievalResponse(BaseModel):
    query: str
    review_context: LegalReviewContext
    embedding_model: Optional[str]
    embedding_version: Optional[str]
    results: list[LegalEvidenceResult]


class LegalTextChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    provision_id: UUID
    article_number: str
    sub_article_reference: Optional[str]
    heading: Optional[str]
    version_label: Optional[str]
    page_number: Optional[int]
    chunk_index: int = Field(ge=0)
    text: str = Field(min_length=1)


class StoredEmbeddingInfo(BaseModel):
    model: str
    version: str
    dimensions: int
    chunks_created: int

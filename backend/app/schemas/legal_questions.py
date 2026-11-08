from datetime import date
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.compliance_analysis import CitationReference
from app.schemas.legal_retrieval import LegalReviewContext


class LegalQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)
    review_context: Optional[LegalReviewContext] = None

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Question must not be blank.")
        return normalized

    @model_validator(mode="after")
    def reject_unverified_context(self) -> "LegalQuestionRequest":
        if self.review_context and self.review_context.include_unverified:
            raise ValueError("Legal questions cannot include unverified sources.")
        return self


class LegalQuestionCitationInput(CitationReference):
    model_config = ConfigDict(extra="forbid")


class LegalQuestionLLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=10_000)
    evidence_assessment: Literal["supporting", "contradictory", "insufficient"]
    citations: list[LegalQuestionCitationInput] = Field(default_factory=list, max_length=20)

    @field_validator("answer")
    @classmethod
    def trim_answer(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Answer must not be blank.")
        return normalized


class LegalQuestionCitation(BaseModel):
    source_id: UUID
    source_title: str
    law_number: Optional[str]
    source_url: Optional[str]
    provision_id: UUID
    article_number: str
    sub_article_reference: Optional[str]
    page_number: Optional[int]
    supporting_quote: str


class LegalQuestionAnswer(BaseModel):
    status: Literal["answered", "insufficient_evidence"]
    question: str
    answer: str
    review_date: date
    citations: list[LegalQuestionCitation]
    model_name: Optional[str]
    model_version: Optional[str]
    disclaimer: str = (
        "This AI-generated information is not legal advice and does not "
        "determine legal rights or obligations. Verify the cited source and "
        "consult a qualified legal professional."
    )

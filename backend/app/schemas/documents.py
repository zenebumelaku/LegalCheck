from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExtractedParagraphResponse(BaseModel):
    paragraph_number: int
    text: str


class ExtractedPageResponse(BaseModel):
    page_number: Optional[int]
    paragraphs: List[ExtractedParagraphResponse]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: Optional[UUID]
    original_filename: str
    content_type: str
    file_size: int
    checksum: Optional[str]
    detected_language: Optional[str]
    document_type: Optional[str]
    processing_status: str
    created_at: datetime
    deleted_at: Optional[datetime]


class DocumentUploadResponse(DocumentResponse):
    pages: List[ExtractedPageResponse]
    warnings: List[str]
    extracted_characters: int


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    limit: int
    offset: int

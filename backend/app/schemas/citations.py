from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CitationReference(BaseModel):
    source_id: UUID
    provision_id: UUID
    article_number: str
    sub_article_reference: Optional[str] = None
    supporting_quote: str = Field(min_length=1, max_length=5000)

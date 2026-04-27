from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

class FeedbackBase(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: str | None = None
    corrected_response: str | None = None

class FeedbackCreate(FeedbackBase):
    ticket_id: UUID

class FeedbackInDB(FeedbackBase):
    id: UUID = Field(default_factory=uuid4)
    ticket_id: UUID
    user_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FeedbackResponse(FeedbackInDB):
    pass

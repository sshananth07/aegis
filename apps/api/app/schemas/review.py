from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ReviewAction(BaseModel):
    status: str  # approved, rejected
    comment: Optional[str] = None

class ReviewResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    reviewer_id: UUID
    status: str
    comment: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 
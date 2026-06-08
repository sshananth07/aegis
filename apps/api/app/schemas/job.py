from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: str
    entity_id: Optional[UUID]
    entity_type: Optional[str]
    result_id: Optional[UUID]
    progress: int
    total: int
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    api_key_id: Optional[uuid.UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[uuid.UUID]
    timestamp: datetime
    metadata: Optional[Any] = None

    class Config:
        from_attributes = True


class APIUsageResponse(BaseModel):
    id: uuid.UUID
    api_key_id: uuid.UUID
    endpoint: str
    method: str
    status_code: int
    latency_ms: int
    timestamp: datetime

    class Config:
        from_attributes = True

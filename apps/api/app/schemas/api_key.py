from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str] = []
    expires_in_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    key_prefix: str
    scopes: List[str]
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    revoked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    key: str

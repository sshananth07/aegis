import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, validator
from app.models.api_key import VALID_SCOPES


class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str]
    expires_in_days: Optional[int] = None

    @validator("scopes")
    def validate_scopes(cls, v):
        for s in v:
            if s not in VALID_SCOPES:
                raise ValueError(f"Invalid scope: {s}. Valid: {VALID_SCOPES}")
        return v


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
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
    key: str  # plaintext key — returned only once on creation

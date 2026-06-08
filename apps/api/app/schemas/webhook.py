from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List

VALID_EVENT_TYPES = {"evaluation.completed", "benchmark.completed", "review.required"}


class WebhookCreate(BaseModel):
    url: str
    event_types: List[str]

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v: str) -> str:
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("url must start with http:// or https://")
        return v

    @field_validator("event_types")
    @classmethod
    def event_types_must_be_valid(cls, v: List[str]) -> List[str]:
        invalid = set(v) - VALID_EVENT_TYPES
        if invalid:
            raise ValueError(
                f"Invalid event_types: {invalid}. "
                f"Valid options: {VALID_EVENT_TYPES}"
            )
        if not v:
            raise ValueError("event_types must not be empty")
        return v


class WebhookResponse(BaseModel):
    id: UUID
    user_id: UUID
    url: str
    event_types: List[str]
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookCreateResponse(WebhookResponse):
    """Returned only on creation — includes the plaintext secret."""
    secret: str


class WebhookDeliveryResponse(BaseModel):
    id: UUID
    webhook_id: UUID
    event_type: str
    status: str
    response_code: Optional[int]
    error_message: Optional[str]
    attempted_at: datetime

    class Config:
        from_attributes = True

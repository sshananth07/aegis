import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, validator

VALID_WEBHOOK_EVENTS = ["evaluation.completed", "benchmark.completed", "review.required"]


class WebhookCreate(BaseModel):
    url: str
    event_types: List[str]

    @validator("url")
    def validate_url(cls, v):
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("event_types")
    def validate_events(cls, v):
        for e in v:
            if e not in VALID_WEBHOOK_EVENTS:
                raise ValueError(f"Invalid event type: {e}")
        return v


class WebhookResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    url: str
    event_types: List[str]
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookCreateResponse(WebhookResponse):
    secret: str  # returned once on creation


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    event_type: str
    status: str
    response_code: Optional[int]
    error_message: Optional[str]
    attempted_at: datetime

    class Config:
        from_attributes = True

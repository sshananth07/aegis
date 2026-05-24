from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class EvaluationCreate(BaseModel):
    prompt_version_id: UUID
    provider: str
    expected_output: Optional[str] = None
    check_json: bool = False

class EvaluationResponse(BaseModel):
    id: UUID
    prompt_version_id: UUID
    provider: str
    response: Optional[str]
    status: str
    score: Optional[float]
    score_details: Optional[dict]
    latency_ms: Optional[int]
    token_usage: Optional[int]
    token_usage_estimated: Optional[bool]
    cost: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class TraceResponse(BaseModel):
    id: UUID
    evaluation_id: UUID
    event_type: str
    provider: Optional[str]
    latency_ms: Optional[int]
    metadata_: Optional[dict]
    timestamp: datetime

    class Config:
        from_attributes = True

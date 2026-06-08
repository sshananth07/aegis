import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

VALID_SCOPES = [
    "evaluations:write",
    "benchmarks:write",
    "traces:read",
    "metrics:read",
    "webhooks:write",
]


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    key_prefix = Column(String, nullable=False)
    scopes = Column(JSONB, nullable=False, default=list)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

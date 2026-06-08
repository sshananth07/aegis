import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

# Action constants
ACTION_API_KEY_CREATED = "api_key.created"
ACTION_API_KEY_REVOKED = "api_key.revoked"
ACTION_WEBHOOK_CREATED = "webhook.created"
ACTION_WEBHOOK_DELETED = "webhook.deleted"
ACTION_EVALUATION_TRIGGERED = "evaluation.triggered"
ACTION_BENCHMARK_STARTED = "benchmark.started"


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    api_key_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_ = Column("metadata", JSONB, nullable=True)

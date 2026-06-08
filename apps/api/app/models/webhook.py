import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    url = Column(String, nullable=False)
    event_types = Column(JSONB, nullable=False, default=list)  # ["evaluation.completed", ...]
    secret = Column(String, nullable=False)  # 32-byte hex, used for HMAC-SHA256 signing
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), nullable=False)
    event_type = Column(String, nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String, nullable=False)       # "success" or "failed"
    response_code = Column(Integer, nullable=True)
    error_message = Column(String, nullable=True)
    attempted_at = Column(DateTime, nullable=False, default=datetime.utcnow)

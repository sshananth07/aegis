import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String, nullable=False)
    key_prefix = Column(String(8), nullable=False)
    key_hash = Column(String, nullable=False)
    scopes = Column(ARRAY(String), nullable=False, default=list)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

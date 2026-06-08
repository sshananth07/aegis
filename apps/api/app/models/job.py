import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Float, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.db.base import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String, nullable=False)
    status = Column(String, default="queued")
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    entity_type = Column(String, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    result_id = Column(UUID(as_uuid=True), nullable=True)
    progress = Column(Integer, default=0)
    total = Column(Integer, default=0)
    error = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

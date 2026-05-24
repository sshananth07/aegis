import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.enums import EvaluationStatus

class EvaluationGroup(Base):
    __tablename__ = "evaluation_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_run_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_runs.id"), nullable=True)
    dataset_item_id = Column(UUID(as_uuid=True), nullable=True)
    prompt_version_id = Column(UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=False)
    divergence_score = Column(Float)
    divergence_detected = Column(Boolean, default=False)
    review_required = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    evaluations = relationship("Evaluation", back_populates="group")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_group_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_groups.id"), nullable=True)
    prompt_version_id = Column(UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=False)
    provider = Column(String, nullable=False)
    response = Column(Text)
    status = Column(String, default=EvaluationStatus.queued)
    score = Column(Float)
    score_details = Column(JSONB)
    latency_ms = Column(Integer)
    token_usage = Column(Integer)
    token_usage_estimated = Column(Boolean, default=False)
    cost = Column(Float)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("EvaluationGroup", back_populates="evaluations")
    prompt_version = relationship("PromptVersion", back_populates="evaluations")
    traces = relationship("Trace", back_populates="evaluation")


class Trace(Base):
    __tablename__ = "traces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_id = Column(UUID(as_uuid=True), ForeignKey("evaluations.id"), nullable=False)
    event_type = Column(String, nullable=False)
    provider = Column(String)
    latency_ms = Column(Integer)
    metadata_ = Column("metadata", JSONB)
    timestamp = Column(DateTime, default=datetime.utcnow)

    evaluation = relationship("Evaluation", back_populates="traces")
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Float, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.core.enums import BenchmarkRunStatus 

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("DatasetItem", back_populates="dataset")


class DatasetItem(Base):
    __tablename__ = "dataset_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    input_text = Column(Text, nullable=False)
    expected_output = Column(Text)
    check_json = Column(Boolean, default=False)
    required_keywords = Column(JSONB, nullable=False, default=list)
    required_json_fields = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="items")


class BenchmarkSuite(Base):
    __tablename__ = "benchmark_suites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=False)
    prompt_version_id = Column(UUID(as_uuid=True), ForeignKey("prompt_versions.id"), nullable=True)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    providers = Column(JSONB, nullable=False, default=list)
    pass_threshold = Column(Float, default=0.7)
    semantic_similarity_threshold = Column(Float, default=0.7)
    keyword_coverage_threshold = Column(Float, default=0.6)
    json_validity_required = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    runs = relationship("BenchmarkRun", back_populates="suite")


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    suite_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_suites.id"), nullable=False)
    status = Column(String, default=BenchmarkRunStatus.queued)
    total_cases = Column(String, default=0)
    passed_cases = Column(String, default=0)
    avg_latency_ms = Column(Float)
    avg_score = Column(Float)
    avg_cost = Column(Float)
    results = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    suite = relationship("BenchmarkSuite", back_populates="runs")

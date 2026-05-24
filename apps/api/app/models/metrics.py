import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, Integer
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ProviderMetricsHourly(Base):
    __tablename__ = "provider_metrics_hourly"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    avg_latency_ms = Column(Float)
    success_rate = Column(Float)
    avg_cost = Column(Float)
    fallback_rate = Column(Float)
    total_evaluations = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False)


class ProviderMetricsDaily(Base):
    __tablename__ = "provider_metrics_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    pass_rate = Column(Float)
    p95_latency_ms = Column(Float)
    avg_cost = Column(Float)
    avg_score = Column(Float)
    total_evaluations = Column(Integer, default=0)
    timestamp = Column(DateTime, nullable=False)
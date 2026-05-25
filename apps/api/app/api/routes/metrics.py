from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.auth import get_user_id
from app.services.metrics_service import (
    compute_hourly_metrics,
    compute_daily_metrics,
    get_platform_overview,
    get_provider_summary
)

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/providers")
def provider_metrics(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    # Depending on implementation, you might pass user_id down
    return get_provider_summary(db)

@router.get("/overview")
def platform_overview(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_platform_overview(db)

@router.post("/providers/{provider}/aggregate/hourly")
def aggregate_hourly(
    provider: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    metrics = compute_hourly_metrics(db, provider)
    if not metrics:
        raise HTTPException(status_code=404, detail="No data found")
    return {
        "provider": metrics.provider,
        "avg_latency_ms": metrics.avg_latency_ms,
        "success_rate": metrics.success_rate,
        "avg_cost": metrics.avg_cost,
        "fallback_rate": metrics.fallback_rate,
        "total_evaluations": metrics.total_evaluations,
        "timestamp": metrics.timestamp
    }

@router.post("/providers/{provider}/aggregate/daily")
def aggregate_daily(
    provider: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    metrics = compute_daily_metrics(db, provider)
    if not metrics:
        raise HTTPException(status_code=404, detail="No data found")
    return {
        "provider": metrics.provider,
        "pass_rate": metrics.pass_rate,
        "p95_latency_ms": metrics.p95_latency_ms,
        "avg_cost": metrics.avg_cost,
        "avg_score": metrics.avg_score,
        "total_evaluations": metrics.total_evaluations,
        "timestamp": metrics.timestamp
    }

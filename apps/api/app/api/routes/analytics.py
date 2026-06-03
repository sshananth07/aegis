from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.auth import get_user_id
from app.services.analytics_service import (
    get_failure_overview,
    get_failure_timeseries,
    get_failures_by_reason,
    get_provider_stability,
    get_cost_overview,
    get_cost_by_provider,
    get_cost_timeseries,
    get_regressions,
    get_benchmark_stability,
    get_benchmark_history,
)
import uuid

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/failures/overview")
def failure_overview(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_failure_overview(db, uuid.UUID(user_id))


@router.get("/failures/timeseries")
def failure_timeseries(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_failure_timeseries(db, uuid.UUID(user_id), days)


@router.get("/failures/by-reason")
def failures_by_reason(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_failures_by_reason(db, uuid.UUID(user_id))


@router.get("/failures/providers")
def provider_stability(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_provider_stability(db, uuid.UUID(user_id))


@router.get("/costs/overview")
def cost_overview(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_cost_overview(db, uuid.UUID(user_id))


@router.get("/costs/providers")
def cost_by_provider(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_cost_by_provider(db, uuid.UUID(user_id))


@router.get("/costs/timeseries")
def cost_timeseries(
    days: int = Query(default=14, ge=1, le=90),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_cost_timeseries(db, uuid.UUID(user_id), days)


@router.get("/regressions")
def regressions(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_regressions(db, uuid.UUID(user_id))

@router.get("/benchmarks/stability")
def benchmark_stability(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_benchmark_stability(db, uuid.UUID(user_id))

@router.get("/benchmarks/history")
def benchmark_history(
    suite_id: str = Query(default=None),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return get_benchmark_history(db, uuid.UUID(user_id), suite_id)

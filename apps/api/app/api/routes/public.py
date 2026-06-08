"""
Public /v1 API routes — authenticated via API key (X-API-Key header).

Endpoints:
  GET /v1/traces          — list traces (scope: traces:read)
  GET /v1/traces/{id}     — get single trace (scope: traces:read)
  GET /v1/metrics         — aggregated metrics (scope: metrics:read)
"""

import uuid
import structlog
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.core.rate_limit import limiter
from app.core.exceptions import (
    invalid_api_key,
    resource_not_found,
)
from app.models.evaluation import Evaluation, Trace
from app.core.enums import EvaluationStatus

logger = structlog.get_logger()

router = APIRouter(prefix="/v1", tags=["public"])


# ── Auth stub ─────────────────────────────────────────────────────────────────
# When Unit 2 (API-key management) is merged, replace this with:
#   from app.core.auth import get_api_key_user
# and remove the stub below.

async def get_api_key_user(
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> str:
    """
    Validate the X-API-Key header and return the owner's user_id (UUID string).

    This is a stub — it always rejects requests until Unit 2's ApiKey model is
    merged.  Once merged, swap this body for a real DB lookup:

        key_row = db.query(ApiKey).filter(
            ApiKey.key_hash == hash_key(x_api_key),
            ApiKey.revoked == False,
        ).first()
        if not key_row:
            raise invalid_api_key()
        return str(key_row.created_by)
    """
    # Stub: reject all keys so the error contract is exercised in tests.
    raise invalid_api_key()


# ── Traces ────────────────────────────────────────────────────────────────────

@router.get("/traces")
@limiter.limit("60/minute")
def list_traces(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_api_key_user),
):
    """List traces owned by the authenticated API-key user (paginated)."""
    logger.info("v1.traces.list", user_id=user_id, limit=limit, offset=offset)

    base_query = (
        db.query(Trace)
        .join(Evaluation, Trace.evaluation_id == Evaluation.id)
        .filter(Evaluation.created_by == uuid.UUID(user_id))
    )

    total = base_query.count()
    items = (
        base_query
        .order_by(Trace.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "items": [_trace_to_dict(t) for t in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/traces/{trace_id}")
@limiter.limit("60/minute")
def get_trace(
    trace_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_api_key_user),
):
    """Get a single trace by ID (ownership-checked)."""
    logger.info("v1.traces.get", user_id=user_id, trace_id=str(trace_id))

    trace = (
        db.query(Trace)
        .join(Evaluation, Trace.evaluation_id == Evaluation.id)
        .filter(
            Trace.id == trace_id,
            Evaluation.created_by == uuid.UUID(user_id),
        )
        .first()
    )

    if trace is None:
        raise resource_not_found("Trace")

    return _trace_to_dict(trace)


# ── Metrics ───────────────────────────────────────────────────────────────────

@router.get("/metrics")
@limiter.limit("30/minute")
def get_metrics(
    request: Request,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_api_key_user),
):
    """Return aggregated evaluation metrics for the authenticated user."""
    logger.info("v1.metrics.get", user_id=user_id)

    evals = (
        db.query(Evaluation)
        .filter(Evaluation.created_by == uuid.UUID(user_id))
        .all()
    )

    total = len(evals)
    if total == 0:
        return {
            "evaluation_count": 0,
            "pass_rate": 0.0,
            "failure_rate": 0.0,
            "avg_latency_ms": 0,
            "provider_distribution": {},
            "top_failure_reasons": [],
            "score_avg": 0.0,
        }

    passed = sum(1 for e in evals if e.status == EvaluationStatus.completed)
    failed = sum(
        1 for e in evals
        if e.status in (EvaluationStatus.failed, EvaluationStatus.review_required)
    )

    latencies = [e.latency_ms for e in evals if e.latency_ms is not None]
    avg_latency = round(sum(latencies) / len(latencies)) if latencies else 0

    scores = [e.score for e in evals if e.score is not None]
    score_avg = round(sum(scores) / len(scores), 4) if scores else 0.0

    # Provider distribution (count per provider)
    provider_dist: dict[str, int] = {}
    for e in evals:
        provider_dist[e.provider] = provider_dist.get(e.provider, 0) + 1

    # Top failure reasons (from score_details JSONB)
    reason_counts: dict[str, int] = {}
    for e in evals:
        if e.score_details and "failure_reasons" in e.score_details:
            for reason in e.score_details["failure_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    top_failure_reasons = [
        {"reason": r, "count": c}
        for r, c in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)
    ][:10]

    return {
        "evaluation_count": total,
        "pass_rate": round(passed / total, 4),
        "failure_rate": round(failed / total, 4),
        "avg_latency_ms": avg_latency,
        "provider_distribution": provider_dist,
        "top_failure_reasons": top_failure_reasons,
        "score_avg": score_avg,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _trace_to_dict(trace: Trace) -> dict:
    return {
        "id": str(trace.id),
        "evaluation_id": str(trace.evaluation_id),
        "event_type": trace.event_type,
        "provider": trace.provider,
        "latency_ms": trace.latency_ms,
        "metadata": trace.metadata_,
        "timestamp": trace.timestamp.isoformat() if trace.timestamp else None,
    }

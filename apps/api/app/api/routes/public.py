import uuid
import structlog
from typing import Optional, Tuple
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.auth import get_api_key_user, require_scope
from app.core.cache import cache_get, cache_set
from app.core.rate_limit import limiter
from app.db.base import get_db
from app.models.benchmark import BenchmarkRun, BenchmarkSuite, DatasetItem
from app.models.evaluation import Evaluation
from app.schemas.benchmark import BenchmarkRunResponse
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse
from app.schemas.job import JobResponse
from app.models.job import Job
from app.services.job_service import create_job
from app.workers.benchmark_worker import run_benchmark_job
from app.workers.evaluation_worker import run_evaluation_job

logger = structlog.get_logger()

router = APIRouter(prefix="/v1", tags=["public-api"])


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

@router.post("/evaluations", response_model=JobResponse)
@limiter.limit("60/minute")
async def public_create_evaluation(
    request: Request,
    data: EvaluationCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user_id: str = Depends(require_scope("evaluations:write")),
):
    """Create an evaluation via API key. Supports Idempotency-Key header."""
    # Idempotency check
    if idempotency_key:
        cache_key = f"idempotency:eval:{user_id}:{idempotency_key}"
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("idempotency_hit", key=idempotency_key)
            job = db.query(Job).filter(Job.id == uuid.UUID(cached)).first()
            if job:
                return job

    job = create_job(
        db=db,
        job_type="evaluation",
        user_id=uuid.UUID(user_id),
        entity_id=data.prompt_version_id,
        entity_type="prompt_version",
        total=1,
        metadata={"provider": data.provider},
    )

    run_evaluation_job.send(
        str(job.id),
        str(data.prompt_version_id),
        data.provider,
        user_id,
        data.expected_output,
        data.check_json,
    )

    if idempotency_key:
        cache_key = f"idempotency:eval:{user_id}:{idempotency_key}"
        try:
            cache_set(cache_key, str(job.id), ttl_seconds=86400)
        except Exception:
            pass  # gracefully skip if cache unavailable

    logger.info("public_evaluation_created",
                job_id=str(job.id),
                user_id=user_id,
                provider=data.provider)
    return job


@router.get("/evaluations/{evaluation_id}", response_model=EvaluationResponse)
async def public_get_evaluation(
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    api_key_data: Tuple[str, list] = Depends(get_api_key_user),
):
    """Retrieve a single evaluation. Requires evaluations:write or traces:read scope."""
    user_id, scopes = api_key_data
    if "evaluations:write" not in scopes and "traces:read" not in scopes:
        raise HTTPException(
            status_code=403,
            detail="Scope 'evaluations:write' or 'traces:read' required",
        )

    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by == uuid.UUID(user_id),
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation


# ---------------------------------------------------------------------------
# Benchmarks
# ---------------------------------------------------------------------------

class BenchmarkRunCreate(BaseModel):
    suite_id: uuid.UUID


@router.post("/benchmarks/run", response_model=JobResponse)
@limiter.limit("20/minute")
async def public_run_benchmark(
    request: Request,
    data: BenchmarkRunCreate,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    user_id: str = Depends(require_scope("benchmarks:write")),
):
    """Trigger a benchmark run via API key. Supports Idempotency-Key header."""
    # Idempotency check
    if idempotency_key:
        cache_key = f"idempotency:bench:{user_id}:{idempotency_key}"
        cached = cache_get(cache_key)
        if cached is not None:
            logger.info("idempotency_hit", key=idempotency_key)
            job = db.query(Job).filter(Job.id == uuid.UUID(cached)).first()
            if job:
                return job

    suite = db.query(BenchmarkSuite).filter(
        BenchmarkSuite.id == data.suite_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id),
    ).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")

    items_count = db.query(DatasetItem).filter(
        DatasetItem.dataset_id == suite.dataset_id
    ).count()
    total = items_count * len(suite.providers)

    job = create_job(
        db=db,
        job_type="benchmark",
        user_id=uuid.UUID(user_id),
        entity_id=data.suite_id,
        entity_type="benchmark_suite",
        total=total,
        metadata={"suite_name": suite.name},
    )

    try:
        run_benchmark_job.send(str(job.id), str(data.suite_id), user_id)
    except RedisError as exc:
        job.status = "failed"
        job.error = "Benchmark worker queue is unavailable"
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Benchmark worker queue is unavailable. Check Redis and retry.",
        ) from exc

    if idempotency_key:
        cache_key = f"idempotency:bench:{user_id}:{idempotency_key}"
        try:
            cache_set(cache_key, str(job.id), ttl_seconds=86400)
        except Exception:
            pass

    logger.info("public_benchmark_run_created",
                job_id=str(job.id),
                suite_id=str(data.suite_id),
                user_id=user_id)
    return job


@router.get("/benchmarks/runs/{run_id}", response_model=BenchmarkRunResponse)
async def public_get_benchmark_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(require_scope("benchmarks:write")),
):
    """Retrieve a benchmark run. Ownership verified via BenchmarkSuite.created_by."""
    run = db.query(BenchmarkRun).join(BenchmarkSuite).filter(
        BenchmarkRun.id == run_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id),
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

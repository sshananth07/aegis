import dramatiq
import uuid
import asyncio
import structlog
from datetime import datetime

from app.core.broker import broker  # noqa: F401

logger = structlog.get_logger()

@dramatiq.actor(max_retries=2, time_limit=3600000)
def run_benchmark_job(job_id: str, suite_id: str, user_id: str):
    """Background worker for benchmark execution."""
    from app.db.base import SessionLocal
    from app.models.job import Job
    from app.services.benchmark_service import run_benchmark
    from app.core.cache import cache_clear_prefix

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return

        # Mark job as running
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info("benchmark_job_started",
            job_id=job_id,
            suite_id=suite_id
        )

        # Run the benchmark
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            run = loop.run_until_complete(
                run_benchmark(
                    db=db,
                    suite_id=uuid.UUID(suite_id),
                    user_id=uuid.UUID(user_id)
                )
            )
        finally:
            loop.close()

        # Mark job as completed
        job.status = "completed"
        job.result_id = run.id
        job.completed_at = datetime.utcnow()
        job.progress = int(run.total_cases or 0)
        job.total = int(run.total_cases or 0)
        db.commit()

        # Clear caches
        cache_clear_prefix("metrics:")
        cache_clear_prefix("analytics:")

        logger.info("benchmark_job_completed",
            job_id=job_id,
            run_id=str(run.id)
        )

    except Exception as e:
        logger.error("benchmark_job_failed",
            job_id=job_id,
            error=str(e)
        )
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.commit()
        raise

    finally:
        db.close()

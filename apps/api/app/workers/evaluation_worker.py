import dramatiq
import uuid
import asyncio
import structlog
from datetime import datetime

from app.core.broker import broker  # noqa: F401

logger = structlog.get_logger()

@dramatiq.actor(max_retries=2, time_limit=300000)
def run_evaluation_job(
    job_id: str,
    prompt_version_id: str,
    provider_name: str,
    user_id: str,
    expected_output: str = None,
    check_json: bool = False,
):
    """Background worker for single evaluation execution."""
    from app.db.base import SessionLocal
    from app.models.job import Job
    from app.services.eval_service import run_evaluation
    from app.core.cache import cache_clear_prefix

    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == uuid.UUID(job_id)).first()
        if not job:
            logger.error("job_not_found", job_id=job_id)
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            evaluation = loop.run_until_complete(
                run_evaluation(
                    db=db,
                    prompt_version_id=uuid.UUID(prompt_version_id),
                    provider_name=provider_name,
                    user_id=uuid.UUID(user_id),
                    expected_output=expected_output,
                    check_json=check_json,
                )
            )
        finally:
            loop.close()

        job.status = "completed"
        job.result_id = evaluation.id
        job.completed_at = datetime.utcnow()
        db.commit()

        cache_clear_prefix("metrics:")
        cache_clear_prefix("analytics:")

        logger.info("evaluation_job_completed",
            job_id=job_id,
            evaluation_id=str(evaluation.id)
        )

    except Exception as e:
        logger.error("evaluation_job_failed",
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

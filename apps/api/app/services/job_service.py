import uuid
import structlog
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job import Job

logger = structlog.get_logger()

def create_job(
    db: Session,
    job_type: str,
    user_id: uuid.UUID,
    entity_id: uuid.UUID = None,
    entity_type: str = None,
    total: int = 0,
    metadata: dict = None,
) -> Job:
    job = Job(
        job_type=job_type,
        status="queued",
        entity_id=entity_id,
        entity_type=entity_type,
        created_by=user_id,
        total=total,
        metadata_=metadata or {},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

def get_job(db: Session, job_id: uuid.UUID, user_id: uuid.UUID) -> Job:
    return db.query(Job).filter(
        Job.id == job_id,
        Job.created_by == user_id
    ).first()

def list_jobs(
    db: Session,
    user_id: uuid.UUID,
    job_type: str = None,
    limit: int = 20
) -> list[Job]:
    query = db.query(Job).filter(Job.created_by == user_id)
    if job_type:
        query = query.filter(Job.job_type == job_type)
    return query.order_by(Job.created_at.desc()).limit(limit).all()

def cancel_job(db: Session, job_id: uuid.UUID, user_id: uuid.UUID) -> Job:
    job = db.query(Job).filter(
        Job.id == job_id,
        Job.created_by == user_id,
        Job.status == "queued"
    ).first()
    if job:
        job.status = "cancelled"
        db.commit()
        db.refresh(job)
    return job

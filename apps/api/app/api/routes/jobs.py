import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.core.auth import get_user_id
from app.services.job_service import get_job, list_jobs, cancel_job
from app.schemas.job import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/", response_model=list[JobResponse])
def list_all_jobs(
    job_type: str = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return list_jobs(db, uuid.UUID(user_id), job_type)

@router.get("/{job_id}", response_model=JobResponse)
def get_job_status(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    job = get_job(db, job_id, uuid.UUID(user_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    job = cancel_job(db, job_id, uuid.UUID(user_id))
    if not job:
        raise HTTPException(
            status_code=400,
            detail="Job not found or cannot be cancelled"
        )
    return job

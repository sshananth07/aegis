import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, TraceResponse
from app.services.eval_service import run_evaluation
from app.services.job_service import create_job
from app.workers.evaluation_worker import run_evaluation_job
from app.schemas.job import JobResponse
from app.models.evaluation import Evaluation, Trace
from app.core.auth import get_user_id
from app.core.rate_limit import limiter

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

@router.post("/", response_model=JobResponse)
@limiter.limit("20/minute")
async def create_evaluation(
    request: Request,
    data: EvaluationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    job = create_job(
        db=db,
        job_type="evaluation",
        user_id=uuid.UUID(user_id),
        entity_id=data.prompt_version_id,
        entity_type="prompt_version",
        total=1,
        metadata={"provider": data.provider}
    )

    run_evaluation_job.send(
        str(job.id),
        str(data.prompt_version_id),
        data.provider,
        user_id,
        data.expected_output,
        data.check_json,
    )

    return job

@router.get("/", response_model=list[EvaluationResponse])
def list_evaluations(
    limit: int = 50,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return db.query(Evaluation).filter(
        Evaluation.created_by == uuid.UUID(user_id)
    ).order_by(Evaluation.created_at.desc()).limit(limit).all()

@router.get("/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by == uuid.UUID(user_id)
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation

@router.get("/{evaluation_id}/traces", response_model=list[TraceResponse])
def get_traces(
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id,
        Evaluation.created_by == uuid.UUID(user_id)
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return db.query(Trace).filter(
        Trace.evaluation_id == evaluation_id
    ).order_by(Trace.timestamp.asc()).all()
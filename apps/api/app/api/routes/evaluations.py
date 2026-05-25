import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, TraceResponse
from app.services.eval_service import run_evaluation
from app.models.evaluation import Evaluation, Trace
from app.core.auth import get_user_id
from app.core.rate_limit import limiter

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

@router.post("/", response_model=EvaluationResponse)
@limiter.limit("20/minute")
async def create_evaluation(
    request: Request,
    data: EvaluationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    try:
        evaluation = await run_evaluation(
            db=db,
            prompt_version_id=data.prompt_version_id,
            provider_name=data.provider,
            user_id=uuid.UUID(user_id),
            expected_output=data.expected_output,
            check_json=data.check_json,
        )
        return evaluation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
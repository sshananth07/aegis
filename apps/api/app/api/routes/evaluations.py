import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, TraceResponse
from app.services.eval_service import run_evaluation
from app.models.evaluation import Evaluation, Trace

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

@router.get("/", response_model=list[EvaluationResponse])
def list_evaluations(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return db.query(Evaluation).order_by(
        Evaluation.created_at.desc()
    ).limit(limit).all()

@router.post("/", response_model=EvaluationResponse)
async def create_evaluation(data: EvaluationCreate, db: Session = Depends(get_db)):
    try:
        evaluation = await run_evaluation(
            db=db,
            prompt_version_id=data.prompt_version_id,
            provider_name=data.provider,
            user_id=TEMP_USER_ID,
            expected_output=data.expected_output,
            check_json=data.check_json,
        )
        return evaluation
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{evaluation_id}", response_model=EvaluationResponse)
def get_evaluation(evaluation_id: uuid.UUID, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return evaluation

@router.get("/{evaluation_id}/traces", response_model=list[TraceResponse])
def get_traces(evaluation_id: uuid.UUID, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    traces = db.query(Trace).filter(
        Trace.evaluation_id == evaluation_id
    ).order_by(Trace.timestamp.asc()).all()

    return traces
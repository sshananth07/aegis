import csv
import json
import uuid
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.evaluation import Evaluation, Trace
from app.models.benchmark import BenchmarkRun

router = APIRouter(prefix="/exports", tags=["exports"])

@router.get("/evaluations/csv")
def export_evaluations_csv(db: Session = Depends(get_db)):
    evaluations = db.query(Evaluation).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "evaluation_id", "provider", "status",
        "score", "latency_ms", "token_usage",
        "token_usage_estimated", "cost", "created_at"
    ])

    for e in evaluations:
        writer.writerow([
            str(e.id), e.provider, e.status,
            e.score, e.latency_ms, e.token_usage,
            e.token_usage_estimated, e.cost,
            e.created_at.isoformat()
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=evaluations.csv"}
    )

@router.get("/benchmarks/{run_id}/csv")
def export_benchmark_csv(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "provider", "input", "score", "passed",
        "latency_ms", "token_usage", "cost", "failure_reasons"
    ])

    for result in (run.results or []):
        writer.writerow([
            result.get("provider"),
            result.get("input"),
            result.get("score"),
            result.get("passed"),
            result.get("latency_ms"),
            result.get("token_usage"),
            result.get("cost"),
            ", ".join(result.get("failure_reasons") or [])
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=benchmark_{run_id}.csv"}
    )

@router.get("/evaluations/{evaluation_id}/json")
def export_evaluation_json(evaluation_id: uuid.UUID, db: Session = Depends(get_db)):
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == evaluation_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    traces = db.query(Trace).filter(
        Trace.evaluation_id == evaluation_id
    ).order_by(Trace.timestamp.asc()).all()

    export = {
        "evaluation": {
            "id": str(evaluation.id),
            "provider": evaluation.provider,
            "status": evaluation.status,
            "score": evaluation.score,
            "score_details": evaluation.score_details,
            "latency_ms": evaluation.latency_ms,
            "token_usage": evaluation.token_usage,
            "token_usage_estimated": evaluation.token_usage_estimated,
            "cost": evaluation.cost,
            "response": evaluation.response,
            "created_at": evaluation.created_at.isoformat()
        },
        "traces": [
            {
                "event_type": t.event_type,
                "provider": t.provider,
                "latency_ms": t.latency_ms,
                "metadata": t.metadata_,
                "timestamp": t.timestamp.isoformat()
            }
            for t in traces
        ]
    }

    return StreamingResponse(
        iter([json.dumps(export, indent=2)]),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=evaluation_{evaluation_id}.json"
        }
    )
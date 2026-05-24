import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.benchmark import Dataset, DatasetItem, BenchmarkSuite, BenchmarkRun
from app.models.prompt import PromptVersion
from app.schemas.benchmark import (
    DatasetCreate, DatasetResponse,
    BenchmarkSuiteCreate, BenchmarkSuiteResponse,
    BenchmarkRunResponse
)
from app.services.benchmark_service import run_benchmark

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])
TEMP_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# --- Datasets ---

@router.post("/datasets", response_model=DatasetResponse)
def create_dataset(data: DatasetCreate, db: Session = Depends(get_db)):
    dataset = Dataset(
        name=data.name,
        description=data.description,
        created_by=TEMP_USER_ID
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    for item in data.items:
        db_item = DatasetItem(
            dataset_id=dataset.id,
            input_text=item.input_text,
            expected_output=item.expected_output,
            check_json=item.check_json,
            required_keywords=item.required_keywords,
            required_json_fields=item.required_json_fields,
        )
        db.add(db_item)
    db.commit()
    db.refresh(dataset)
    return dataset

@router.get("/datasets", response_model=list[DatasetResponse])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(Dataset).all()


# --- Benchmark Suites ---

@router.post("/suites", response_model=BenchmarkSuiteResponse)
def create_suite(data: BenchmarkSuiteCreate, db: Session = Depends(get_db)):
    prompt_version_query = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == data.prompt_id
    )

    if data.prompt_version_id:
        prompt_version = prompt_version_query.filter(
            PromptVersion.id == data.prompt_version_id
        ).first()
    else:
        prompt_version = prompt_version_query.order_by(
            PromptVersion.version.desc()
        ).first()

    if not prompt_version:
        raise HTTPException(status_code=400, detail="Prompt version not found")

    suite = BenchmarkSuite(
        name=data.name,
        description=data.description,
        prompt_id=data.prompt_id,
        prompt_version_id=prompt_version.id,
        dataset_id=data.dataset_id,
        providers=data.providers,
        pass_threshold=data.pass_threshold,
        semantic_similarity_threshold=data.semantic_similarity_threshold,
        keyword_coverage_threshold=data.keyword_coverage_threshold,
        json_validity_required=data.json_validity_required,
        created_by=TEMP_USER_ID
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite

@router.get("/suites", response_model=list[BenchmarkSuiteResponse])
def list_suites(db: Session = Depends(get_db)):
    return db.query(BenchmarkSuite).all()

@router.get("/suites/{suite_id}", response_model=BenchmarkSuiteResponse)
def get_suite(suite_id: uuid.UUID, db: Session = Depends(get_db)):
    suite = db.query(BenchmarkSuite).filter(BenchmarkSuite.id == suite_id).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    return suite


# --- Benchmark Runs ---

@router.post("/suites/{suite_id}/run", response_model=BenchmarkRunResponse)
async def run_suite(suite_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        run = await run_benchmark(db=db, suite_id=suite_id, user_id=TEMP_USER_ID)
        return run
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suites/{suite_id}/runs", response_model=list[BenchmarkRunResponse])
def list_runs(suite_id: uuid.UUID, db: Session = Depends(get_db)):
    return db.query(BenchmarkRun).filter(
        BenchmarkRun.suite_id == suite_id
    ).order_by(BenchmarkRun.created_at.desc()).all()

@router.get("/runs/{run_id}", response_model=BenchmarkRunResponse)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/runs/{run_id}/provider-summary")
def get_provider_summary(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not run.results:
        return {}

    provider_stats = {}
    for result in run.results:
        provider = result.get("provider")
        if provider not in provider_stats:
            provider_stats[provider] = {
                "total": 0,
                "passed": 0,
                "scores": [],
                "latencies": [],
                "costs": []
            }
        stats = provider_stats[provider]
        stats["total"] += 1
        if result.get("passed"):
            stats["passed"] += 1
        if result.get("score") is not None:
            stats["scores"].append(result["score"])
        if result.get("latency_ms"):
            stats["latencies"].append(result["latency_ms"])
        if result.get("cost") is not None:
            stats["costs"].append(result["cost"])

    summary = {}
    for provider, stats in provider_stats.items():
        summary[provider] = {
            "pass_rate": stats["passed"] / stats["total"] if stats["total"] else 0,
            "avg_score": sum(stats["scores"]) / len(stats["scores"]) if stats["scores"] else 0,
            "avg_latency_ms": sum(stats["latencies"]) / len(stats["latencies"]) if stats["latencies"] else 0,
            "avg_cost": sum(stats["costs"]) / len(stats["costs"]) if stats["costs"] else 0,
            "total_cases": stats["total"],
            "passed_cases": stats["passed"],
        }

    return summary
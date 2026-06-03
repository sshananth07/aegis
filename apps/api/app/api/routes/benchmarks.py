import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from app.db.base import get_db
from app.models.benchmark import Dataset, DatasetItem, BenchmarkSuite, BenchmarkRun
from app.models.prompt import PromptVersion
from app.schemas.benchmark import (
    DatasetCreate, DatasetResponse,
    DatasetItemCreate, DatasetItemResponse,
    BenchmarkSuiteCreate, BenchmarkSuiteResponse,
    BenchmarkRunResponse
)
from app.services.benchmark_service import run_benchmark
from app.core.auth import get_user_id
from app.core.rate_limit import limiter

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


# --- Datasets ---

@router.post("/datasets", response_model=DatasetResponse)
def create_dataset(
    data: DatasetCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    dataset = Dataset(
        name=data.name,
        description=data.description,
        created_by=uuid.UUID(user_id)
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
def list_datasets(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return db.query(Dataset).options(
        joinedload(Dataset.items)
    ).filter(
        Dataset.created_by == uuid.UUID(user_id)
    ).all()

@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    dataset = db.query(Dataset).options(
        joinedload(Dataset.items)
    ).filter(
        Dataset.id == dataset_id,
        Dataset.created_by == uuid.UUID(user_id)
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset

@router.post("/datasets/{dataset_id}/items", response_model=DatasetItemResponse)
def add_dataset_item(
    dataset_id: uuid.UUID,
    item: DatasetItemCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    # Verify ownership
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.created_by == uuid.UUID(user_id)
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    db_item = DatasetItem(
        dataset_id=dataset_id,
        input_text=item.input_text,
        expected_output=item.expected_output,
        check_json=item.check_json,
        required_keywords=item.required_keywords,
        required_json_fields=item.required_json_fields,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/datasets/{dataset_id}/items/{item_id}")
def delete_dataset_item(
    dataset_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.created_by == uuid.UUID(user_id)
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    item = db.query(DatasetItem).filter(
        DatasetItem.id == item_id,
        DatasetItem.dataset_id == dataset_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(item)
    db.commit()
    return {"deleted": True}

@router.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.created_by == uuid.UUID(user_id)
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete items first due to foreign key constraint
    db.query(DatasetItem).filter(
        DatasetItem.dataset_id == dataset_id
    ).delete()

    db.delete(dataset)
    db.commit()
    return {"deleted": True}

@router.patch("/datasets/{dataset_id}/items/{item_id}", response_model=DatasetItemResponse)
def update_dataset_item(
    dataset_id: uuid.UUID,
    item_id: uuid.UUID,
    item: DatasetItemCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    dataset = db.query(Dataset).filter(
        Dataset.id == dataset_id,
        Dataset.created_by == uuid.UUID(user_id)
    ).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    db_item = db.query(DatasetItem).filter(
        DatasetItem.id == item_id,
        DatasetItem.dataset_id == dataset_id
    ).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.input_text = item.input_text
    db_item.expected_output = item.expected_output
    db_item.check_json = item.check_json
    db_item.required_keywords = item.required_keywords
    db_item.required_json_fields = item.required_json_fields
    db.commit()
    db.refresh(db_item)
    return db_item


# --- Benchmark Suites ---

@router.post("/suites", response_model=BenchmarkSuiteResponse)
def create_suite(
    data: BenchmarkSuiteCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
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
        created_by=uuid.UUID(user_id)
    )
    db.add(suite)
    db.commit()
    db.refresh(suite)
    return suite

@router.get("/suites", response_model=list[BenchmarkSuiteResponse])
def list_suites(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return db.query(BenchmarkSuite).filter(
        BenchmarkSuite.created_by == uuid.UUID(user_id)
    ).all()

@router.get("/suites/{suite_id}", response_model=BenchmarkSuiteResponse)
def get_suite(
    suite_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    suite = db.query(BenchmarkSuite).filter(
        BenchmarkSuite.id == suite_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id)
    ).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")
    return suite


# --- Benchmark Runs ---

@router.post("/suites/{suite_id}/run", response_model=BenchmarkRunResponse)
@limiter.limit("5/minute")
async def run_suite(
    request: Request,
    suite_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    try:
        run = await run_benchmark(db=db, suite_id=suite_id, user_id=uuid.UUID(user_id))
        return run
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/suites/{suite_id}/runs", response_model=list[BenchmarkRunResponse])
def list_runs(
    suite_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    # Verify suite owner
    suite = db.query(BenchmarkSuite).filter(
        BenchmarkSuite.id == suite_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id)
    ).first()
    if not suite:
        raise HTTPException(status_code=404, detail="Suite not found")

    return db.query(BenchmarkRun).filter(
        BenchmarkRun.suite_id == suite_id
    ).order_by(BenchmarkRun.created_at.desc()).all()

@router.get("/runs/{run_id}", response_model=BenchmarkRunResponse)
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    # Join with suit to verify owner
    run = db.query(BenchmarkRun).join(BenchmarkSuite).filter(
        BenchmarkRun.id == run_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id)
    ).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.get("/runs/{run_id}/provider-summary")
def get_provider_summary(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    run = db.query(BenchmarkRun).join(BenchmarkSuite).filter(
        BenchmarkRun.id == run_id,
        BenchmarkSuite.created_by == uuid.UUID(user_id)
    ).first()
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
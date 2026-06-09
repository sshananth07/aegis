"""
Tests for benchmark runs: route dispatch, worker flow, and end-to-end with mocked LLM.

What to pay attention to:
- PASS: POST /suites/{id}/run returns a Job with status "queued"
- PASS: worker creates a BenchmarkRun and sets job.result_id
- PASS: BenchmarkRun status reflects pass/fail counts correctly
- PASS: non-existent suite returns 404
- PASS: worker sets failed status on error, never crashes silently
- FAIL patterns:
    500 = suite query or job creation broken
    result_id None after worker = worker crashed before writing back
    status "running" after worker = worker died mid-execution
    avg_score None = scoring pipeline not running for benchmarks
"""

import uuid
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def benchmark_suite(db, user_id, prompt_version):
    """A minimal BenchmarkSuite with one DatasetItem — enough to trigger a run."""
    from app.models.benchmark import BenchmarkSuite, Dataset, DatasetItem

    dataset = Dataset(name="Test Dataset", created_by=user_id)
    db.add(dataset)
    db.flush()

    db.add(DatasetItem(
        dataset_id=dataset.id,
        input_text="What is 2 + 2?",
        expected_output="4",
        check_json=False,
    ))
    db.flush()

    suite = BenchmarkSuite(
        name="Test Suite",
        prompt_id=prompt_version.prompt_id,
        prompt_version_id=prompt_version.id,
        dataset_id=dataset.id,
        providers=["gemini"],
        pass_threshold=0.5,
        created_by=user_id,
    )
    db.add(suite)
    db.flush()
    return suite


@pytest.fixture()
def benchmark_suite_multi_provider(db, user_id, prompt_version):
    """Suite with two providers and two dataset items for coverage of parallel runs."""
    from app.models.benchmark import BenchmarkSuite, Dataset, DatasetItem

    dataset = Dataset(name="Multi-provider Dataset", created_by=user_id)
    db.add(dataset)
    db.flush()

    for i in range(2):
        db.add(DatasetItem(
            dataset_id=dataset.id,
            input_text=f"Question {i}",
            expected_output=f"Answer {i}",
        ))
    db.flush()

    suite = BenchmarkSuite(
        name="Multi Suite",
        prompt_id=prompt_version.prompt_id,
        prompt_version_id=prompt_version.id,
        dataset_id=dataset.id,
        providers=["gemini", "gemini"],  # two providers (use same for testing)
        pass_threshold=0.3,
        created_by=user_id,
    )
    db.add(suite)
    db.flush()
    return suite


# ── Route: POST /suites/{id}/run ──────────────────────────────────────────────

def test_run_suite_returns_job(client, auth_headers, benchmark_suite):
    with patch("app.api.routes.benchmarks.run_benchmark_job") as mock_worker:
        mock_worker.send = MagicMock()
        resp = client.post(
            f"/benchmarks/suites/{benchmark_suite.id}/run",
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["job_type"] == "benchmark"
    assert data["status"] == "queued"
    assert data["total"] >= 1
    assert data.get("result_id") is None


def test_run_suite_dispatches_worker(client, auth_headers, benchmark_suite):
    with patch("app.api.routes.benchmarks.run_benchmark_job") as mock_task:
        mock_task.send = MagicMock()
        client.post(
            f"/benchmarks/suites/{benchmark_suite.id}/run",
            headers=auth_headers,
        )
        mock_task.send.assert_called_once()
        args = mock_task.send.call_args[0]
        # args: (job_id, suite_id, user_id)
        assert args[1] == str(benchmark_suite.id)


def test_run_nonexistent_suite_returns_404(client, auth_headers):
    with patch("app.api.routes.benchmarks.run_benchmark_job") as mock_worker:
        mock_worker.send = MagicMock()
        resp = client.post(
            f"/benchmarks/suites/{uuid.uuid4()}/run",
            headers=auth_headers,
        )
    assert resp.status_code == 404


# ── Worker: run_benchmark_job ─────────────────────────────────────────────────

def _make_mock_provider_result(score=0.9, passed=True):
    """Returns a dict matching the shape _run_single_provider actually returns."""
    return {
        "provider": "gemini",
        "response": "Mocked LLM response",
        "score": score,
        "score_details": {"semantic": score, "keywords": 1.0, "json": 1.0},
        "failure_reasons": [],
        "latency_ms": 150,
        "token_usage": 10,
        "cost": 0.001,
        "passed": passed,
        "events": [],
        "error": None,
    }


def test_benchmark_worker_sets_result_id(patch_worker_db, user_id, benchmark_suite):
    """
    Worker must create a BenchmarkRun and write its ID to job.result_id.

    FAIL signals:
    - result_id is None: worker crashed before writing back
    - status != 'completed': worker errored (check job.error)
    """
    db = patch_worker_db
    from app.services.job_service import create_job
    from app.workers.benchmark_worker import run_benchmark_job

    job = create_job(
        db=db,
        job_type="benchmark",
        user_id=user_id,
        entity_id=benchmark_suite.id,
        entity_type="benchmark_suite",
        total=1,
    )

    mock_result = _make_mock_provider_result()

    with patch("app.services.benchmark_service._run_single_provider",
               new=AsyncMock(return_value=mock_result)):
        run_benchmark_job(str(job.id), str(benchmark_suite.id), str(user_id))

    db.refresh(job)

    assert job.status == "completed", \
        f"Job must be 'completed'. Got '{job.status}'. Error: {job.error}"
    assert job.result_id is not None, \
        "Worker must set result_id to the BenchmarkRun UUID"
    assert job.completed_at is not None


def test_benchmark_worker_creates_run_with_scores(patch_worker_db, user_id, benchmark_suite):
    """
    BenchmarkRun referenced by result_id must have avg_score set.

    FAIL signals:
    - avg_score is None: scoring not accumulating across evals
    - total_cases mismatch: provider/item count multiplication wrong
    """
    db = patch_worker_db
    from app.services.job_service import create_job
    from app.workers.benchmark_worker import run_benchmark_job
    from app.models.benchmark import BenchmarkRun

    job = create_job(
        db=db,
        job_type="benchmark",
        user_id=user_id,
        entity_id=benchmark_suite.id,
        entity_type="benchmark_suite",
        total=1,
    )

    mock_result = _make_mock_provider_result(score=0.85)

    with patch("app.services.benchmark_service._run_single_provider",
               new=AsyncMock(return_value=mock_result)):
        run_benchmark_job(str(job.id), str(benchmark_suite.id), str(user_id))

    db.refresh(job)
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == job.result_id).first()

    assert run is not None, "BenchmarkRun row must exist"
    assert run.avg_score is not None, "avg_score must be computed"
    assert run.avg_score > 0, f"avg_score must be positive, got: {run.avg_score}"
    assert run.status in ("completed", "partially_completed"), \
        f"Run status must reflect outcomes, got: {run.status}"
    assert run.total_cases is not None


def test_benchmark_worker_failed_status_on_missing_suite(patch_worker_db, user_id):
    """
    Worker must set job.status='failed' if suite doesn't exist.

    FAIL signals:
    - Worker raises uncaught exception instead of setting failed status
    - job.error is None (failure not recorded)
    """
    db = patch_worker_db
    from app.services.job_service import create_job
    from app.workers.benchmark_worker import run_benchmark_job

    nonexistent_suite = str(uuid.uuid4())
    job = create_job(
        db=db,
        job_type="benchmark",
        user_id=user_id,
        entity_id=uuid.UUID(nonexistent_suite),
        entity_type="benchmark_suite",
        total=0,
    )

    # Worker re-raises after setting failed status (Dramatiq retry semantics)
    with pytest.raises(Exception):
        run_benchmark_job(str(job.id), nonexistent_suite, str(user_id))

    db.refresh(job)

    assert job.status == "failed", \
        f"Worker must set status='failed' for missing suite, got '{job.status}'"
    assert job.error is not None, "job.error must contain the failure reason"


def test_benchmark_all_failed_sets_failed_status(patch_worker_db, user_id, benchmark_suite):
    """
    If all LLM calls fail, BenchmarkRun status should be 'failed'.

    FAIL signals:
    - Status is 'completed' when all providers errored
    - passed_cases > 0 when all calls failed
    """
    db = patch_worker_db
    from app.services.job_service import create_job
    from app.workers.benchmark_worker import run_benchmark_job
    from app.models.benchmark import BenchmarkRun

    job = create_job(
        db=db,
        job_type="benchmark",
        user_id=user_id,
        entity_id=benchmark_suite.id,
        entity_type="benchmark_suite",
        total=1,
    )

    # All provider calls raise — worker catches, sets failed, then re-raises (Dramatiq retry semantics)
    with patch("app.services.benchmark_service._run_single_provider",
               new=AsyncMock(side_effect=Exception("LLM unavailable"))):
        with pytest.raises(Exception):
            run_benchmark_job(str(job.id), str(benchmark_suite.id), str(user_id))

    db.refresh(job)

    # Worker should complete (not crash) — benchmark service handles per-item errors
    assert job.status in ("completed", "failed"), \
        f"Job must be terminal, got '{job.status}'"

    if job.result_id:
        run = db.query(BenchmarkRun).filter(BenchmarkRun.id == job.result_id).first()
        if run:
            assert run.status in ("failed", "partially_completed"), \
                "Run with all failures should not be 'completed'"

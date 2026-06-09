"""
Integration tests — require a live Gemini API key and a running DB.

Run with:   pytest tests/ -m integration -v
Skip in CI: pytest tests/ -m "not integration"

These tests do NOT mock the LLM. They prove:
1. The real Gemini API call completes successfully
2. The evaluation worker writes result_id back to the job
3. The evaluation has a real score (not None)
4. The worker correctly transitions job: queued → running → completed
"""

import uuid
import asyncio
import pytest
from unittest.mock import patch, MagicMock


pytestmark = pytest.mark.integration


@pytest.fixture()
def real_prompt_version(db, user_id):
    """A prompt version with a simple template suitable for Gemini."""
    from app.models.prompt import Prompt, PromptVersion

    prompt = Prompt(name="Integration Test Prompt", created_by=user_id)
    db.add(prompt)
    db.flush()

    version = PromptVersion(
        prompt_id=prompt.id,
        template="Reply with exactly one word: hello",
        version=1,
    )
    db.add(version)
    db.flush()
    return version


def test_real_gemini_eval_completes(db, user_id, real_prompt_version):
    """
    Calls run_evaluation with the real Gemini provider.
    Asserts: evaluation completes with a non-null score and response.

    FAIL signals:
    - Invalid/expired GEMINI_API_KEY in .env
    - GeminiProvider raising an unhandled exception
    - Score computation returning None (scoring pipeline broken)
    """
    from app.services.eval_service import run_evaluation

    loop = asyncio.new_event_loop()
    try:
        evaluation = loop.run_until_complete(
            run_evaluation(
                db=db,
                prompt_version_id=real_prompt_version.id,
                provider_name="gemini",
                user_id=user_id,
                expected_output="hello",
                check_json=False,
            )
        )
    finally:
        loop.close()

    assert evaluation is not None
    assert evaluation.id is not None
    assert evaluation.response is not None and len(evaluation.response) > 0, \
        "Gemini must return a non-empty response"
    assert evaluation.status in ("completed", "review_required"), \
        f"Evaluation must complete, got: {evaluation.status}"
    assert evaluation.score is not None, \
        "Score must be set — scoring pipeline is broken if None"
    assert 0.0 <= evaluation.score <= 1.0, \
        f"Score must be in [0, 1], got: {evaluation.score}"
    assert evaluation.latency_ms is not None and evaluation.latency_ms > 0, \
        "Latency must be recorded"
    assert evaluation.created_by == user_id


def test_worker_writes_result_id_to_job(db, user_id, real_prompt_version):
    """
    Calls the worker function directly (not via Dramatiq broker).
    Asserts: job transitions queued → completed and result_id is set.

    FAIL signals:
    - Worker crashing before setting result_id (check job.error field)
    - Job stuck in 'running' (worker didn't commit completion)
    - result_id is None (worker wrote status but missed the result_id assignment)
    """
    from app.models.job import Job
    from app.services.job_service import create_job
    from app.workers.evaluation_worker import run_evaluation_job

    job = create_job(
        db=db,
        job_type="evaluation",
        user_id=user_id,
        entity_id=real_prompt_version.id,
        entity_type="prompt_version",
        total=1,
        metadata={"provider": "gemini"},
    )
    initial_status = job.status
    assert initial_status == "queued"

    # Call worker function directly — bypasses Dramatiq, runs synchronously
    run_evaluation_job(
        str(job.id),
        str(real_prompt_version.id),
        "gemini",
        str(user_id),
        None,
        False,
    )

    # Refresh from DB
    db.refresh(job)

    assert job.status == "completed", \
        f"Job must be 'completed'. Got '{job.status}'. Error: {job.error}"
    assert job.result_id is not None, \
        "Worker must set result_id to the evaluation UUID"
    assert job.started_at is not None, "started_at must be set by worker"
    assert job.completed_at is not None, "completed_at must be set by worker"

    # Verify the result_id points to a real evaluation
    from app.models.evaluation import Evaluation
    evaluation = db.query(Evaluation).filter(Evaluation.id == job.result_id).first()
    assert evaluation is not None, \
        "result_id must reference a real evaluation row"
    assert evaluation.score is not None, \
        "Evaluation referenced by result_id must have a score"


def test_worker_sets_failed_status_on_bad_prompt_version(db, user_id):
    """
    If the prompt version doesn't exist, the worker must set job.status='failed'
    and store an error message — never crash silently.

    FAIL signals:
    - Worker raises unhandled exception instead of catching it
    - job.status remains 'running' (worker died mid-flight)
    - job.error is None (failure mode not recorded)
    """
    from app.services.job_service import create_job
    from app.workers.evaluation_worker import run_evaluation_job

    nonexistent_version_id = str(uuid.uuid4())

    job = create_job(
        db=db,
        job_type="evaluation",
        user_id=user_id,
        entity_id=uuid.UUID(nonexistent_version_id),
        entity_type="prompt_version",
        total=1,
    )

    run_evaluation_job(
        str(job.id),
        nonexistent_version_id,
        "gemini",
        str(user_id),
    )

    db.refresh(job)

    assert job.status == "failed", \
        f"Worker must set status='failed' for missing prompt version, got '{job.status}'"
    assert job.error is not None and len(job.error) > 0, \
        "Worker must store error message in job.error"
    assert job.completed_at is not None, \
        "completed_at must be set even on failure"

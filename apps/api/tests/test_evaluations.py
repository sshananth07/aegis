"""
Tests for the evaluation lifecycle: POST /evaluations/, GET /evaluations/{id},
GET /jobs/{job_id}, and the Dramatiq worker dispatch.

What to pay attention to:
- PASS: POST returns a Job (not an Evaluation) with status "queued"
- PASS: Job is scoped to authenticated user — other users cannot access it
- PASS: GET /evaluations/{id} returns 404 for non-existent ID
- PASS: Evaluation records are scoped — one user cannot read another's evals
- PASS: Worker dispatch is called (mocked — no real Gemini calls in tests)
- FAIL patterns: 500 = missing dependency or worker import error
  422 = payload schema mismatch; job.result_id never set = worker not writing back
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock


# ── POST /evaluations/ ────────────────────────────────────────────────────────

def test_create_evaluation_returns_job(client, auth_headers, prompt_version):
    """Triggering an eval must return a Job record, not an Evaluation."""
    with patch("app.api.routes.evaluations.run_evaluation_job") as mock_worker:
        mock_worker.send = MagicMock()
        resp = client.post(
            "/evaluations/",
            json={"prompt_version_id": str(prompt_version.id), "provider": "gemini"},
            headers=auth_headers,
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "job_type" in data, "Response must be a Job object with job_type field"
    assert data["job_type"] == "evaluation"
    assert data["status"] == "queued"
    assert "id" in data
    assert data.get("result_id") is None


def test_create_evaluation_dispatches_worker(client, auth_headers, prompt_version):
    """Worker .send() must be called exactly once with the right args."""
    with patch("app.api.routes.evaluations.run_evaluation_job") as mock_task:
        mock_task.send = MagicMock()
        client.post(
            "/evaluations/",
            json={"prompt_version_id": str(prompt_version.id), "provider": "gemini"},
            headers=auth_headers,
        )
        mock_task.send.assert_called_once()
        args = mock_task.send.call_args[0]
        assert args[2] == "gemini"
        assert args[1] == str(prompt_version.id)


def test_create_evaluation_missing_provider(client, auth_headers, prompt_version):
    with patch("app.api.routes.evaluations.run_evaluation_job"):
        resp = client.post(
            "/evaluations/",
            json={"prompt_version_id": str(prompt_version.id)},  # missing provider
            headers=auth_headers,
        )
    assert resp.status_code == 422


# ── GET /evaluations/ ─────────────────────────────────────────────────────────

def test_list_evaluations_empty(client, auth_headers):
    resp = client.get("/evaluations/", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_evaluations_scoped_to_user(client, auth_headers, db, user_id, prompt_version):
    """Evaluations owned by another user must not appear in the list."""
    from app.models.evaluation import Evaluation
    from app.core.enums import EvaluationStatus

    other_user = uuid.uuid4()
    db.add(Evaluation(
        prompt_version_id=prompt_version.id,
        provider="gemini",
        status=EvaluationStatus.completed,
        created_by=other_user,
    ))
    db.flush()

    resp = client.get("/evaluations/", headers=auth_headers)
    assert resp.status_code == 200
    # TEST_USER_ID has no evals — other user's eval must not appear
    assert len(resp.json()) == 0


def test_get_evaluation_not_found(client, auth_headers):
    resp = client.get(f"/evaluations/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_get_evaluation_wrong_user(client, auth_headers, db, prompt_version):
    """An eval owned by another user must return 404."""
    from app.models.evaluation import Evaluation
    from app.core.enums import EvaluationStatus

    other_eval = Evaluation(
        prompt_version_id=prompt_version.id,
        provider="gemini",
        status=EvaluationStatus.completed,
        created_by=uuid.uuid4(),
    )
    db.add(other_eval)
    db.flush()

    resp = client.get(f"/evaluations/{other_eval.id}", headers=auth_headers)
    assert resp.status_code == 404


# ── GET /jobs/{id} ────────────────────────────────────────────────────────────

def test_get_job_after_create(client, auth_headers, prompt_version):
    """Job must be retrievable by its ID immediately after creation."""
    with patch("app.api.routes.evaluations.run_evaluation_job") as mock_task:
        mock_task.send = MagicMock()
        create = client.post(
            "/evaluations/",
            json={"prompt_version_id": str(prompt_version.id), "provider": "gemini"},
            headers=auth_headers,
        )

    job_id = create.json()["id"]
    resp = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == job_id
    assert resp.json()["status"] == "queued"


def test_get_job_wrong_user_returns_404(client, auth_headers, db, user_id):
    """A job owned by another user must not be accessible."""
    from app.models.job import Job

    other_job = Job(
        job_type="evaluation",
        created_by=uuid.uuid4(),  # different user
        status="queued",
        progress=0,
        total=1,
    )
    db.add(other_job)
    db.flush()

    resp = client.get(f"/jobs/{other_job.id}", headers=auth_headers)
    assert resp.status_code == 404

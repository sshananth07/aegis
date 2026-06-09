"""
Tests for public /v1 routes: GET /v1/traces, GET /v1/traces/{id}, GET /v1/metrics

What to pay attention to:
- PASS: valid API key reaches endpoints and gets paginated response
- PASS: missing/invalid API key gets {"error":{"code":"invalid_api_key",...}}
- PASS: metrics returns correct structure with zero values when no evals exist
- PASS: traces are scoped to the key owner — cannot read another user's traces
- PASS: rate limit headers present on every /v1 response
- FAIL patterns: 500 = unhandled exception; missing "error" key = error contract broken
"""

import uuid
import pytest


# ── Error contract (uses real API key validation) ──────────────────────────────

def test_missing_api_key_returns_error_contract(client_real_apikey):
    resp = client_real_apikey.get("/v1/traces")
    assert resp.status_code == 401
    body = resp.json()
    assert "error" in body, "Must use {error:{code,message}} contract, not {detail:...}"
    assert body["error"]["code"] == "invalid_api_key"
    assert "message" in body["error"]


def test_invalid_api_key_returns_error_contract(client_real_apikey):
    resp = client_real_apikey.get("/v1/traces", headers={"X-API-Key": "ak_totallyinvalid"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"


# ── GET /v1/traces ─────────────────────────────────────────────────────────────

def test_list_traces_empty(client, api_key_headers):
    resp = client.get("/v1/traces", headers=api_key_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data


def test_list_traces_pagination_params(client, api_key_headers):
    resp = client.get("/v1/traces?limit=10&offset=0", headers=api_key_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 10
    assert data["offset"] == 0


def test_get_trace_not_found(client, api_key_headers):
    resp = client.get(f"/v1/traces/{uuid.uuid4()}", headers=api_key_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "resource_not_found"


def test_traces_only_return_own_user(client, api_key_headers, db, user_id, prompt_version):
    """Traces from another user must not appear in the response."""
    from app.models.evaluation import Evaluation, Trace
    from app.core.enums import EvaluationStatus

    other_user = uuid.uuid4()
    # Create eval owned by other_user — uses the same prompt_version FK
    eval_ = Evaluation(
        prompt_version_id=prompt_version.id,
        provider="gemini",
        status=EvaluationStatus.completed,
        created_by=other_user,
    )
    db.add(eval_)
    db.flush()

    trace = Trace(
        evaluation_id=eval_.id,
        event_type="llm_call",
        provider="gemini",
        latency_ms=100,
    )
    db.add(trace)
    db.flush()

    resp = client.get("/v1/traces", headers=api_key_headers)
    assert resp.status_code == 200
    ids = [t["id"] for t in resp.json()["items"]]
    assert str(trace.id) not in ids, "Must not see another user's traces"


# ── GET /v1/metrics ────────────────────────────────────────────────────────────

def test_metrics_empty_user(client, api_key_headers):
    resp = client.get("/v1/metrics", headers=api_key_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_count"] == 0
    assert data["pass_rate"] == 0.0
    assert data["failure_rate"] == 0.0
    assert data["avg_latency_ms"] == 0
    assert isinstance(data["provider_distribution"], dict)
    assert isinstance(data["top_failure_reasons"], list)
    assert data["score_avg"] == 0.0


def test_metrics_with_evaluations(client, api_key_headers, db, user_id, prompt_version):
    """With evals in the DB, metrics must reflect real counts."""
    from app.models.evaluation import Evaluation
    from app.core.enums import EvaluationStatus

    for i in range(3):
        db.add(Evaluation(
            prompt_version_id=prompt_version.id,
            provider="gemini",
            status=EvaluationStatus.completed,
            score=0.9,
            latency_ms=200,
            created_by=user_id,
        ))
    db.add(Evaluation(
        prompt_version_id=prompt_version.id,
        provider="ollama",
        status=EvaluationStatus.failed,
        created_by=user_id,
    ))
    db.flush()

    resp = client.get("/v1/metrics", headers=api_key_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["evaluation_count"] == 4
    assert data["provider_distribution"]["gemini"] == 3
    assert data["provider_distribution"]["ollama"] == 1
    assert data["score_avg"] > 0


# ── Rate limit headers ─────────────────────────────────────────────────────────

def test_rate_limit_headers_present(client, api_key_headers):
    resp = client.get("/v1/metrics", headers=api_key_headers)
    assert resp.status_code == 200
    header_keys = {k.lower() for k in resp.headers}
    assert "x-ratelimit-limit" in header_keys, \
        "RateLimitHeaderMiddleware must inject X-RateLimit-Limit on /v1 responses"

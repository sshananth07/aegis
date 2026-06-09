"""
Tests for webhook management routes: POST/GET/DELETE /webhooks/ and delivery history.

What to pay attention to:
- PASS: webhook created with secret returned once
- PASS: invalid event_types are rejected (422)
- PASS: listing is paginated and ownership-scoped
- PASS: delete removes the webhook from listing
- PASS: delivery history returns correct structure
- PASS: HMAC signature is correct on trigger_webhook calls
- FAIL patterns: 500 = unhandled exception in trigger; missing secret = security gap
"""

import uuid
import json
import hmac
import hashlib
import pytest
from unittest.mock import AsyncMock, patch


VALID_WEBHOOK = {
    "url": "https://example.com/hook",
    "event_types": ["evaluation.completed"],
}


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_create_webhook_returns_secret(client, auth_headers):
    resp = client.post("/webhooks/", json=VALID_WEBHOOK, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data, "Secret must be returned on creation"
    assert len(data["secret"]) >= 32, "Secret must be at least 32 chars"
    assert data["url"] == VALID_WEBHOOK["url"]
    assert "evaluation.completed" in data["event_types"]
    assert data["active"] is True


def test_create_webhook_invalid_event_type(client, auth_headers):
    resp = client.post(
        "/webhooks/",
        json={"url": "https://example.com", "event_types": ["not.a.real.event"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, "Invalid event type must be rejected"


def test_list_webhooks_paginated(client, auth_headers):
    for i in range(2):
        client.post("/webhooks/", json={
            "url": f"https://example.com/hook-{i}",
            "event_types": ["evaluation.completed"],
        }, headers=auth_headers)

    resp = client.get("/webhooks/", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "total" in data
    assert data["total"] >= 2


def test_delete_webhook(client, auth_headers):
    create = client.post("/webhooks/", json=VALID_WEBHOOK, headers=auth_headers)
    assert create.status_code == 200
    wh_id = create.json()["id"]

    delete = client.delete(f"/webhooks/{wh_id}", headers=auth_headers)
    assert delete.status_code in (200, 204)

    listing = client.get("/webhooks/", headers=auth_headers)
    ids = [w["id"] for w in listing.json()["items"]]
    assert wh_id not in ids


def test_delete_nonexistent_webhook_returns_404(client, auth_headers):
    resp = client.delete(f"/webhooks/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_webhook_delivery_history_empty(client, auth_headers):
    create = client.post("/webhooks/", json=VALID_WEBHOOK, headers=auth_headers)
    wh_id = create.json()["id"]

    resp = client.get(f"/webhooks/{wh_id}/deliveries", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


# ── HMAC signature ────────────────────────────────────────────────────────────

def test_trigger_webhook_hmac_signature(db, user_id):
    """
    _deliver must include X-Aegis-Signature = sha256=hmac(secret, body).
    Calls _deliver directly (bypasses asyncio.create_task) with a mocked httpx client.
    """
    import asyncio
    import httpx
    from app.models.webhook import Webhook
    from app.services.webhook_service import _deliver

    secret = "a" * 64
    wh = Webhook(
        user_id=user_id,
        url="https://example.com/hook",
        event_types=["evaluation.completed"],
        secret=secret,
        active=True,
    )
    db.add(wh)
    db.flush()

    payload = {"evaluation_id": str(uuid.uuid4()), "status": "completed", "score": 0.95}
    captured = {}

    async def fake_post(self, url, *, content, headers):
        captured["headers"] = headers
        captured["body"] = content
        class FakeResp:
            status_code = 200
        return FakeResp()

    with patch.object(httpx.AsyncClient, "post", new=fake_post):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_deliver(db, wh, "evaluation.completed", payload))
        finally:
            loop.close()

    assert "X-Aegis-Signature" in captured.get("headers", {}), \
        "Webhook delivery must include X-Aegis-Signature header"

    body_bytes = captured["body"] if isinstance(captured["body"], bytes) \
        else captured["body"].encode()
    expected_sig = "sha256=" + hmac.new(
        secret.encode(), body_bytes, hashlib.sha256
    ).hexdigest()
    assert captured["headers"]["X-Aegis-Signature"] == expected_sig, \
        "HMAC signature must match sha256=hex(hmac(secret, body))"

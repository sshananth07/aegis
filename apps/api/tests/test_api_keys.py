"""
Tests for API key management routes: POST/GET/DELETE /api-keys/

What to pay attention to:
- PASS: key is returned once on creation (plaintext never stored)
- PASS: listing shows key_prefix, never the full key
- PASS: revoked key is rejected on subsequent requests
- PASS: invalid scope names are rejected with 422
- FAIL patterns: 422 = bad request shape; 401 = auth broken; 500 = unhandled exception
"""

import pytest


CREATE_PAYLOAD = {
    "name": "ci-key",
    "scopes": ["traces:read", "metrics:read"],
}


def test_create_api_key_returns_plaintext(client, auth_headers):
    resp = client.post("/api-keys/", json=CREATE_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"].startswith("ak_"), "Plaintext key must start with ak_"
    assert "key_hash" not in data, "key_hash must never be exposed"
    assert data["key_prefix"] == data["key"][:16]
    assert data["name"] == "ci-key"
    assert "traces:read" in data["scopes"]


def test_create_api_key_plaintext_shown_once(client, auth_headers):
    """After creation, listing must not expose the plaintext key."""
    create = client.post("/api-keys/", json=CREATE_PAYLOAD, headers=auth_headers)
    assert create.status_code == 200

    listing = client.get("/api-keys/", headers=auth_headers)
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) >= 1
    for item in items:
        assert "key" not in item, "Plaintext key must not appear in list"
        assert item.get("key_prefix"), "key_prefix must be present"


def test_list_api_keys_pagination(client, auth_headers):
    for i in range(3):
        client.post("/api-keys/", json={"name": f"key-{i}", "scopes": ["traces:read"]},
                    headers=auth_headers)

    resp = client.get("/api-keys/?limit=2&offset=0", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "total" in data
    assert len(data["items"]) <= 2
    assert data["total"] >= 3


def test_revoke_api_key(client, auth_headers):
    create = client.post("/api-keys/", json=CREATE_PAYLOAD, headers=auth_headers)
    assert create.status_code == 200
    key_id = create.json()["id"]

    delete = client.delete(f"/api-keys/{key_id}", headers=auth_headers)
    assert delete.status_code in (200, 204)

    # Revoked key appears in listing but must be marked revoked=True
    listing = client.get("/api-keys/", headers=auth_headers)
    key_in_list = next((k for k in listing.json()["items"] if k["id"] == key_id), None)
    assert key_in_list is not None
    assert key_in_list["revoked"] is True, "Revoked key must have revoked=True"


def test_revoke_nonexistent_key_returns_404(client, auth_headers):
    import uuid
    resp = client.delete(f"/api-keys/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_invalid_scope_rejected(client, auth_headers):
    resp = client.post(
        "/api-keys/",
        json={"name": "bad-key", "scopes": ["not:a:real:scope"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422, "Invalid scope must be rejected with 422"


def test_revoked_key_cannot_access_v1(client_real_apikey, db, user_id, auth_headers):
    """Create a key via service, revoke it, confirm real validation rejects it."""
    from app.services.api_key_service import create_api_key, revoke_api_key

    key_obj, plaintext = create_api_key(db, user_id, "revoke-test", ["traces:read"])
    # commit so validate_api_key can see the row (client_real_apikey uses same db)
    db.flush()

    revoke_api_key(db, key_obj.id, user_id)
    db.flush()

    # client_real_apikey does NOT override get_api_key_user — real validation runs
    resp = client_real_apikey.get("/v1/traces", headers={"X-API-Key": plaintext})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_api_key"

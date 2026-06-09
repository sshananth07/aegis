"""
Test fixtures.

Local dev:  reads DATABASE_URL from .env (your Supabase dev DB).
            Tests run in transactions that are rolled back — no permanent data.
CI:         DATABASE_URL is set via GitHub Actions secret.

Auth is bypassed via dependency_overrides — no live Supabase needed.
Rate limiting is disabled in the test client.
"""

import os
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

os.environ.setdefault("SUPABASE_URL", "https://placeholder.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "placeholder-anon-key")
os.environ.setdefault("GEMINI_API_KEY", "placeholder-gemini-key")

TEST_USER_ID = str(uuid.uuid4())

from app.main import app  # noqa: E402
from app.db.base import Base, get_db  # noqa: E402
from app.core.auth import get_current_user, get_api_key_user  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402


# ── Engine ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def SessionFactory(db_engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=db_engine)


# ── Per-test DB session with rollback ──────────────────────────────────────────

@pytest.fixture()
def db(db_engine, SessionFactory):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = SessionFactory(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


# ── Client with full auth + rate-limit bypass ──────────────────────────────────

@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    def override_get_current_user():
        return {"sub": TEST_USER_ID}

    def override_get_api_key_user():
        return (TEST_USER_ID, ["evaluations:write", "benchmarks:write",
                               "traces:read", "metrics:read", "webhooks:write"])

    # Reset rate limiter counters so tests don't hit 429
    limiter.reset()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_api_key_user] = override_get_api_key_user

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ── Client with JWT auth override only (real API key validation) ───────────────

@pytest.fixture()
def client_real_apikey(db):
    """Use this when testing API key validation — get_api_key_user is NOT overridden."""
    def override_get_db():
        yield db

    def override_get_current_user():
        return {"sub": TEST_USER_ID}

    limiter.reset()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    # get_api_key_user is intentionally NOT overridden

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ── Helpers ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.UUID(TEST_USER_ID)


@pytest.fixture()
def auth_headers() -> dict:
    return {"Authorization": "Bearer test-token", "Content-Type": "application/json"}


@pytest.fixture()
def api_key_headers(client, auth_headers) -> dict:
    resp = client.post(
        "/api-keys/",
        json={"name": "test-key", "scopes": ["traces:read", "metrics:read",
                                               "evaluations:write", "webhooks:write"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, f"api_key_headers fixture failed: {resp.text}"
    return {"X-API-Key": resp.json()["key"]}


@pytest.fixture()
def prompt_version(db, user_id):
    """A real Prompt + PromptVersion row — needed for Evaluations (FK constraint)."""
    from app.models.prompt import Prompt, PromptVersion
    prompt = Prompt(name="Test Prompt", created_by=user_id)
    db.add(prompt)
    db.flush()
    version = PromptVersion(
        prompt_id=prompt.id,
        template="You are a helpful assistant.",
        version=1,
    )
    db.add(version)
    db.flush()
    return version

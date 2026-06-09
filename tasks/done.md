# Completed Work Log

A record of everything fixed and implemented, newest first.

---

## 2026-06-08

### Initialize CLAUDE.md
- Created `CLAUDE.md` with project overview, commands, architecture, data models, environment variables, and conventions for the Aegis monorepo.

### Add Workflow Rules to CLAUDE.md
- Added **Workflow & Behavior Rules** section covering: plan mode, subagent strategy, self-improvement loop (`tasks/lessons.md`), verification gates, autonomous bug fixing, and minimal-impact code quality rules.

### Create tasks/ folder
- Created `tasks/todo.md` (planning), `tasks/lessons.md` (self-improvement), and `tasks/done.md` (this file) for persistent session tracking.

### Phase 5 — Developer Platform (9 units, all merged to main)
Transformed Aegis from a web-only app into a developer platform:
- **Unit 1**: `APIKey` SQLAlchemy model, Pydantic schemas (`APIKeyCreate`, `APIKeyResponse`, `APIKeyCreateResponse`), Alembic migration. Scopes: `evaluations:write`, `benchmarks:write`, `traces:read`, `metrics:read`, `webhooks:write`. Uses JSONB for scopes.
- **Unit 2**: `api_key_service.py` (create/validate/revoke/list), `get_api_key_user` + `require_scope` FastAPI dependencies in `auth.py`, `RateLimitHeaderMiddleware` injecting `X-RateLimit-*` headers on `/v1` responses.
- **Unit 3**: JWT-authenticated API key management routes (`POST/GET/DELETE /api-keys/`), registered in `main.py`. FastAPI app metadata updated (`title`, `version`, `/docs`, `/redoc`, `/v1/openapi.json`).
- **Unit 4**: `APIUsage` and `AuditEvent` models + migrations, `audit_service.py` fire-and-forget `log_event()`/`log_usage()`.
- **Unit 5**: Public `/v1` router — `POST/GET /v1/evaluations`, `POST/GET /v1/benchmarks/run`. Idempotency-Key header support (Redis-backed, 24h TTL). Job model + workers + broker.
- **Unit 6**: `GET /v1/traces`, `GET /v1/traces/{id}`, `GET /v1/metrics`. `AegisAPIException` error contract (`{error:{code,message}}`), registered exception handler. 8 error code factory functions.
- **Unit 7**: `Webhook` + `WebhookDelivery` models + migration, `webhook_service.py` (fire-and-forget HMAC-SHA256 delivery), JWT-authenticated webhook management routes + delivery history. `trigger_webhook` hooked into `eval_service` and `benchmark_service`.
- **Unit 8**: Frontend `/api-keys` page — list keys, create form with scope checkboxes, one-time key reveal dialog, revoke confirmation modal. Sidebar nav item added.
- **Unit 9**: Frontend `/webhooks` page — list webhooks, create form, one-time secret dialog, delete modal, per-webhook delivery history (lazily fetched). Sidebar nav item added.

### Phase 5 — Post-merge fixes and E2E verification (2026-06-09)
Resolved all issues found during smoke testing after merging all 9 PRs:
- **Migration chain**: Linearized 4 conflicting migrations (duplicate `a1b2c3d4e5f6` revision, orphaned `8f9e83ef1d00` DB revision). Created stub migration + updated down_revision pointers.
- **public.py auth stub**: Unit 6 merge overwrote `get_api_key_user` with a stub that always raised `invalid_api_key`. Fixed by importing real dependency.
- **Tuple unpacking**: All `/v1` route handlers updated to `api_key_data: tuple = Depends(get_api_key_user)` then `user_id, _ = api_key_data`.
- **Error contract**: `get_api_key_user` now raises `AegisAPIException` (not `HTTPException`) so errors return `{"error":{...}}` not `{"detail":"..."}`.
- **Sidebar.tsx**: Fixed missing commas in lucide-react imports (`Globe`, `Key`).
- **Smoke tests**: Created `test_phase5.ps1` (12 API key tests), `test_webhooks.ps1` (webhook lifecycle + delivery), `test_eval_trigger.ps1` (end-to-end eval → webhook fire).
- **E2E result**: Evaluation completed (score 1.0, Gemini), webhook delivery confirmed on webhook.site with HMAC-SHA256 signature.

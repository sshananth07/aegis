# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Workflow & Behavior Rules

### Planning
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions). Write a detailed spec upfront.
- If something goes sideways mid-task, STOP and re-plan immediately — don't keep pushing.
- Write the plan to `tasks/todo.md` with checkable items, then check in before starting implementation.
- Mark items complete as you go; when done, move a summary entry to `tasks/done.md`.

### Subagents
- Use subagents liberally to keep the main context window clean.
- Offload research, exploration, and parallel analysis to subagents.
- One focused task per subagent — don't bundle unrelated queries.

### Task Files
| File | Purpose |
|---|---|
| `tasks/todo.md` | Active plan — checkable items for the current task |
| `tasks/done.md` | Completed work log — append a summary after every task |
| `tasks/lessons.md` | Self-improvement log — rules derived from user corrections |

### Self-Improvement
- After ANY correction from the user, update `tasks/lessons.md` with the pattern and a rule to prevent it recurring.
- Review `tasks/lessons.md` at the start of each session for relevant lessons.

### Verification
- Never mark a task complete without proving it works (run tests, check logs, demonstrate correctness).
- When relevant, diff behavior between `main` and your changes before declaring done.
- Ask: "Would a staff engineer approve this PR?"

### Bug Fixing
- When given a bug report: fix it autonomously. Point at logs/errors/failing tests and resolve them.
- Find root causes — no temporary fixes or workarounds.

### Code Quality
- Make every change as simple as possible. Minimize code touched.
- For non-trivial changes, pause and ask "is there a more elegant solution?" before finalizing.
- If a fix feels hacky, implement the elegant solution instead.
- Skip elegance checks for simple, obvious one-liners.

---

## Overview

Aegis is an AI evaluation and benchmarking platform. Users create versioned prompts, run them against multiple LLM providers (Gemini, Ollama), and analyze results via scoring, traces, and dashboards. The monorepo has a **FastAPI** backend and a **Next.js** frontend, orchestrated with Turborepo + pnpm.

---

## Commands

### Monorepo (root)
```bash
pnpm install          # Install all dependencies
pnpm run dev          # Start API + Web concurrently (via Turbo)
pnpm run build        # Build all apps
pnpm run lint         # Lint all workspaces
```

### Backend (`apps/api`)
```bash
make venv             # Create Python venv + install requirements
make dev              # Start FastAPI on port 8000 with hot-reload
make migrate          # Apply Alembic migrations (upgrade head)
make migration name="add_foo"  # Generate a new migration
```

On Windows (no make):
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

### Frontend (`apps/web`)
```bash
npm run dev           # Next.js dev server on port 3000
npm run build         # Production build
npm run lint          # ESLint
```

### Docker
```bash
docker compose up -d                                    # API + Web (production images)
docker compose -f docker-compose.local.yml up -d       # + Redis + Ollama + Worker
```

---

## Architecture

### Request Flow
```
Next.js (port 3000)
  └─ apiFetch() [lib/api.ts] – attaches Supabase JWT
       └─ FastAPI (port 8000)
            ├─ auth.py – validates JWT against Supabase
            ├─ Route → Service → SQLAlchemy (PostgreSQL)
            └─ Long-running ops: Job record → Dramatiq task → Redis → Worker process
```

Real-time updates go through **Supabase Realtime** subscriptions (not polling FastAPI). The frontend `useRealtime*` hooks subscribe to table change events; `useJob.ts` handles the fallback REST-polling case.

### Key Abstractions

**Backend layers** (in order of dependency):
1. `app/providers/` – LLM adapters (`GeminiProvider`, `OllamaProvider`) behind a `ProviderRouter` with a Gemini → Ollama fallback chain
2. `app/services/` – Business logic (`eval_service`, `benchmark_service`, `scoring`, `comparison_service`, etc.)
3. `app/api/routes/` – Thin FastAPI route handlers; delegate immediately to services
4. `app/workers/` – Dramatiq tasks for async evaluation execution
5. `app/models/` – SQLAlchemy ORM models (UUID PKs throughout)
6. `app/schemas/` – Pydantic request/response DTOs (separate from ORM models)
7. `app/core/` – Cross-cutting concerns: auth, config, caching (Redis), rate limiting (SlowAPI), logging (structlog)

**Frontend layers:**
- `src/lib/api.ts` – `apiFetch` utility: injects JWT, handles errors uniformly
- `src/hooks/` – Data-fetching and realtime hooks (React Query + Supabase subscriptions)
- `src/app/` – Next.js app router pages; each page fetches its own data via hooks
- `src/components/ui/` – shadcn/ui wrappers; `src/components/` – feature components
- `packages/types/` – Shared TypeScript types (`@aegis/types`) imported by the web app

### Data Models (core relationships)
```
Prompt → PromptVersion
BenchmarkSuite → Dataset → DatasetItem
BenchmarkSuite → BenchmarkRun → EvaluationGroup → Evaluation → Trace
Evaluation → Job (async tracking)
Evaluation → Review (manual review queue)
User → APIKey (programmatic access)
User → Webhook → WebhookDelivery (event delivery history)
APIKey → APIUsage (per-key usage tracking)
User → AuditEvent (structured audit log)
```

### Scoring Pipeline (`app/services/scoring.py`)
Each evaluation produces a score from three components:
- Semantic similarity vs. expected output (embeddings)
- Keyword coverage (`required_keywords` on DatasetItem)
- JSON field validation (`required_json_fields` on DatasetItem)

### Background Jobs
Dramatiq + Redis broker. The `apps/api/app/workers/` directory contains worker tasks. A separate **Worker** process (`Dockerfile.worker`) consumes these tasks. Job status is tracked in the `Job` model and surfaced via `/api/jobs/{job_id}`.

---

## Environment Variables

**API (required):**
| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase public anon key |
| `SUPABASE_JWT_SECRET` | JWT secret for token validation |
| `GEMINI_API_KEY` | Google Gemini API access |
| `CORS_ORIGINS` | Comma-separated allowed origins |

**API (optional):**
| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_ENABLED` | `false` | Enable local Ollama fallback |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama endpoint |
| `REDIS_URL` | `redis://localhost:6379` | Broker + cache |

**Frontend:**
| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_SUPABASE_URL` | Public Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public Supabase anon key |

See `.env.example` for the full list.

---

## Conventions

- **UUID primary keys** on all SQLAlchemy models
- **`created_by`** field on all user-owned resources; route handlers filter by authenticated user
- **Service layer** holds all business logic — routes are thin wrappers
- **Pydantic schemas** (`app/schemas/`) are separate from ORM models (`app/models/`)
- **Async throughout**: FastAPI async routes, `httpx.AsyncClient` for provider calls, Dramatiq for background work
- **Structured logging** via `structlog` (JSON output)
- Status enums (`queued` → `running` → `completed` | `failed`) used for Job and BenchmarkRun tracking
- JSONB columns used for flexible metadata and all array fields (score details, scopes, event_types, etc.)
- TypeScript path alias: `@/*` maps to `src/*` in the web app
- **Pagination standard**: all list endpoints return `{ items, total, limit, offset }`
- **Error contract on `/v1`**: `{ "error": { "code": "...", "message": "..." } }` — use `AegisAPIException` from `app.core.exceptions`
- **API key auth**: `get_api_key_user` dependency in `auth.py` returns `(user_id_str, scopes)`; use `require_scope("scope:name")` factory for scope enforcement
- **Webhooks**: fire-and-forget via `asyncio.create_task`; HMAC-SHA256 signed with `X-Aegis-Signature` header; trigger via `webhook_service.trigger_webhook(db, user_id, event_type, payload)`
- **Audit logging**: fire-and-forget `audit_service.log_event()` / `log_usage()` — swallow all exceptions, never block the request path

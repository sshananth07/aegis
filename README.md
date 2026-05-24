# Aegis

Aegis is an AI evaluation and benchmarking platform. It provides tools to manage prompts, run evaluations, collect traces, and perform real-time benchmarking against various models (including Gemini and local Ollama instances).

This project is structured as a monorepo using [Turborepo](https://turbo.build/) and `pnpm`.

## Project Structure

- **`apps/api`**: FastAPI backend that handles evaluations, benchmarks, metrics, and interactions with AI models.
- **`apps/web`**: Next.js (React) front-end web application with a real-time dashboard and playgrounds.
- **`packages/types`**: Shared types package utilized by both the API and the Web app.

## Prerequisites

- [Node.js](https://nodejs.org/) (v18 or newer recommended)
- [pnpm](https://pnpm.io/) (`npm install -g pnpm`)
- [Python 3](https://www.python.org/)
- [Docker & Docker Compose](https://www.docker.com/) (For database and infrastructure)

## Getting Started

### 1. Install Dependencies

Install Node packages at the root:
```bash
pnpm install
```

### 2. Configure the Backend (API)

Navigate to `apps/api` to set up the Python environment:
```bash
cd apps/api
make venv
```
*(On Windows, run `python -m venv .venv` and install from `requirements.txt` manually. See `apps/api/README.md` for details).*

### 3. Run the Development Servers

From the root of the project, use Turborepo to start both the API and Web applications concurrently:
```bash
pnpm run dev
```

Alternatively, you can run and manage infrastructure using the provided Docker compose file:
```bash
docker compose up -d
```

### 4. Database Migrations

The backend uses `alembic` for database migrations. To apply the latest migrations:
```bash
cd apps/api
alembic upgrade head
```

## Features

- **Prompt Management**: Organize and version control your Prompts.
- **Evaluation**: Run complex reviews and scoring pipelines.
- **Benchmarks**: Compare performance across different LLMs automatically.
- **Traces**: Full observability of LLM chains and operations.

## Scripts Context

From the root directory:
- `pnpm run dev` - Starts development servers for all workspaces.
- `pnpm run build` - Builds all applications and packages.
- `pnpm run lint` - Runs linting across all workspaces.

## Deployment

Refer to `docs/deployment.md` for detailed instructions on deploying the Aegis platform.

#!/bin/bash
set -e

echo "Starting Aegis API..."

# Skip migrations in Docker - DB already migrated via local alembic
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
#!/bin/bash
set -e

echo "Starting Aegis API..."
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
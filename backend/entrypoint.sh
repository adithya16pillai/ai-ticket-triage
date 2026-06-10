#!/usr/bin/env sh
set -e

# Wait for Postgres, run migrations, then serve.
echo "Running database migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

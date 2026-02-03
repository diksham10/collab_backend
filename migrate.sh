#!/bin/sh
set -e

echo "Waiting for Postgres to be ready..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  echo "Postgres is not ready yet..."
  sleep 2
done

# Give Postgres an extra 2 seconds to settle
sleep 2

echo "Postgres is ready. Running migrations..."

# Export DATABASE_URL dynamically from environment
export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "Using DATABASE_URL=$DATABASE_URL"

# Run Alembic upgrade
uv run alembic upgrade head

echo "Migrations finished!"

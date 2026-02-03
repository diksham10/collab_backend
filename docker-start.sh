#!/bin/bash
set -e

echo "🚀 Starting collab-backend with Docker Compose..."

# Clean up old containers and volumes
echo "🧹 Cleaning up old containers..."
docker compose down -v

# Build fresh images
echo "🏗️  Building Docker images..."
docker compose build --no-cache

# Start postgres and wait for it to be healthy
echo "🗄️  Starting PostgreSQL..."
docker compose up -d postgres redis

# Wait for postgres to be healthy
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Generate migration if needed
echo "📝 Generating Alembic migration..."
docker compose run --rm -v $(pwd)/alembic:/app/alembic migrate sh -c "uv run alembic revision --autogenerate -m 'init'"

# Run migrations
echo "⬆️  Running migrations..."
docker compose up migrate

# Verify tables were created
echo "✅ Verifying database tables..."
docker compose exec postgres psql -U test -d test -c "\dt"

# Start the API
echo "🚀 Starting FastAPI application..."
docker compose up -d api

# Show logs
echo "📋 Showing API logs (Ctrl+C to exit)..."
docker compose logs -f api

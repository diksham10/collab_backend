#!/bin/bash
# Simple commands to manage the Docker setup

case "$1" in
  start)
    echo "🚀 Starting all services (development mode)..."
    docker compose up -d
    docker compose logs -f api
    ;;
  
  prod)
    echo "🚀 Starting all services (production mode with Nginx)..."
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
    docker compose logs -f nginx
    ;;
  
  stop)
    echo "🛑 Stopping all services..."
    docker compose down
    ;;
  
  restart)
    echo "🔄 Restarting API service..."
    docker compose restart api
    docker compose logs -f api
    ;;
  
  migrate)
    echo "📝 Creating migration..."
    docker compose run --rm migrate sh -c "uv run alembic revision --autogenerate -m '${2:-migration}'"
    echo "⬆️  Applying migration..."
    docker compose up migrate
    ;;
  
  logs)
    docker compose logs -f ${2:-api}
    ;;
  
  db)
    echo "🗄️  Connecting to database..."
    docker compose exec postgres psql -U test -d test
    ;;
  
  clean)
    echo "🧹 Cleaning everything (including volumes)..."
    docker compose down -v
    ;;
  
  build)
    echo "🏗️  Building images..."
    docker compose build ${2:---no-cache}
    ;;
  
  shell)
    echo "💻 Opening shell in ${2:-api} container..."
    docker compose exec ${2:-api} sh
    ;;
  
  *)
    echo "Usage: $0 {start|prod|stop|restart|migrate|logs|db|clean|build|shell}"
    echo ""
    echo "Commands:"
    echo "  start   - Start all services (development)"
    echo "  prod    - Start with Nginx (production)"
    echo "  stop    - Stop all services"
    echo "  restart - Restart API service"
    echo "  migrate - Create and apply migration"
    echo "  logs    - Show logs (optional: service name)"
    echo "  db      - Connect to database"
    echo "  clean   - Remove all containers and volumes"
    echo "  build   - Rebuild Docker images"
    echo "  shell   - Open shell in container"
    exit 1
    ;;
esac

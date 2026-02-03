# Docker Quick Reference

## Development Mode (Fast Reloading)
```bash
# Start all services
./docker.sh start

# Or manually
docker compose up -d
```

Access: http://localhost:8000

## Production Mode (with Nginx)
```bash
./docker.sh prod
```

Access: http://localhost (port 80)

## Common Commands
```bash
# View logs
./docker.sh logs api

# Database shell
./docker.sh db

# Create + apply migration
./docker.sh migrate "add_new_field"

# Restart API
./docker.sh restart

# Stop everything
./docker.sh stop

# Clean everything (including data)
./docker.sh clean
```

## Why Reloading Was Slow

### Problems Fixed:
1. **Removed alembic volume mount** - API doesn't need it, only migrate service does
2. **Added `:cached` flag** - Optimizes file sync on macOS/Windows
3. **Volume only watches `/app/src`** - Not the entire project

### Before:
- Watched: `./src` + `./alembic` + all `__pycache__` files
- Reload time: 3-5 seconds

### After:
- Watches: `./src` only (cached)
- Reload time: ~1 second

## Nginx Setup

Added `nginx.conf` and `docker-compose.prod.yml` for production:
- Rate limiting (10 req/s)
- Security headers
- WebSocket support
- Reverse proxy to FastAPI

Use `./docker.sh prod` to start with Nginx.

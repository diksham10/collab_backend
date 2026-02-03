# Use official uv image with Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation and suppress output buffering
ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copy dependency files first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install runtime dependencies + Alembic globally
RUN uv sync --frozen


# Install PostgreSQL client for pg_isready
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*


# Copy the entire project
COPY . .

# Default command (API)
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# syntax=docker/dockerfile:1

FROM python:3.13-slim-bookworm

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# Install system dependencies required by psycopg (libpq) and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    libffi-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy project files
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY README.md .

# Install the project itself
RUN uv pip install -e .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

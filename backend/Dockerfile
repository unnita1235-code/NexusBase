# ─── NexusBase Backend ────────────────────────────────────────
# Multi-stage build: install deps, then run uvicorn
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

WORKDIR /app

# System deps for PyMuPDF, asyncpg, and cryptography
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency spec first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy application code
COPY . .

# The packages directory is mounted via docker-compose volumes
ENV PYTHONPATH="/app:/packages"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]

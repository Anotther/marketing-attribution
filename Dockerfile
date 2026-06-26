FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Minimal build deps for pyarrow/duckdb wheels; kept slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source.
COPY src/ ./src/
COPY pyproject.toml ./

# Non-root user for runtime safety.
RUN useradd --create-home --uid 10001 attribution
RUN mkdir -p /app/data /app/credentials \
    && chown -R attribution:attribution /app
USER attribution

ENV DATA_DIR=/app/data \
    LOG_LEVEL=INFO

# `config` module validates ENV at runtime; default entrypoint runs the pipeline.
ENTRYPOINT ["python", "-m", "src.main"]

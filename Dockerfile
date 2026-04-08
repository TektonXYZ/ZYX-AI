# Dockerfile for ZYX AI
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# Copy application code
COPY src/ ./src/

# Production stage
FROM base as production

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "zyx_ai.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM base as development

# Install additional dev dependencies
RUN pip install pytest pytest-cov black isort flake8 mypy

# Expose port
EXPOSE 8000

# Run with reload for development
CMD ["uvicorn", "zyx_ai.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

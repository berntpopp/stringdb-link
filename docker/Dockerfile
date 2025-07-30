# Multi-stage Dockerfile for StringDB-Link
# Optimized for both development and production deployment

# --- Builder Stage ---
# This stage installs all dependencies and creates a clean Python environment
FROM python:3.11-slim AS builder

# Set environment variables for optimal Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for better dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency files first for better layer caching
WORKDIR /app
COPY pyproject.toml ./

# Install dependencies in the virtual environment
# Use --no-deps to prevent pip from installing development dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .[production]

# --- Production Stage ---
# This stage creates the final, minimal production image
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --system app || true && \
    useradd --system --gid app --home /home/app --create-home app || true

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /home/app/web

# Copy application source code
COPY --chown=app:app ./stringdb_link ./stringdb_link
COPY --chown=app:app ./server.py ./mcp_server.py ./pyproject.toml ./README.md ./
COPY --chown=app:app ./docker/gunicorn_conf.py ./

# Install the application package
RUN /opt/venv/bin/pip install -e . --no-deps

# Switch to non-root user
USER app

# Expose the application port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1

# Default production command using Gunicorn with Uvicorn workers
CMD ["gunicorn", "-c", "gunicorn_conf.py", "stringdb_link.app:app"]
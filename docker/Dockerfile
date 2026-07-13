# Multi-stage Dockerfile for StringDB-Link
# Optimized for both development and production deployment

# --- Builder Stage ---
# This stage installs all dependencies and creates a clean Python environment
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS builder

# Set environment variables for optimal Python behavior
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment for better dependency isolation
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

# Pin uv to a digest-pinned build of the official image instead of a floating
# installer bootstrap (F-19) — reproducible, supply-chain-hardened.
COPY --from=ghcr.io/astral-sh/uv:0.8.7@sha256:1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab /uv /usr/local/bin/uv

# Copy dependency files first for better layer caching
WORKDIR /app
COPY uv.lock pyproject.toml README.md ./

# Install dependencies in the virtual environment
# Install production dependencies only
RUN uv sync --frozen --no-dev --active --no-install-project

# --- Prepared Stage ---
# This stage prepares the runtime filesystem before the scratch production image
FROM python:3.12-slim@sha256:423ed6ab25b1921a477529254bfeeabf5855151dc2c3141699a1bfc852199fbf AS prepared

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web" \
    HOST=0.0.0.0 \
    PORT=8000 \
    TRANSPORT=unified

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
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

RUN rm -rf /root/.cache/pip /usr/local/lib/python*/ensurepip \
    && find / -xdev -type d -name __pycache__ -prune -exec rm -rf '{}' + \
    && find / -xdev -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
RUN find / -xdev -perm /6000 -exec chmod a-s '{}' + \
    && test -z "$(find / -xdev -perm /6000 -print -quit)"
RUN actual="$(find / -xdev -type f -links +1 -printf '%i %p\n' | sort -k2,2)" \
    && expected="$(printf '%s %s\n%s %s\n' \
         "$(stat -c '%i' /usr/bin/perl)" /usr/bin/perl \
         "$(stat -c '%i' /usr/bin/perl5.40.1)" /usr/bin/perl5.40.1 | sort -k2,2)" \
    && { test "$actual" = "$expected" || { printf 'unexpected hardlinks:\n%s\n' "$actual"; exit 1; }; } \
    && rm -f /usr/bin/perl5.40.1

# --- Production Stage ---
FROM scratch AS production
COPY --from=prepared / /

ARG APP_VERSION=0.0.0
ARG VCS_REF=unknown
ARG BUILD_DATE=1970-01-01T00:00:00Z
LABEL org.opencontainers.image.title="stringdb-link" \
      org.opencontainers.image.description="GeneFoundry MCP/API server for STRING protein interaction research data" \
      org.opencontainers.image.url="https://github.com/berntpopp/stringdb-link" \
      org.opencontainers.image.source="https://github.com/berntpopp/stringdb-link" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="GeneFoundry"
ENV VCS_REF="${VCS_REF}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web" \
    HOST=0.0.0.0 \
    PORT=8000 \
    TRANSPORT=unified

# Set working directory
WORKDIR /home/app/web

# Switch to non-root user
USER app

# Expose the application port
EXPOSE 8000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Default production command exposes REST plus hosted MCP.
CMD ["stringdb-link", "server", "--transport", "unified", "--host", "0.0.0.0", "--port", "8000"]

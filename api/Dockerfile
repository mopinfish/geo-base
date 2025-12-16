# =============================================================================
# geo-base API Server Dockerfile
# =============================================================================
# GDAL/rasterio対応のFastAPIタイルサーバー
# 
# Features:
# - Python 3.11 + GDAL 3.8
# - rasterio, rio-tiler for raster tile generation
# - PostGIS compatible vector tile generation
# - uv for fast dependency management
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image with GDAL
# -----------------------------------------------------------------------------
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.8.5 AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # uv settings
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install Python and build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# -----------------------------------------------------------------------------
# Stage 2: Builder - Install dependencies with uv
# -----------------------------------------------------------------------------
FROM base AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies (excluding dev dependencies)
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 3: Production image
# -----------------------------------------------------------------------------
FROM base AS production

# Copy uv for runtime use (optional, for debugging)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY lib/ ./lib/
COPY index.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port (Fly.io uses 8080 by default)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/api/health || exit 1

# Run the application
# Note: Fly.io sets PORT environment variable
CMD ["sh", "-c", "uvicorn lib.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

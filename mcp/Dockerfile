# geo-base MCP Server Dockerfile
# For deployment on Fly.io

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# MCP Server configuration
ENV MCP_TRANSPORT=sse
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for better caching)
# README.md is needed because pyproject.toml references it
COPY pyproject.toml ./
COPY uv.lock ./
COPY README.md ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for HTTP transport
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run MCP server with SSE transport for remote connections
CMD ["uv", "run", "python", "server.py"]

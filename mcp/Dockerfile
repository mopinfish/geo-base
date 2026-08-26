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

# Copy ALL application files first
# (uv sync needs source files to install the local package)
COPY . .

# Install dependencies into .venv
RUN uv sync --frozen --no-dev

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for HTTP transport
EXPOSE 8080

# Health check - use /sse endpoint since FastMCP doesn't have /health by default
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/sse -o /dev/null -s -w '%{http_code}' | grep -q '200' || exit 1

# Run MCP server directly using the installed venv
CMD ["/app/.venv/bin/python", "server.py"]

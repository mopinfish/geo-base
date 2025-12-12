# geo-base MCP Server Dockerfile
# For deployment on Fly.io

FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first (for better caching)
COPY pyproject.toml ./
COPY uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port for HTTP transport (if needed)
EXPOSE 8080

# Default command: run MCP server with stdio transport
# For Claude Desktop local connection, use stdio transport
# For remote connection via Fly.io, you may need to configure HTTP/SSE transport
CMD ["uv", "run", "python", "server.py"]

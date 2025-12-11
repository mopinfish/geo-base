#!/bin/bash

# geo-base Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up geo-base development environment..."

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi
echo "✅ Python $(python3 --version)"

# Check uv
if ! command -v uv &> /dev/null; then
    echo "⚠️  uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
fi
echo "✅ uv installed"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi
echo "✅ Docker installed"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available"
    exit 1
fi
echo "✅ Docker Compose installed"

# Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Create necessary directories
echo ""
echo "📁 Creating directories..."
mkdir -p api/data
mkdir -p app/public
echo "✅ Directories created"

# Copy environment files if they don't exist
echo ""
echo "📝 Setting up environment files..."

if [ ! -f "api/.env" ]; then
    cp api/.env.example api/.env
    echo "✅ Created api/.env from template"
else
    echo "ℹ️  api/.env already exists"
fi

if [ ! -f "mcp/.env" ]; then
    cp mcp/.env.example mcp/.env
    echo "✅ Created mcp/.env from template"
else
    echo "ℹ️  mcp/.env already exists"
fi

# Start PostGIS
echo ""
echo "🐘 Starting PostGIS..."
cd docker
docker compose up -d
cd ..

# Wait for PostGIS to be ready
echo "⏳ Waiting for PostGIS to be ready..."
sleep 5

# Check PostGIS health
if docker compose -f docker/docker-compose.yml ps | grep -q "healthy"; then
    echo "✅ PostGIS is ready"
else
    echo "⚠️  PostGIS may not be fully ready yet. Check with: docker compose -f docker/docker-compose.yml ps"
fi

# Install API dependencies
echo ""
echo "📦 Installing API dependencies..."
cd api
uv sync
cd ..
echo "✅ API dependencies installed"

# Install MCP dependencies
echo ""
echo "📦 Installing MCP dependencies..."
cd mcp
uv sync
cd ..
echo "✅ MCP dependencies installed"

echo ""
echo "✨ Setup complete!"
echo ""
echo "To start the API server:"
echo "  cd api && uv run uvicorn lib.main:app --reload --port 3000"
echo ""
echo "To start the MCP server:"
echo "  cd mcp && uv run python server.py"
echo ""
echo "To stop PostGIS:"
echo "  cd docker && docker compose down"

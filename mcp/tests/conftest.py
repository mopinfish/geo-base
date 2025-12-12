"""
pytest configuration for geo-base MCP tests.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ.setdefault("TILE_SERVER_URL", "https://geo-base-puce.vercel.app")
os.environ.setdefault("ENVIRONMENT", "test")


def pytest_configure(config):
    """Configure pytest."""
    print("\n" + "=" * 60)
    print("🧪 geo-base MCP Server Tests")
    print(f"📡 Tile Server: {os.environ.get('TILE_SERVER_URL')}")
    print("=" * 60)

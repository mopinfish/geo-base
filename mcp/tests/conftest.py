"""
pytest configuration for geo-base MCP tests.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment variables
os.environ.setdefault("TILE_SERVER_URL", "https://geo-base-api.fly.dev")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "DEBUG")

# Exclude live_test.py from pytest collection (it's a standalone script)
collect_ignore = ["live_test.py"]


def pytest_configure(config):
    """Configure pytest."""
    # Register asyncio marker to avoid warnings
    config.addinivalue_line("markers", "asyncio: mark test as async")

    print("\n" + "=" * 60)
    print("🧪 geo-base MCP Server Tests")
    print(f"📡 Tile Server: {os.environ.get('TILE_SERVER_URL')}")
    print(f"📝 Log Level: {os.environ.get('LOG_LEVEL')}")
    print("=" * 60)

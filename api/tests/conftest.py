"""
Pytest configuration and fixtures for geo-base API tests.
"""

import sys
from pathlib import Path

# Add lib directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))


# ============================================================
# Fixtures
# ============================================================

# Database fixtures will be added when needed for integration tests

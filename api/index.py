"""
Vercel entry point for geo-base API.

This file is used by Vercel to serve the FastAPI application.
"""

import sys
from pathlib import Path

# Add the api directory to the Python path for Vercel
# This is needed because Vercel runs from the project root
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from lib.main import app

# Vercel requires the app to be exported as 'app'
# The handler is automatically provided by Vercel Python runtime

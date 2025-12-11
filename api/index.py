"""
Vercel Serverless Function Entry Point

This file exports the FastAPI app for Vercel deployment.
"""

import sys
from pathlib import Path

# Add the api directory to the path for imports
api_dir = Path(__file__).parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from lib.main import app

# Vercel expects the app to be named 'app' or 'handler'
# FastAPI apps work directly with Vercel's Python runtime

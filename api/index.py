"""
Vercel entry point for geo-base API.

This file is used by Vercel to serve the FastAPI application.
"""

from lib.main import app

# Vercel requires the app to be exported as 'app'
# The handler is automatically provided by Vercel Python runtime

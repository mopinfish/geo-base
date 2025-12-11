"""
Vercel Serverless Function Entry Point

This file exports the FastAPI app for Vercel deployment.
"""

from lib.main import app

# Vercel expects the app to be named 'app' or 'handler'
# FastAPI apps work directly with Vercel's Python runtime

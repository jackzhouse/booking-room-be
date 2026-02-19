"""
Vercel Serverless Entry Point
This file serves as the entry point for Vercel's serverless functions.
"""

from app.main import app

# Vercel expects a callable with event/context signature
# Using lambda to wrap the FastAPI app
handler = lambda event, context: app

"""
Vercel Serverless Entry Point
This file serves as the entry point for Vercel's serverless functions.
"""

from mangum import Mangum
from app.main import app

# Wrap the FastAPI app with Mangum for serverless compatibility
handler = Mangum(app)

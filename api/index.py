"""
Vercel Serverless Entry Point
This file serves as the entry point for Vercel's serverless functions.
"""

from app.main import app

# Vercel's Python runtime expects a callable 'handler'
handler = app

# Alternative: Use Vercel's ASGI wrapper if needed
# from vercel import ASGI
# handler = ASGI(app)

"""
Vercel Serverless Entry Point
This file serves as the entry point for Vercel's serverless functions.
"""

from app.main import app

# Vercel will import this 'handler' function
handler = app
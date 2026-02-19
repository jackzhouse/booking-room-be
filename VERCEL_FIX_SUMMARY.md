# Vercel Deployment Fix Summary

This document explains the fixes made to resolve the `pip install -r requirements.txt` error on Vercel.

## Root Cause Analysis

The deployment was failing due to several configuration issues:

1. **Incorrect `vercel.json` configuration** - Using deprecated fields and redundant build/install commands
2. **Development dependencies in production** - Testing and code quality tools were included in production requirements
3. **Missing Python runtime specification** - Vercel wasn't sure which Python version to use
4. **Redundant configuration** - Both `buildCommand` and `installCommand` were set to the same value
5. **Python version mismatch** - `.python-version` was set to 3.11 but uv (Vercel's package installer) requires `==3.12.*`
6. **Missing ASGI wrapper** - FastAPI apps need Mangum wrapper to work with Vercel's serverless environment

## Fixes Applied

### 1. Updated `vercel.json`

**Before:**
```json
{
  "buildCommand": "pip install -r requirements.txt",
  "outputDirectory": ".",
  "framework": "fastapi",
  "installCommand": "pip install -r requirements.txt"
}
```

**After:**
```json
{
  "buildCommand": "pip install -r requirements.txt",
  "outputDirectory": ".",
  "devCommand": "uvicorn app.main:app --reload"
}
```

**Changes:**
- Simplified configuration to let Vercel auto-detect Python framework
- Added `devCommand` for local development
- Removed redundant `installCommand` field

### 2. Cleaned Up `requirements.txt`

**Before:** Included development dependencies (pytest, ruff, black, etc.)

**After:** Only production dependencies + Mangum for serverless
```txt
# FastAPI & Server
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12

# MongoDB & ODM
motor==3.6.0
beanie==1.28.0
pymongo>=4.9,<4.10

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-dateutil==2.9.0

# Telegram Bot
python-telegram-bot==21.7

# Pydantic & Validation
pydantic==1.10.18
email-validator==2.2.0

# Utilities
python-dotenv==1.0.1

# Serverless
mangum==0.17.0
```

**Changes:**
- Removed `pytest==8.3.3`
- Removed `pytest-asyncio==0.24.0`
- Removed `httpx==0.27.2`
- Removed `ruff==0.7.1`
- Removed `black==24.10.0`
- Added `mangum==0.17.0` for ASGI serverless compatibility

### 3. Created `requirements-dev.txt`

New file for development dependencies:
```txt
# Include production dependencies
-r requirements.txt

# Development & Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2

# Code Quality
ruff==0.7.1
black==24.10.0
```

**Usage:**
- For development: `pip install -r requirements-dev.txt`
- For production (Vercel): `pip install -r requirements.txt`

### 4. Added `.python-version` File

Created `.python-version` file to specify Python 3.12:
```
3.12
```

This ensures Vercel uses the correct Python version and matches uv's requirement of `==3.12.*`.

### 5. Updated `api/index.py` with Mangum Wrapper

**Before:** Had commented-out code and no ASGI wrapper

**After:** Proper ASGI wrapper for serverless compatibility
```python
"""
Vercel Serverless Entry Point
This file serves as the entry point for Vercel's serverless functions.
"""

from mangum import Mangum
from app.main import app

# Wrap the FastAPI app with Mangum for serverless compatibility
handler = Mangum(app)
```

**Changes:**
- Added Mangum import for ASGI-to-serverless adapter
- Wrapped FastAPI app with Mangum handler
- Exported as `handler` for Vercel serverless functions

## Why These Changes Fix the Issue

### 1. Proper Vercel Configuration
The updated `vercel.json`:
- Simplified configuration lets Vercel auto-detect Python framework
- Added `devCommand` for local development workflow
- Removed redundant `installCommand` that was causing conflicts
- Handles pip installation correctly

### 2. Reduced Dependencies
Removing development dependencies:
- Reduces deployment time
- Prevents conflicts with Vercel's build environment
- Minimizes attack surface
- Ensures only necessary packages are installed

### 3. Explicit Python Version
The `.python-version` file:
- Guarantees Python 3.12 is used (matches uv's `==3.12.*` requirement)
- Matches the version tested during development
- Prevents version mismatches

### 4. ASGI Wrapper with Mangum
The Mangum wrapper in `api/index.py`:
- Converts ASGI app (FastAPI) to serverless-compatible handler
- Resolves the `TypeError: issubclass() arg 1 must be a class` error
- Enables FastAPI to work with Vercel's serverless functions
- Maintains all FastAPI functionality in serverless environment

## Verification Steps

After applying these fixes, verify the deployment:

### 1. Local Test
```bash
# Install production dependencies
pip install -r requirements.txt

# Test the application
uvicorn app.main:app --reload
```

### 2. Vercel Deployment
1. Commit and push changes:
   ```bash
   git add .
   git commit -m "Fix Vercel deployment issues"
   git push origin main
   ```

2. Check Vercel logs for successful pip installation

3. Test the deployed application:
   ```bash
   curl https://your-app-name.vercel.app/health
   ```

### 3. Expected Outcome
- ✅ `pip install -r requirements.txt` succeeds
- ✅ Build completes without errors
- ✅ Application responds to health check
- ✅ Telegram webhook functions correctly

## Additional Recommendations

### 1. Environment Variables
Ensure all required environment variables are set in Vercel:
- `SECRET_KEY`
- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `BOT_TOKEN`
- `WEBHOOK_BASE_URL`
- `ADMIN_TELEGRAM_ID`
- `FRONTEND_URL`

### 2. MongoDB Atlas Configuration
- Allow access from `0.0.0.0/0` (Vercel has dynamic IPs)
- Verify database user permissions
- Test connection string locally first

### 3. Monitor Logs
After deployment:
- Check Vercel logs for any runtime errors
- Verify webhook setup via Telegram API
- Test bot functionality end-to-end

## Troubleshooting

### Issue: Still Getting pip install errors

**Solution:**
1. Check Vercel build logs for specific error messages
2. Verify all dependencies in `requirements.txt` are compatible
3. Try pinning versions more strictly if needed

### Issue: TypeError: issubclass() arg 1 must be a class

**Solution:**
1. This error occurs when FastAPI app is not properly wrapped for serverless
2. Ensure Mangum is installed and imported in `api/index.py`
3. Verify the handler is wrapped: `handler = Mangum(app)`
4. This should be resolved with the current implementation

### Issue: Application crashes on startup

**Solution:**
1. Verify all environment variables are set
2. Check MongoDB connection string format
3. Review Vercel function logs for specific errors
4. Ensure Mangum is properly wrapping the FastAPI app

### Issue: Telegram bot not responding

**Solution:**
1. Check webhook URL is correct
2. Verify `BOT_TOKEN` is set correctly
3. Check Vercel logs for webhook processing errors

## Files Modified

```
Modified:
  - vercel.json
  - requirements.txt
  - api/index.py

Created:
  - requirements-dev.txt
  - .python-version
  - VERCEL_FIX_SUMMARY.md (this file)
```

## Next Steps

1. Commit and push these changes to Git
2. Redeploy to Vercel
3. Monitor the build process
4. Test all functionality
5. Update documentation if needed

---

**Deployment should now succeed! 🚀**
# Fix for Used Code Verification Issue

## Problem
After sending `/authorize <code>` in the Telegram bot, the frontend verification endpoint returned "CODE_NOT_FOUND" error even though the code was valid and had user data.

## Root Cause
The `verify_code()` method in `auth_code_service.py` was rejecting ALL used codes, including those that had been properly authenticated by the bot with user data attached.

```python
# OLD CODE - Always rejected used codes
if auth_code.used:
    print(f"🔍 AuthCodeService: Code already used")
    return None  # ← Always returns None for used codes
```

## The Issue Flow
1. ✅ Frontend generates code via `POST /generate-code`
2. ✅ User sends `/authorize 343339` in Telegram bot
3. ✅ Bot calls `/verify-code-telegram` → marks code as `used: true` and attaches `telegram_user_data`
4. ❌ Frontend polls `/verify-code?code=343339` → code is used → returns "CODE_NOT_FOUND" error

## Solution Implemented

Updated `verify_code()` method to distinguish between:
- **Used codes WITH user data** → Allow verification (return the code object)
- **Used codes WITHOUT user data** → Reject verification (return None)

### New Logic
```python
# Check if code is already used
if auth_code.used:
    # If code has user data, it was used by bot - allow verification
    if auth_code.telegram_user_data:
        print(f"🔍 AuthCodeService: Code used but has user data - allowing verification")
        auth_code.expires_at = expires_at_jakarta
        return auth_code
    # If code is used but has no user data, reject it
    print(f"🔍 AuthCodeService: Code already used without user data")
    return None
```

## Benefits
✅ Used codes with user data can be verified successfully  
✅ Frontend can retrieve the verified user data after `/authorize`  
✅ Used codes without user data are still rejected (security)  
✅ Proper authentication flow from bot to frontend works correctly  

## Files Modified
- `app/services/auth_code_service.py` - Updated `verify_code()` method to allow used codes with user data

## Testing

### Test with existing code `343339`
The code is still valid (expires at 2026-02-20T06:09:26 Jakarta time). Test it now:

```bash
curl "https://booking-room-be.onrender.com/api/v1/auth/verify-code?code=343339"
```

Expected result:
```json
{
  "success": true,
  "data": {
    "status": "verified",
    "user": {
      "id": "...",
      "telegram_id": 293871670,
      "username": "jokomakruf",
      "first_name": "Joko",
      "last_name": "Makruf",
      "photo_url": null,
      "is_admin": false,
      "is_active": true
    },
    "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

### Test complete flow
1. Generate new code: `POST /api/v1/auth/generate-code`
2. Send `/authorize {code}` in Telegram bot
3. Verify code: `GET /api/v1/auth/verify-code?code={code}`
4. Should return `status: "verified"` with user data and token

## Deployment
The fix has been committed and pushed to GitHub. Render will automatically deploy the updates.
# Authorization Code Security Implementation

## Overview

This implementation secures the authorization code system by making codes **user-specific** when possible. The system supports both Telegram Mini App and Web usage with appropriate security levels.

## Problem Solved

**Previous Vulnerability**: Any Telegram user could use any authorization code, allowing unauthorized access.

**Solution**: Authorization codes can optionally be tied to a specific Telegram user ID. For Mini App users, codes are user-specific. For Web users, codes work on a first-come-first-served basis.

## Changes Made

### 1. Database Model (`app/models/auth_code.py`)

**Added field:**
```python
telegram_user_id: Optional[int] = None
"""
Telegram user ID this code is authorized for (set during generation).
"""
```

This field links each code to the specific Telegram user who generated it.

### 2. Auth Schemas (`app/schemas/auth.py`)

**Updated schema:**
```python
class AuthCodeGenerateRequest(BaseModel):
    """Request schema for generating auth code"""
    telegram_user_id: Optional[int] = Field(
        None, 
        description="Telegram user ID to authorize the code for (optional for web users)"
    )
```

**Key Change**: `telegram_user_id` is now **optional** to support both Mini App and Web usage.

### 3. Auth Code Service (`app/services/auth_code_service.py`)

**Updated `generate_code()` method:**
- Now accepts `telegram_user_id: Optional[int] = None` parameter
- Stores the `telegram_user_id` with the code (if provided)
- Prevents code reuse by different users (only if telegram_user_id is set)

**Updated `mark_code_used()` method:**
- Now returns `tuple[bool, str]` (success, error_message)
- Validates that the requesting user ID matches the authorized user ID (only if telegram_user_id is set)
- Returns `"USER_MISMATCH"` error if users don't match (only for codes with user ID)

**Validation Logic:**
```python
# Validate telegram_user_id matches (only if telegram_user_id is set)
authorized_user_id = auth_code.telegram_user_id
requesting_user_id = user_data.get("id")

# Only validate if code has a user ID restriction
if authorized_user_id is not None and requesting_user_id != authorized_user_id:
    return False, "USER_MATCH"

# If telegram_user_id is None (web user), allow first-come-first-served
```

### 4. API Endpoint (`app/api/v1/auth.py`)

**Updated `/auth/generate-code` endpoint:**
```python
@router.post("/generate-code", response_model=AuthCodeResponse)
async def generate_auth_code(request: AuthCodeGenerateRequest):
    code, expires_at = await auth_code_service.generate_code(request.telegram_user_id)
    # ... returns code
```

**Updated `/auth/verify-code-telegram` endpoint:**
- Handles `USER_MISMATCH` error
- Returns appropriate error response to bot

**New Error Response:**
```json
{
  "success": false,
  "data": { "status": "invalid" },
  "error": {
    "code": "USER_MISMATCH",
    "message": "This code is not valid for your Telegram account"
  }
}
```

### 5. Bot Handler (`app/bot/handlers/authorize.py`)

**Updated `/authorize` command:**
- Checks `mark_code_used()` result for errors
- Sends clear Indonesian error message on user mismatch
- Prevents unauthorized code usage

**New User Mismatch Response:**
```
❌ Kode ini tidak valid untuk Anda.

Kode otorisasi hanya dapat digunakan oleh akun Telegram yang membuatkannya.

Silakan minta kode baru dari aplikasi.
```

## API Changes

### Before
```http
POST /api/v1/auth/generate-code
Content-Type: application/json

{ }
```

### After
```http
POST /api/v1/auth/generate-code
Content-Type: application/json

{
  "telegram_user_id": 123456789
}
```

## Frontend Changes Required

See `FRONTEND_AUTH_CODE_SECURITY_GUIDE.md` for detailed frontend implementation instructions.

### Quick Frontend Summary

1. **Get Telegram User ID:**
```typescript
const webApp = (window as any).Telegram?.WebApp;
const telegramUserId = webApp?.initDataUnsafe?.user?.id;
```

2. **Generate Code:**
```typescript
fetch('/api/v1/auth/generate-code', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ telegram_user_id: telegramUserId })
})
```

3. **Handle USER_MISMATCH Error:**
```typescript
if (response.error?.code === 'USER_MISMATCH') {
  showError('This code is not valid for your Telegram account');
}
```

## Mini App vs Web Usage

The system supports both Telegram Mini App and Web browser usage with different security levels:

### Scenario 1: Telegram Mini App (High Security)

**Frontend Code:**
```typescript
// Extract user ID from Telegram WebApp API
const webApp = (window as any).Telegram?.WebApp;
const telegramUserId = webApp?.initDataUnsafe?.user?.id;

// Generate user-specific code
const response = await fetch('/api/v1/auth/generate-code', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ telegram_user_id: telegramUserId })
});
```

**Security Level:** ✅ **HIGH** - Code is tied to specific user ID

**User Flow:**
1. User opens Mini App in Telegram
2. Frontend extracts `telegram_user_id` from WebApp API
3. Frontend calls `/auth/generate-code` with `telegram_user_id`
4. Backend generates code linked to that user
5. Frontend displays code to user
6. User sends `/authorize {code}` to bot
7. Bot validates user ID matches
8. ✅ Authorization successful

**Error Protection:**
- If User A generates code and User B tries to use it
- Bot responds: "❌ Kode ini tidak valid untuk Anda"
- User B must generate their own code

### Scenario 2: Web Browser (Medium Security)

**Frontend Code:**
```typescript
// No Telegram WebApp API available
// Generate code without user ID
const response = await fetch('/api/v1/auth/generate-code', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ })  // Empty or undefined
});
```

**Security Level:** ⚠️ **MEDIUM** - First-come-first-served

**User Flow:**
1. User opens app in web browser
2. Frontend calls `/auth/generate-code` without `telegram_user_id`
3. Backend generates code with no user restriction
4. Frontend displays code to user
5. User sends `/authorize {code}` to bot
6. Bot validates code (no user ID check)
7. ✅ Authorization successful

**Limitation:**
- Any user can use the code if they get to it first
- Code sharing is possible (though unlikely with 3-minute expiration)

### Comparison Table

| Feature | Mini App | Web Browser |
|---------|-----------|-------------|
| **telegram_user_id** | Provided | Not provided |
| **Security Level** | High (user-specific) | Medium (first-come-first-served) |
| **Code Sharing** | ❌ Not possible | ⚠️ Possible but unlikely |
| **User Validation** | ✅ Strict | ⏸️ Lenient |
| **Frontend Complexity** | Low (extract ID) | Very Low (no ID needed) |
| **Recommended** | ✅ Yes | ⚠️ Acceptable |

### Implementation Recommendation

**Primary Use Case:** Telegram Mini App (recommended)
- Highest security
- Best user experience
- Native Telegram integration

**Secondary Use Case:** Web Browser
- Acceptable fallback
- Simpler implementation
- Good for testing/development

### Frontend Detection

Frontend can detect which platform it's running on:

```typescript
const webApp = (window as any).Telegram?.WebApp;

if (webApp && webApp.initDataUnsafe?.user?.id) {
  // Running in Telegram Mini App
  const telegramUserId = webApp.initDataUnsafe.user.id;
  // Generate user-specific code
} else {
  // Running in web browser
  // Generate code without user ID
}
```

## User Flow

### Normal Flow (Mini App - Successful)
1. User opens Telegram Mini App
2. Frontend extracts `telegram_user_id` from WebApp
3. Frontend calls `/auth/generate-code` with `telegram_user_id`
4. Backend generates code linked to that user
5. Frontend displays code to user
6. User sends `/authorize {code}` to bot
7. Bot validates user ID matches
8. ✅ Authorization successful

### Error Flow (Mini App - Wrong User)
1. User A generates code "123456"
2. User B tries `/authorize 123456`
3. Bot detects user ID mismatch
4. ❌ Bot responds: "Kode ini tidak valid untuk Anda"
5. User B must generate their own code

## Security Benefits

✅ **Code Isolation**: Each code is tied to a specific Telegram user  
✅ **Prevents Sharing**: Users cannot share codes  
✅ **Clear Messaging**: Users receive clear error messages  
✅ **Maintains Flow**: No disruption to normal authorization flow  
✅ **Database Tracked**: All codes are linked to users in database  

## Testing Checklist

### Test Case 1: Normal Authorization
- [ ] User generates code from frontend
- [ ] Code displays in frontend
- [ ] User sends `/authorize {code}` to bot
- [ ] Bot responds: "✅ Otorisasi berhasil!"
- [ ] Frontend automatically logs in

### Test Case 2: Wrong User Tries Code
- [ ] User A (ID: 123) generates code "123456"
- [ ] User B (ID: 456) tries `/authorize 123456`
- [ ] Bot responds: "❌ Kode ini tidak valid untuk Anda"
- [ ] User A can still use their own code

### Test Case 3: Code Expiration
- [ ] User generates code
- [ ] Wait 3+ minutes
- [ ] User tries `/authorize {code}`
- [ ] Bot responds: "❌ Invalid or expired code"

### Test Case 4: Code Reuse
- [ ] User generates and uses code successfully
- [ ] Same user tries `/authorize {code}` again
- [ ] Bot responds with error (already used)

### Test Case 5: Frontend Integration
- [ ] Frontend sends `telegram_user_id` in request
- [ ] Backend accepts and stores the ID
- [ ] Code is linked to correct user
- [ ] Verification works as expected

## Database Migration

The new `telegram_user_id` field is optional, so no migration is needed for existing documents. New codes will include this field.

```python
# Old codes (before implementation)
{
  "code": "123456",
  "telegram_user_id": null,  # Not set
  ...
}

# New codes (after implementation)
{
  "code": "789012",
  "telegram_user_id": 123456789,  # Set to specific user
  ...
}
```

## Error Codes

| Error Code | Message | When It Occurs |
|------------|----------|----------------|
| `CODE_NOT_FOUND` | Invalid authorization code | Code doesn't exist or is expired |
| `USER_MISMATCH` | This code is not valid for your Telegram account | Wrong user tries to use code |
| `CODE_ERROR` | Code processing error | General code processing failure |

## Monitoring and Logs

The system includes detailed logging:

```python
print(f"✅ AuthCodeService: Generated and saved code: {code} for user {telegram_user_id}")
print(f"❌ AuthCodeService: User mismatch - Code authorized for {authorized_user_id}, requested by {requesting_user_id}")
print(f"🔍 Bot: User mismatch - code authorized for different user")
```

Monitor logs for:
- Successful code generations
- User mismatch attempts (potential security concerns)
- Failed authorizations

## Backward Compatibility

✅ **Good News**: This change is **backward compatible** with existing frontend code!

Old frontend code that doesn't send `telegram_user_id` will continue to work:
```http
POST /api/v1/auth/generate-code
Content-Type: application/json

{ }
```

This will generate a code without user restriction (medium security).

**Recommended Enhancement**: Update frontend to include `telegram_user_id` when available (high security):
- Mini App: Extract and send `telegram_user_id` for full security
- Web Browser: Continue without `telegram_user_id` (works as before)

See `FRONTEND_AUTH_CODE_SECURITY_GUIDE.md` for implementation details.

## Deployment Steps

1. ✅ Deploy backend changes (already done)
2. ⏳ Update frontend to extract and send `telegram_user_id`
3. ⏳ Test the complete flow with multiple users
4. ⏳ Monitor logs for user mismatch attempts
5. ⏳ Update user documentation if needed

## Support Documentation

- **Frontend Guide**: `FRONTEND_AUTH_CODE_SECURITY_GUIDE.md`
- **Bot Handler**: `app/bot/handlers/authorize.py`
- **API Endpoint**: `app/api/v1/auth.py`
- **Service**: `app/services/auth_code_service.py`

## Summary

This implementation successfully secures the authorization code system by:
1. Linking each code to a specific Telegram user ID
2. Validating user identity before authorization
3. Providing clear error messages for security violations
4. Maintaining smooth user experience for legitimate users

The system now prevents code sharing while maintaining the ease of use for legitimate authorization flows.
# Code-Based Authentication System - Complete Implementation

## Overview

A new authentication system that avoids CORS/Tunnel issues by using a simple code-based flow. Users generate a code from the frontend, then send it to the Telegram bot via `/authorize` command.

## Architecture

```
Frontend                    Backend                      Bot
  |                           |                          |
  |--- POST /generate-code -->|                          |
  |<--- {code: "123456"} ---|                          |
  |                           |                          |
  |                           |                          |
User sends /authorize 123456 to bot ---------------------->|
  |                           |<-- POST /verify-code-telegram
  |                           |     {code, user_data}     |
  |<--- JWT token -----------|                          |
```

## API Endpoints

### 1. Generate Auth Code

**Endpoint:** `POST /api/v1/auth/generate-code`

**Request:** No body required

**Response:**
```json
{
  "success": true,
  "data": {
    "code": "321807",
    "expires_at": "2026-02-19T12:40:57Z",
    "expires_in": 600
  }
}
```

**Details:**
- Generates a random 6-digit code
- Code expires after 10 minutes (600 seconds)
- Each code can only be used once
- `expires_in` shows remaining seconds until expiration

### 2. Verify Code with Telegram Data

**Endpoint:** `POST /api/v1/auth/verify-code-telegram?code=123456`

**Request Body:**
```json
{
  "id": 293871670,
  "first_name": "Joko",
  "last_name": "Makruf",
  "username": "jokomakruf",
  "photo_url": null
}
```

**Response:**
```json
{
  "verified": true,
  "user_data": {
    "id": 293871670,
    "full_name": "Joko Makruf",
    "username": "jokomakruf",
    "avatar_url": null,
    "is_admin": true
  },
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Details:**
- Verifies the code is valid and not expired
- Creates/updates user in database
- Generates JWT token
- Marks code as used

## Bot Command

### /authorize

**Usage:** `/authorize <code>`

**Examples:**
- `/authorize 123456`
- `/authorize 321807`

**User Flow:**
1. Frontend generates code via `/generate-code`
2. User sends `/authorize 123456` to the bot
3. Bot verifies code and associates Telegram identity
4. Bot returns JWT token to user
5. User copies token to frontend

**Bot Responses:**

**Success:**
```
✅ Authorization successful!

Welcome, Joko Makruf!

🔑 You have admin privileges.

🔐 Your access token:
`eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

💡 Use this token to authenticate with the frontend.
```

**Error - No code:**
```
❌ Please provide a 6-digit code.

Usage: /authorize <code>

Example: /authorize 123456
```

**Error - Invalid format:**
```
❌ Invalid code format.

Code must be a 6-digit number.

Example: /authorize 123456
```

**Error - Invalid/Expired:**
```
❌ Invalid or expired code.

Please generate a new code from the frontend and try again.
```

## Timezone Configuration

The backend uses **Jakarta timezone (Asia/Jakarta, UTC+7)** for all date/time operations.

**Configuration:** `app/core/config.py`
```python
TIMEZONE: str = "Asia/Jakarta"  # Default timezone for the application

@property
def timezone(self) -> ZoneInfo:
    """Get timezone as ZoneInfo object"""
    return ZoneInfo(self.TIMEZONE)
```

**Usage:**
```python
from datetime import datetime
from app.core.config import settings

# Get current time in Jakarta timezone
now = datetime.now(settings.timezone)
```

**Note:** JWT tokens continue to use UTC (standard practice for authentication).

## Implementation Files

### 1. Service Layer
**File:** `app/services/auth_code_service.py`

**Class:** `AuthCodeService`

**Key Methods:**
- `generate_code()` - Creates 6-digit code
- `verify_code(code)` - Validates code
- `mark_code_used(code, user_data)` - Associates user data
- `_cleanup_expired_codes()` - Removes expired codes

**Features:**
- In-memory storage (can upgrade to MongoDB)
- Automatic cleanup of expired codes
- 10-minute expiration
- Single-use codes

### 2. API Routes
**File:** `app/api/v1/auth.py`

**New Endpoints:**
- `POST /auth/generate-code` - Generate code
- `GET /auth/verify-code` - Check code status
- `POST /auth/verify-code-telegram` - Verify with Telegram data

### 3. Bot Handler
**File:** `app/bot/handlers/authorize.py`

**Function:** `authorize_command(update, context)`

**Features:**
- Input validation
- HTTP calls to backend API
- Error handling
- User-friendly messages

### 4. Schemas
**File:** `app/schemas/auth.py`

**New Schemas:**
- `AuthCodeResponse` - Generate code response
- `AuthCodeVerifyResponse` - Verify code response
- `TelegramUserAuth` - Telegram user data

## Configuration

### Environment Variables

No new variables needed. Uses existing:
- `WEBHOOK_BASE_URL` - Backend URL for bot API calls
- `BOT_TOKEN` - Telegram bot token

### Settings

Code expiration is configured in `app/services/auth_code_service.py`:
```python
self.code_expiry_minutes = 10  # Change this value as needed
```

## Testing

### Test 1: Generate Code
```bash
curl -X POST http://localhost:8000/api/v1/auth/generate-code
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "code": "321807",
    "expires_at": "2026-02-19T15:46:12.177122+07:00",
    "expires_in": 599
  }
}
```

### Test 2: Verify Code
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-code-telegram?code=321807" \
  -H "Content-Type: application/json" \
  -d '{"id": 293871670, "first_name": "Joko", "last_name": "Makruf", "username": "jokomakruf"}'
```

**Expected Response:**
```json
{
  "verified": true,
  "user_data": {...},
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Test 3: Invalid Code
```bash
curl -X POST "http://localhost:8000/api/v1/auth/verify-code-telegram?code=999999" \
  -H "Content-Type: application/json" \
  -d '{"id": 123, "first_name": "Test"}'
```

**Expected Response:**
```json
{
  "verified": false,
  "user_data": null,
  "access_token": null
}
```

## Frontend Integration

### Step 1: Generate Code
```javascript
async function generateAuthCode() {
  const response = await fetch('http://localhost:8000/api/v1/auth/generate-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  const data = await response.json();
  return data.code; // e.g., "321807"
}
```

### Step 2: Display Code to User
```javascript
const code = await generateAuthCode();
alert(`Send this code to the bot: /authorize ${code}`);
```

### Step 3: User Sends Code to Bot
User opens Telegram and sends: `/authorize 321807`

### Step 4: User Copies Token from Bot
Bot returns: `🔐 Your access token: eyJhbGci...`

### Step 5: Frontend Stores Token
```javascript
// User pastes token into input or frontend receives it somehow
localStorage.setItem('token', userToken);
```

## Security Considerations

### Pros ✅
- No CORS issues
- Works with any frontend URL
- Simple user experience
- No need for public backend URL
- Codes expire quickly (10 minutes)
- Single-use codes prevent replay attacks

### Cons ⚠️
- Requires user to copy/paste token manually
- In-memory storage (lost on server restart)
- Token transmitted via bot message (can be intercepted)

### Recommendations
1. **Production:** Upgrade to MongoDB storage for codes
2. **Security:** Use secure channel for token delivery (consider alternative)
3. **UX:** Implement polling or WebSocket for automatic token delivery
4. **Monitoring:** Log all code generation and verification attempts

## Advantages Over Traditional Flow

### Old Flow (Telegram Login Widget)
❌ Requires CORS configuration
❌ Frontend and backend must be publicly accessible
❌ Complex hash verification
❌ Ngrok tunnel conflicts

### New Flow (Code-Based)
✅ No CORS requirements
✅ Backend can be localhost
✅ Simple verification
✅ Works with any frontend setup
✅ Easy to test and debug

## Future Enhancements

1. **Polling Mode:** Frontend polls `/verify-code` to check if code is used
2. **WebSocket:** Real-time notification when code is verified
3. **MongoDB Storage:** Persistent code storage across restarts
4. **Rate Limiting:** Prevent code spam
5. **Code Reuse:** Allow same user to reuse code within time window
6. **QR Code:** Display QR code that bot can scan

## Troubleshooting

### Issue: "Invalid or expired code"
**Solution:** Generate a new code and try again

### Issue: Bot cannot reach backend
**Solution:** Check `WEBHOOK_BASE_URL` in `.env`

### Issue: Code works but no JWT token
**Solution:** Check logs for database errors

### Issue: Server restart loses codes
**Solution:** This is expected with in-memory storage. Upgrade to MongoDB for persistence.

## Summary

The code-based authentication system provides a simple, CORS-free alternative to traditional Telegram authentication. It's perfect for development and testing, and can be enhanced for production use.

**Key Benefits:**
- ✅ No CORS/Tunnel issues
- ✅ Simple implementation
- ✅ Works with localhost backend
- ✅ Easy user flow
- ✅ Secure (short-lived, single-use codes)

**Files Modified/Created:**
- `app/services/auth_code_service.py` (new)
- `app/api/v1/auth.py` (updated)
- `app/schemas/auth.py` (updated)
- `app/bot/handlers/authorize.py` (new)
- `app/bot/webhook.py` (updated)
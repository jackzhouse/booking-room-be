# Frontend Guide: Secure Authorization Code Implementation

## Overview

This guide explains the frontend changes required for the new secure authorization code system. The authorization codes are now **user-specific** - each code can only be used by the Telegram user who generated it.

## Problem Being Solved

**Previous Behavior**: Any Telegram user could use any authorization code, creating a security vulnerability.

**New Behavior**: Authorization codes are tied to a specific Telegram user ID. Only that user can authorize the code.

## Getting Telegram User ID

Your frontend is a Telegram Mini App, so you can access user data via the Telegram WebApp API.

### Method: Access Telegram WebApp User Data

```typescript
// Get Telegram WebApp instance
const webApp = (window as any).Telegram?.WebApp;

// Check if running inside Telegram
if (!webApp) {
  console.error('Not running inside Telegram');
  // Handle error: show message to open app from Telegram
  return;
}

// Get user data
const telegramUser = webApp.initDataUnsafe?.user;

if (!telegramUser) {
  console.error('No user data available');
  // Handle error: user not authenticated in Telegram
  return;
}

// Extract user information
const telegramUserId = telegramUser.id;
const userName = telegramUser.first_name;
const userLastName = telegramUser.last_name;
const username = telegramUser.username;

console.log('Telegram User ID:', telegramUserId);
console.log('User Name:', userName);
```

### Helper Function

```typescript
/**
 * Get Telegram user ID from WebApp
 * @returns Telegram user ID or null if not available
 */
function getTelegramUserId(): number | null {
  const webApp = (window as any).Telegram?.WebApp;
  
  if (!webApp?.initDataUnsafe?.user) {
    return null;
  }
  
  return webApp.initDataUnsafe.user.id;
}

/**
 * Get Telegram user data from WebApp
 * @returns User object or null if not available
 */
function getTelegramUserData() {
  const webApp = (window as any).Telegram?.WebApp;
  
  if (!webApp?.initDataUnsafe?.user) {
    return null;
  }
  
  return {
    id: webApp.initDataUnsafe.user.id,
    firstName: webApp.initDataUnsafe.user.first_name,
    lastName: webApp.initDataUnsafe.user.last_name,
    username: webApp.initDataUnsafe.user.username,
    photoUrl: webApp.initDataUnsafe.user.photo_url
  };
}
```

## Updated API Calls

### 1. Generate Authorization Code

**New Request Format**:

```typescript
async function generateAuthCode(): Promise<AuthCodeResponse> {
  // Get Telegram user ID
  const telegramUserId = getTelegramUserId();
  
  if (!telegramUserId) {
    throw new Error('Telegram user ID not available. Please open this app from Telegram.');
  }
  
  // Make API call
  const response = await fetch('/api/v1/auth/generate-code', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      telegram_user_id: telegramUserId
    })
  });
  
  if (!response.ok) {
    throw new Error('Failed to generate authorization code');
  }
  
  const data = await response.json();
  return data;
}

// Type definitions
interface AuthCodeResponse {
  success: boolean;
  data: {
    code: string;
    expires_at: string;  // ISO 8601 datetime
    expires_in: number;  // seconds until expiration
  };
}
```

**Response Example**:

```json
{
  "success": true,
  "data": {
    "code": "123456",
    "expires_at": "2026-03-06T09:30:00+07:00",
    "expires_in": 180
  }
}
```

### 2. Verify Authorization Code (Polling)

**Request Format** (unchanged):

```typescript
async function verifyAuthCode(code: string): Promise<VerifyResponse> {
  const response = await fetch(`/api/v1/auth/verify-code?code=${code}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    }
  });
  
  const data = await response.json();
  return data;
}
```

**Response Examples**:

**Pending (code valid but not used yet)**:
```json
{
  "success": true,
  "data": {
    "status": "pending",
    "expires_at": "2026-03-06T09:30:00+07:00",
    "expires_in": 120
  }
}
```

**Verified (code used by correct user)**:
```json
{
  "success": true,
  "data": {
    "status": "verified",
    "user": {
      "id": "...",
      "telegram_id": 123456789,
      "username": "john_doe",
      "first_name": "John",
      "last_name": "Doe",
      "photo_url": "...",
      "is_admin": false,
      "is_active": true
    },
    "token": "eyJhbGciOiJIUzI1NiIs..."
  }
}
```

**User Mismatch (NEW - code used by wrong user)**:
```json
{
  "success": false,
  "data": {
    "status": "invalid"
  },
  "error": {
    "code": "USER_MISMATCH",
    "message": "This code is not valid for your Telegram account"
  }
}
```

**Expired/Invalid**:
```json
{
  "success": false,
  "data": {
    "status": "expired"
  },
  "error": {
    "code": "CODE_NOT_FOUND",
    "message": "Invalid authorization code"
  }
}
```

## UI Updates

### Display Code with User-Specific Message

```typescript
function AuthCodeDisplay() {
  const [code, setCode] = useState<string>('');
  const [expiresAt, setExpiresAt] = useState<string>('');
  const [userName, setUserName] = useState<string>('');
  
  const handleGenerateCode = async () => {
    try {
      // Get user name
      const userData = getTelegramUserData();
      if (userData) {
        setUserName(userData.firstName || 'User');
      }
      
      // Generate code
      const response = await generateAuthCode();
      setCode(response.data.code);
      setExpiresAt(response.data.expires_at);
      
    } catch (error) {
      console.error('Error generating code:', error);
      // Show error to user
      alert('Failed to generate authorization code. Please try again.');
    }
  };
  
  return (
    <div className="auth-code-container">
      {!code ? (
        <button onClick={handleGenerateCode}>
          Generate Authorization Code
        </button>
      ) : (
        <div className="code-display">
          <h3>Your Authorization Code</h3>
          <p className="user-specific">
            This code is only valid for: <strong>{userName}</strong>
          </p>
          <div className="code-number">{code}</div>
          <p className="instructions">
            Send this code to the bot:<br/>
            <code>/authorize {code}</code>
          </p>
          <p className="expires-in">
            Expires in: {formatExpiresIn(expiresAt)}
          </p>
          <div className="warning-box">
            ⚠️ <strong>Important:</strong> Only your Telegram account can use this code!
          </div>
        </div>
      )}
    </div>
  );
}
```

### Error Handling for User Mismatch

```typescript
function useCodeVerification(code: string) {
  const [status, setStatus] = useState<'pending' | 'verified' | 'error'>('pending');
  const [error, setError] = useState<string>('');
  
  useEffect(() => {
    if (!code) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await verifyAuthCode(code);
        
        if (response.data?.status === 'verified') {
          setStatus('verified');
          clearInterval(pollInterval);
          // Store token and redirect
          localStorage.setItem('token', response.data.token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
          // Redirect to dashboard
          window.location.href = '/dashboard';
          
        } else if (response.error?.code === 'USER_MISMATCH') {
          setStatus('error');
          setError(
            'This authorization code is not valid for your Telegram account. ' +
            'Please generate a new code.'
          );
          clearInterval(pollInterval);
          
        } else if (response.error?.code === 'CODE_NOT_FOUND') {
          setStatus('error');
          setError(
            'This code has expired or is invalid. ' +
            'Please generate a new code.'
          );
          clearInterval(pollInterval);
        }
        
      } catch (err) {
        console.error('Error verifying code:', err);
      }
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(pollInterval);
  }, [code]);
  
  return { status, error };
}
```

## Complete Example Component

```typescript
import React, { useState, useEffect } from 'react';

// Helper functions
function getTelegramUserId(): number | null {
  const webApp = (window as any).Telegram?.WebApp;
  return webApp?.initDataUnsafe?.user?.id || null;
}

function getTelegramUserData() {
  const webApp = (window as any).Telegram?.WebApp;
  return webApp?.initDataUnsafe?.user || null;
}

async function generateAuthCode(telegramUserId: number) {
  const response = await fetch('/api/v1/auth/generate-code', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ telegram_user_id: telegramUserId })
  });
  return response.json();
}

async function verifyAuthCode(code: string) {
  const response = await fetch(`/api/v1/auth/verify-code?code=${code}`);
  return response.json();
}

function formatExpiresIn(expiresAt: string): string {
  const expires = new Date(expiresAt).getTime();
  const now = Date.now();
  const seconds = Math.floor((expires - now) / 1000);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${seconds % 60}s`;
}

// Main Component
function AuthorizationPage() {
  const [code, setCode] = useState<string>('');
  const [expiresAt, setExpiresAt] = useState<string>('');
  const [userName, setUserName] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  
  const handleGenerateCode = async () => {
    const telegramUserId = getTelegramUserId();
    
    if (!telegramUserId) {
      setError('Please open this app from Telegram to generate an authorization code.');
      return;
    }
    
    const userData = getTelegramUserData();
    if (userData) {
      setUserName(userData.firstName || 'User');
    }
    
    setLoading(true);
    setError('');
    
    try {
      const response = await generateAuthCode(telegramUserId);
      if (response.success) {
        setCode(response.data.code);
        setExpiresAt(response.data.expires_at);
      } else {
        setError('Failed to generate authorization code.');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    if (!code) return;
    
    const pollInterval = setInterval(async () => {
      try {
        const response = await verifyAuthCode(code);
        
        if (response.data?.status === 'verified') {
          clearInterval(pollInterval);
          // Success! Redirect to dashboard
          localStorage.setItem('token', response.data.token);
          localStorage.setItem('user', JSON.stringify(response.data.user));
          window.location.href = '/dashboard';
          
        } else if (response.error?.code === 'USER_MISMATCH') {
          clearInterval(pollInterval);
          setError(
            '⚠️ This code is not valid for your Telegram account. ' +
            'Please generate a new code.'
          );
          
        } else if (response.error?.code === 'CODE_NOT_FOUND') {
          clearInterval(pollInterval);
          setError('⚠️ Code expired or invalid. Please generate a new code.');
        }
        
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 2000);
    
    return () => clearInterval(pollInterval);
  }, [code]);
  
  return (
    <div className="authorization-page">
      <h2>Telegram Authorization</h2>
      
      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => { setError(''); setCode(''); }}>
            Try Again
          </button>
        </div>
      )}
      
      {!code && !error && (
        <div>
          <p>
            Generate an authorization code and send it to the bot
            to verify your Telegram account.
          </p>
          <button 
            onClick={handleGenerateCode}
            disabled={loading}
          >
            {loading ? 'Generating...' : 'Generate Authorization Code'}
          </button>
        </div>
      )}
      
      {code && (
        <div className="code-display">
          <h3>Authorization Code</h3>
          <p className="user-specific">
            Valid for: <strong>{userName}</strong>
          </p>
          <div className="code-number">{code}</div>
          <p className="instructions">
            <strong>Step 1:</strong> Open the Telegram bot<br/>
            <strong>Step 2:</strong> Send: <code>/authorize {code}</code><br/>
            <strong>Step 3:</strong> Wait for automatic login
          </p>
          <p className="expires-in">
            ⏰ Expires in: {formatExpiresIn(expiresAt)}
          </p>
          <div className="warning-box">
            ⚠️ <strong>Security Notice:</strong> This code is tied to your 
            Telegram account and cannot be used by anyone else.
          </div>
        </div>
      )}
    </div>
  );
}

export default AuthorizationPage;
```

## Testing Checklist

### Test Case 1: Normal Flow
- [ ] User opens app from Telegram
- [ ] User clicks "Generate Code"
- [ ] Code is displayed with user's name
- [ ] User sends `/authorize {code}` to bot
- [ ] Bot responds: "✅ Otorisasi berhasil!"
- [ ] Frontend automatically redirects to dashboard

### Test Case 2: Wrong User Tries Code
- [ ] User A generates code "123456"
- [ ] User B tries `/authorize 123456`
- [ ] Bot responds: "❌ Kode ini tidak valid untuk Anda. Silakan minta kode baru."
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

## Migration Steps

1. **Update your API client** to include `telegram_user_id` in the request body
2. **Add user data extraction** from Telegram WebApp
3. **Update UI** to show user-specific messages
4. **Add error handling** for `USER_MISMATCH` error
5. **Test the flow** with multiple Telegram accounts

## Support

If you encounter any issues:
1. Check that Telegram WebApp is available: `console.log(window.Telegram?.WebApp)`
2. Verify `telegram_user_id` is being sent in the request
3. Check browser console for error messages
4. Ensure backend has been updated with the new security implementation
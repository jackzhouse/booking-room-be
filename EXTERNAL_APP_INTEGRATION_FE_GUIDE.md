# External App Integration Guide - Frontend

## Overview

This guide explains how to integrate the Booking Room system with external applications (specifically Katalis App). Users from the external app can access the booking room system using a JWT token provided by their app.

## Integration Flow

### High-Level Flow

```
External App (Katalis)
       ↓
    User clicks link with JWT token
       ↓
Booking Room Frontend
       ↓
Verify token with BE
       ↓
    ┌───────┴───────┐
    ↓               ↓
User exists?   User doesn't exist?
    ↓               ↓
Redirect to    Show registration form
  dashboard           ↓
    ↓           Submit registration
    ↓               ↓
   Access       Redirect to dashboard
   booking           ↓
                      Access booking
```

### Detailed Flow

#### Step 1: User Access from External App

User from external app clicks a link like:
```
https://booking-room.tkilocal.biz.id/auth/token/{jwt_token}
```

The JWT token contains:
```json
{
  "producer": "katalis",
  "userId": "695dcff40cdc7726a29f5006",
  "accountId": "695dcff40cdc7726a29f5005",
  "companyId": "0000000074739c67c2a1d6fe",
  "roles": ["ROLE_USER"],
  "permission": "",
  "exp": 1772156888,
  "iat": 1771984088
}
```

#### Step 2: Frontend Extracts Token

Extract the JWT token from the URL:
```typescript
// Example: /auth/token/eyJhbGciOiJIUzI1NiJ9.eyJwcm9kdWNlciI6Im...
const pathParts = window.location.pathname.split('/');
const jwtToken = pathParts[pathParts.length - 1];
```

#### Step 3: Verify Token

Call the verify token endpoint to check user status:

```typescript
const verifyResponse = await fetch('https://booking-room.tkilocal.biz.id/api/v1/auth/external/verify-token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ token: jwtToken })
});

const verifyData = await verifyResponse.json();
```

**Response if user doesn't exist:**
```json
{
  "success": true,
  "registered": false,
  "user_id": "695dcff40cdc7726a29f5006",
  "company_id": "0000000074739c67c2a1d6fe"
}
```

**Response if user exists:**
```json
{
  "success": true,
  "registered": true,
  "user": {
    "id": "6507f9b8e1...",
    "telegram_id": null,
    "full_name": "John Doe",
    "username": null,
    "avatar_url": null,
    "division": "IT Division",
    "email": "john.doe@example.com",
    "telegram_username": "@johndoe",
    "is_admin": false,
    "is_active": true,
    "created_at": "2026-03-04T10:00:00Z",
    "last_login_at": "2026-03-04T10:00:00Z"
  }
}
```

#### Step 4a: Handle New User (Registration)

If `registered: false`, show registration form:

**Registration Form Fields:**
- Full Name (required)
- Division (required)
- Email (required)
- Telegram Username (optional)

**Submit Registration:**
```typescript
const registerResponse = await fetch('https://booking-room.tkilocal.biz.id/api/v1/auth/external/register', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    token: jwtToken,
    full_name: formData.name,
    division: formData.division,
    email: formData.email,
    telegram_username: formData.telegramUsername
  })
});

const registerData = await registerResponse.json();
```

**Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "6507f9b8e1...",
    "telegram_id": null,
    "full_name": "John Doe",
    "username": null,
    "avatar_url": null,
    "division": "IT Division",
    "email": "john.doe@example.com",
    "telegram_username": "@johndoe",
    "is_admin": false,
    "is_active": true,
    "created_at": "2026-03-04T10:00:00Z",
    "last_login_at": "2026-03-04T10:00:00Z"
  }
}
```

After successful registration:
```typescript
// Save user data to state/context
setUser(registerData.user);

// Save token to localStorage (for subsequent requests)
localStorage.setItem('external_token', jwtToken);

// Redirect to dashboard
navigate('/app/mobile/');
```

#### Step 4b: Handle Existing User

If `registered: true`, user can proceed directly:

```typescript
// Save user data to state/context
setUser(verifyData.user);

// Save token to localStorage (for subsequent requests)
localStorage.setItem('external_token', jwtToken);

// Redirect to dashboard
navigate('/app/mobile/');
```

#### Step 5: Access Booking Endpoints

For all subsequent requests, include the external token in Authorization header:

```typescript
const response = await fetch('https://booking-room.tkilocal.biz.id/api/v1/bookings', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${jwtToken}`
  }
});

// Or using stored token
const storedToken = localStorage.getItem('external_token');
const response = await fetch('https://booking-room.tkilocal.biz.id/api/v1/bookings', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${storedToken}`
  }
});
```

## API Endpoints

### 1. Verify Token

Check if external token is valid and user registration status.

**Endpoint:** `POST /api/v1/auth/external/verify-token`

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9..."
}
```

**Success Response (User Not Registered):**
```json
{
  "success": true,
  "registered": false,
  "user_id": "695dcff40cdc7726a29f5006",
  "company_id": "0000000074739c67c2a1d6fe"
}
```

**Success Response (User Registered):**
```json
{
  "success": true,
  "registered": true,
  "user": {
    "id": "6507f9b8e1...",
    "telegram_id": null,
    "full_name": "John Doe",
    "division": "IT Division",
    "email": "john.doe@example.com",
    "telegram_username": "@johndoe",
    "is_admin": false,
    "is_active": true,
    "created_at": "2026-03-04T10:00:00Z",
    "last_login_at": "2026-03-04T10:00:00Z"
  }
}
```

**Error Response (Invalid Token):**
```json
{
  "detail": "Invalid token"
}
```

### 2. Register User

Register a new user from external app.

**Endpoint:** `POST /api/v1/auth/external/register`

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "full_name": "John Doe",
  "division": "IT Division",
  "email": "john.doe@example.com",
  "telegram_username": "@johndoe"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "6507f9b8e1...",
    "telegram_id": null,
    "full_name": "John Doe",
    "division": "IT Division",
    "email": "john.doe@example.com",
    "telegram_username": "@johndoe",
    "is_admin": false,
    "is_active": true,
    "created_at": "2026-03-04T10:00:00Z",
    "last_login_at": "2026-03-04T10:00:00Z"
  }
}
```

**Error Response (Invalid Token):**
```json
{
  "detail": "Invalid token"
}
```

**Error Response (User Already Exists):**
```json
{
  "detail": "User already registered"
}
```

## Complete Code Example

### React Component Example

```typescript
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface FormData {
  name: string;
  division: string;
  email: string;
  telegramUsername: string;
}

const ExternalAuthPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showRegistration, setShowRegistration] = useState(false);
  const [formData, setFormData] = useState<FormData>({
    name: '',
    division: '',
    email: '',
    telegramUsername: ''
  });

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      // Extract token from URL
      const pathParts = window.location.pathname.split('/');
      const jwtToken = pathParts[pathParts.length - 1];

      if (!jwtToken || jwtToken === 'token') {
        setError('Invalid token');
        setLoading(false);
        return;
      }

      // Verify token
      const verifyResponse = await fetch('/api/v1/auth/external/verify-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: jwtToken })
      });

      const verifyData = await verifyResponse.json();

      if (verifyData.success) {
        if (verifyData.registered) {
          // User already exists, save data and redirect
          localStorage.setItem('external_token', jwtToken);
          // Assuming you have a context/state management
          setUser(verifyData.user);
          navigate('/app/mobile/');
        } else {
          // User doesn't exist, show registration form
          setShowRegistration(true);
          setLoading(false);
        }
      } else {
        setError('Failed to verify token');
        setLoading(false);
      }
    } catch (err) {
      setError('An error occurred');
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const pathParts = window.location.pathname.split('/');
      const jwtToken = pathParts[pathParts.length - 1];

      const registerResponse = await fetch('/api/v1/auth/external/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token: jwtToken,
          full_name: formData.name,
          division: formData.division,
          email: formData.email,
          telegram_username: formData.telegramUsername
        })
      });

      const registerData = await registerResponse.json();

      if (registerData.success) {
        localStorage.setItem('external_token', jwtToken);
        setUser(registerData.user);
        navigate('/app/mobile/');
      } else {
        setError(registerData.detail || 'Registration failed');
        setLoading(false);
      }
    } catch (err) {
      setError('An error occurred during registration');
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!showRegistration) {
    return <div>Redirecting...</div>;
  }

  return (
    <div>
      <h1>Complete Your Registration</h1>
      <form onSubmit={handleRegister}>
        <div>
          <label>Full Name *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            required
          />
        </div>
        <div>
          <label>Division *</label>
          <input
            type="text"
            value={formData.division}
            onChange={(e) => setFormData({ ...formData, division: e.target.value })}
            required
          />
        </div>
        <div>
          <label>Email *</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            required
          />
        </div>
        <div>
          <label>Telegram Username (Optional)</label>
          <input
            type="text"
            value={formData.telegramUsername}
            onChange={(e) => setFormData({ ...formData, telegramUsername: e.target.value })}
            placeholder="@username"
          />
        </div>
        <button type="submit" disabled={loading}>
          Complete Registration
        </button>
      </form>
    </div>
  );
};

export default ExternalAuthPage;
```

### API Service Example

```typescript
// api/externalAuth.ts

export const verifyExternalToken = async (token: string) => {
  const response = await fetch('/api/v1/auth/external/verify-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token })
  });
  return response.json();
};

export const registerExternalUser = async (token: string, userData: {
  full_name: string;
  division: string;
  email: string;
  telegram_username?: string;
}) => {
  const response = await fetch('/api/v1/auth/external/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token, ...userData })
  });
  return response.json();
};

// Generic API call with external token
export const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const token = localStorage.getItem('external_token');
  
  const response = await fetch(endpoint, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  return response.json();
};

// Usage examples
export const getBookings = () => apiCall('/api/v1/bookings');
export const getRooms = () => apiCall('/api/v1/rooms');
export const createBooking = (data: any) => apiCall('/api/v1/bookings', {
  method: 'POST',
  body: JSON.stringify(data)
});
```

## Error Handling

### Common Errors

1. **Invalid Token (401)**
   - Token is malformed or expired
   - SECRET_KEY mismatch (ensure Katalis uses the same SECRET_KEY as Booking Room BE)
   - Invalid producer (not "katalis")

2. **User Already Exists (400)**
   - Trying to register a user that's already registered
   - Should call verify-token first

3. **Network Errors**
   - Backend is down
   - CORS issues
   - Network connectivity problems

### Error Handling Example

```typescript
const handleAuth = async () => {
  try {
    const response = await verifyExternalToken(token);
    
    if (response.success) {
      // Success handling
    } else {
      // Backend returned error
      if (response.detail) {
        alert(`Error: ${response.detail}`);
      } else {
        alert('An unknown error occurred');
      }
    }
  } catch (error) {
    // Network or parsing error
    console.error('Auth error:', error);
    alert('Failed to connect to server. Please try again.');
  }
};
```

## Security Considerations

1. **Token Storage**: Store token in localStorage (recommended) or sessionStorage
2. **Token Validation**: Backend validates token using **SECRET_KEY** (same secret key used for both Telegram users and external users)
3. **Token Expiration**: Backend will reject expired tokens
4. **HTTPS**: Always use HTTPS in production
5. **Logout**: Clear token on logout
   ```typescript
   const logout = () => {
     localStorage.removeItem('external_token');
     setUser(null);
     navigate('/login');
   };
   ```

## User Types

The system supports two types of users:

1. **Telegram Users**: Created via Telegram auth (have `telegram_id`)
2. **External Users**: Created via external app (have `external_user_id`)

Both can access the same booking endpoints, but:
- External users have `telegram_id: null`
- External users have `external_user_id`, `external_company_id`, `external_producer`
- External users can have `telegram_username` for notifications (optional)

## Testing

### Test Flow

1. Obtain a valid JWT token from the external app
2. Navigate to: `https://booking-room.tkilocal.biz.id/auth/token/{jwt_token}`
3. Verify the token is processed correctly
4. Complete registration if needed
5. Access booking endpoints
6. Verify notifications work (if telegram_username provided)

### Test Tokens

You can test with a real JWT token from Katalis app or create a test token for development.

## Support

For issues or questions, contact the backend team or check the backend API documentation.
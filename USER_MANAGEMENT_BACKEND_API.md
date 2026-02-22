# User Management Backend API Documentation

Dokumentasi endpoint backend yang dibutuhkan untuk fitur User Management di frontend.

## Overview

User Management memungkinkan admin untuk:
- Melihat semua user yang terdaftar di sistem
- Mengubah role user (menjadi admin atau user biasa)
- Mengaktifkan/menonaktifkan user

## Required Endpoints

### 1. Get All Users

**Endpoint:** `GET /api/v1/admin/users`

**Authentication:** Required (JWT Token - Admin only)

**Query Parameters:**
- `role` (optional): Filter by role
  - `all` (default): Return all users
  - `admin`: Return only admin users

**Success Response (200 OK):**
```json
{
  "users": [
    {
      "id": 1,
      "telegram_id": 123456789,
      "first_name": "John",
      "last_name": "Doe",
      "username": "johndoe",
      "is_admin": true,
      "is_active": true,
      "avatar": "https://t.me/i/userpic/320/123456789.jpg",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "telegram_id": 987654321,
      "first_name": "Jane",
      "last_name": null,
      "username": "janedoe",
      "is_admin": false,
      "is_active": true,
      "avatar": null,
      "created_at": "2024-01-16T14:20:00Z"
    }
  ],
  "total": 2
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Not enough permissions"
  }
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "error": {
    "code": "SERVER_ERROR",
    "message": "Failed to fetch users"
  }
}
```

---

### 2. Toggle User Admin Role

**Endpoint:** `PATCH /api/v1/admin/users/{userId}/admin`

**Authentication:** Required (JWT Token - Admin only)

**Path Parameters:**
- `userId` (integer): ID of the user to update

**Request Body:**
```json
{
  "is_admin": true
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "telegram_id": 987654321,
    "first_name": "Jane",
    "last_name": null,
    "username": "janedoe",
    "is_admin": true,
    "is_active": true,
    "avatar": null,
    "created_at": "2024-01-16T14:20:00Z"
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Not enough permissions"
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User not found"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request data"
  }
}
```

---

### 3. Toggle User Active Status

**Endpoint:** `PATCH /api/v1/admin/users/{userId}/status`

**Authentication:** Required (JWT Token - Admin only)

**Path Parameters:**
- `userId` (integer): ID of the user to update

**Request Body:**
```json
{
  "is_active": false
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": 2,
    "telegram_id": 987654321,
    "first_name": "Jane",
    "last_name": null,
    "username": "janedoe",
    "is_admin": false,
    "is_active": false,
    "avatar": null,
    "created_at": "2024-01-16T14:20:00Z"
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Not enough permissions"
  }
}
```

**Error Response (404 Not Found):**
```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "User not found"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request data"
  }
}
```

---

## Database Schema

Users table should have the following fields:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT,
    username TEXT UNIQUE,
    is_admin BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    avatar TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Important Notes

1. **Authentication**: All endpoints require JWT token authentication and admin role verification
2. **Soft Delete**: Use `is_active` flag for soft delete instead of hard delete
3. **Last Admin**: There's NO restriction on removing admin role from the last admin (as per user request)
4. **Inactive Users**: Users with `is_active = false` should not be able to:
   - Create new bookings
   - Login to the system
5. **Response Format**: Always use consistent response format with `success` and `data` fields
6. **Error Handling**: Return appropriate HTTP status codes with descriptive error messages
7. **Date Format**: Use ISO 8601 format for timestamps (`YYYY-MM-DDTHH:mm:ssZ`)

## Testing Endpoints

You can test these endpoints using curl or Postman:

### Get All Users
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Only Admins
```bash
curl -X GET "http://localhost:8000/api/v1/admin/users?role=admin" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Toggle Admin Role
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/2/admin" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_admin": true}'
```

### Toggle Active Status
```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/users/2/status" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
```

## Frontend Integration

Frontend sudah mengimplementasikan:
- API functions di `lib/api.ts`
- Custom hooks di `lib/hooks/useUsers.ts`
- UserCard component di `components/user/UserCard.tsx`
- User management page di `app/(main)/admin/users/page.tsx`

Pastikan backend endpoint sesuai dengan dokumentasi ini agar frontend bisa berfungsi dengan baik.
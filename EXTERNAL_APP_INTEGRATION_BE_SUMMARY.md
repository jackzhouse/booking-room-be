# External App Integration (Katalis) - Backend Implementation Summary

## Overview
Dokumentasi ini menjelaskan implementasi integrasi dengan aplikasi eksternal (Katalis) untuk memungkinkan user dari aplikasi lain mengakses sistem Booking Room.

## Implementation Date
4 Maret 2026

## What Was Implemented

### 1. **Model Updates** (`app/models/user.py`)
- Menambahkan field baru untuk mendukung user eksternal:
  - `telegram_username`: Username Telegram untuk user eksternal (opsional)
  - `external_user_id`: User ID dari aplikasi eksternal (Katalis)
  - `external_company_id`: Company ID dari aplikasi eksternal
  - `external_producer`: Nama aplikasi eksternal (e.g., "katalis")
- Membuat `telegram_id` menjadi optional untuk user eksternal

### 2. **Schema Updates** (`app/schemas/auth.py`)
Menambahkan schema baru untuk integrasi eksternal:
- `ExternalTokenVerifyRequest`: Request untuk verify token eksternal
- `ExternalTokenVerifyResponse`: Response dari verify token
- `ExternalRegisterRequest`: Request untuk registrasi user eksternal
- `ExternalRegisterResponse`: Response dari registrasi user
- Mengupdate `UserResponse` untuk mencakup field eksternal

### 3. **Configuration Updates** (`app/core/config.py`)
Menambahkan environment variable baru:
- `KATALIS_PRODUCER`: Nama producer (default: "katalis")

### 4. **Security Updates** (`app/core/security.py`)
Menambahkan fungsi baru:
- `verify_external_token(token)`: Decode dan validasi JWT token dari Katalis
  - Validasi signature dengan `SECRET_KEY` (sama dengan BE JWT token)
  - Validasi producer field
  - Validasi required fields (userId, companyId)

### 5. **API Endpoints** (`app/api/v1/auth.py`)
Menambahkan 2 endpoint baru:

#### a. `POST /api/v1/auth/external/verify-token`
**Purpose**: Verify token eksternal dan cek status registrasi user

**Request Body**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (User Not Registered)**:
```json
{
  "success": true,
  "registered": false,
  "user_id": "695dcff40cdc7726a29f5006",
  "company_id": "0000000074739c67c2a1d6fe"
}
```

**Response (User Already Registered)**:
```json
{
  "success": true,
  "registered": true,
  "user": {
    "id": "...",
    "full_name": "...",
    "email": "...",
    "external_user_id": "...",
    "external_company_id": "...",
    "external_producer": "katalis",
    ...
  }
}
```

#### b. `POST /api/v1/auth/external/register`
**Purpose**: Register user eksternal baru

**Request Body**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "full_name": "Budi Santoso",
  "division": "Engineering",
  "email": "budi@example.com",
  "telegram_username": "budisantoso" // optional
}
```

**Response**:
```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "...",
    "full_name": "Budi Santoso",
    "division": "Engineering",
    "email": "budi@example.com",
    "telegram_username": "budisantoso",
    "external_user_id": "695dcff40cdc7726a29f5006",
    "external_company_id": "0000000074739c67c2a1d6fe",
    "external_producer": "katalis",
    "is_admin": false,
    "is_active": true,
    ...
  }
}
```

### 6. **Dependency Updates** (`app/api/deps.py`)
Mengupdate `get_current_user()` untuk mendukung dua tipe token:
1. **BE JWT Token**: Untuk user Telegram (existing flow)
2. **External App JWT Token**: Untuk user eksternal (Katalis)

Fungsi ini akan mencoba decode token sebagai BE JWT terlebih dahulu, jika gagal akan mencoba sebagai external JWT.

### 7. **Notification Updates** (`app/services/telegram_service.py`)
Mengupdate fungsi-fungsi notifikasi untuk menampilkan username yang benar untuk user eksternal:
- `notify_new_booking()`
- `notify_booking_updated()`
- `notify_booking_cancelled()`
- `notify_consumption_group()`
- `notify_verification_group_booking()`

Untuk user eksternal:
- Jika `telegram_username` tersedia → gunakan itu
- Jika tidak → gunakan `full_name`

### 8. **Environment Configuration** (`.env.example`)
Katalis menggunakan SECRET_KEY yang sama dengan BE untuk encode/decode JWT:
```env
SECRET_KEY=your-jwt-secret-key-minimum-32-characters-long
# Share SECRET_KEY dengan Katalis untuk validasi token
```

## Integration Flow

### 1. First-Time User (Not Registered)
```
User from Katalis App
    ↓
Click "Book Room" link with Bearer token
    ↓
POST /api/v1/auth/external/verify-token
    ↓
Response: registered=false, user_id, company_id
    ↓
Show registration form to user
    ↓
User fills: full_name, division, email, telegram_username (optional)
    ↓
POST /api/v1/auth/external/register
    ↓
Create user in database
    ↓
User can now access dashboard and make bookings
```

### 2. Existing Registered User
```
User from Katalis App
    ↓
Click "Book Room" link with Bearer token
    ↓
POST /api/v1/auth/external/verify-token
    ↓
Response: registered=true, user data
    ↓
Redirect to dashboard
    ↓
User can make bookings
```

### 3. Making Bookings (Protected Endpoints)
```
User makes booking request
    ↓
Bearer token in Authorization header (Katalis JWT)
    ↓
get_current_user() validates token
    ↓
User is authenticated as external user
    ↓
Booking created successfully
    ↓
Notifications sent to Telegram groups
```

## Expected Token Structure

Katalis harus mengirim JWT token dengan struktur berikut:

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

**Required Fields**:
- `producer`: Harus bernilai "katalis"
- `userId`: User ID unik dari Katalis
- `companyId`: Company ID dari Katalis

**Optional Fields**:
- `accountId`
- `roles`
- `permission`

## Authentication Flow for Protected Endpoints

Semua endpoint yang menggunakan `Depends(get_current_user)` sekarang mendukung dua tipe token:

```python
@router.get("/protected-endpoint")
async def protected_route(current_user: User = Depends(get_current_user)):
    # Works with both:
    # 1. BE JWT token (Telegram users)
    # 2. Katalis JWT token (External users)
    pass
```

## Testing

### Test Script
File: `test_external_app_integration.py`

### Running Tests

1. Start the server:
```bash
uvicorn app.main:app --reload
```

2. Run test script:
```bash
python test_external_app_integration.py
```

### Manual Testing with cURL

#### 1. Verify Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/external/verify-token \
  -H "Content-Type: application/json" \
  -d '{"token": "YOUR_KATALIS_JWT_TOKEN"}'
```

#### 2. Register User
```bash
curl -X POST http://localhost:8000/api/v1/auth/external/register \
  -H "Content-Type: application/json" \
  -d '{
    "token": "YOUR_KATALIS_JWT_TOKEN",
    "full_name": "Budi Santoso",
    "division": "Engineering",
    "email": "budi@example.com",
    "telegram_username": "budisantoso"
  }'
```

#### 3. Access Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_KATALIS_JWT_TOKEN"
```

## Database Changes

### User Collection Structure
```javascript
{
  "_id": ObjectId("..."),
  "telegram_id": null, // null for external users
  "full_name": "Budi Santoso",
  "username": null,
  "avatar_url": null,
  "division": "Engineering",
  "email": "budi@example.com",
  "telegram_username": "budisantoso", // for Telegram tagging in notifications
  "external_user_id": "695dcff40cdc7726a29f5006",
  "external_company_id": "0000000074739c67c2a1d6fe",
  "external_producer": "katalis",
  "is_admin": false,
  "is_active": true,
  "created_at": ISODate("2026-03-04T03:43:00.000Z"),
  "updated_at": ISODate("2026-03-04T03:43:00.000Z"),
  "last_login_at": ISODate("2026-03-04T03:43:00.000Z")
}
```

## Important Notes

### Security
1. **Secret Key**: Katalis dan Booking Room BE menggunakan **SECRET_KEY yang sama** untuk encode/decode JWT token. Tidak perlu secret key terpisah.
2. **Token Validation**: Semua validasi dilakukan di server-side, tidak ada client-side validation
3. **HTTPS**: Production environment harus menggunakan HTTPS untuk mengirim token dengan aman

### User Identification
- Telegram users: diidentifikasi oleh `telegram_id`
- External users: diidentifikasi oleh `external_user_id`
- Kedua tipe user memiliki record yang sama di collection `users`

### Permissions
- External users selalu regular user (`is_admin: false`)
- Hanya admin Telegram yang bisa menjadi admin

### Notifications
- External users dengan `telegram_username` akan ditag dengan `@username` di notifikasi Telegram
- External users tanpa `telegram_username` hanya akan ditampilkan nama lengkap

## Frontend Integration Guide

Lihat dokumentasi terpisah: `EXTERNAL_APP_INTEGRATION_FE_GUIDE.md`

## Troubleshooting

### Error: "Invalid token"
- Pastikan `KATALIS_SECRET_KEY` di environment sudah benar
- Pastikan token tidak expired
- Pastikan token struktur valid (ada producer, userId, companyId)

### Error: "User already registered"
- User dengan `external_user_id` yang sama sudah terdaftar
- User bisa langsung login tanpa registrasi ulang

### Error: "Could not validate credentials" pada protected endpoint
- Pastikan token dikirim di header: `Authorization: Bearer <token>`
- Pastikan token masih valid dan tidak expired

### Notifications tidak menampilkan username
- Pastikan user mengisi `telegram_username` saat registrasi
- Tanpa `telegram_username`, notifikasi akan menampilkan nama lengkap saja

## Future Enhancements

1. **Support Multiple External Apps**: Extend to support apps other than Katalis
2. **Token Refresh**: Implement refresh token mechanism for external users
3. **SSO Integration**: Direct SSO with Katalis instead of JWT token passing
4. **Role Mapping**: Map external roles to internal permissions
5. **User Profile Updates**: Allow external users to update their profile

## Files Modified

1. `app/models/user.py` - Added external user fields
2. `app/schemas/auth.py` - Added external app schemas
3. `app/core/config.py` - Added Katalis configuration
4. `app/core/security.py` - Added token verification function
5. `app/api/v1/auth.py` - Added verify-token and register endpoints
6. `app/api/deps.py` - Updated get_current_user for dual token support
7. `app/services/telegram_service.py` - Updated notification logic
8. `.env.example` - Added Katalis configuration examples

## Files Created

1. `EXTERNAL_APP_INTEGRATION_FE_GUIDE.md` - Frontend integration guide
2. `test_external_app_integration.py` - Test script for external app integration
3. `EXTERNAL_APP_INTEGRATION_BE_SUMMARY.md` - This documentation

## Contact

Untuk pertanyaan atau clarifikasi terkait implementasi ini, hubungi tim development Booking Room.
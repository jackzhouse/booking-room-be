# PRD — Backend
## Aplikasi Booking Ruang Meeting
**Versi:** 1.0.0  
**Tanggal:** Februari 2025  
**Tech Stack:** Python · FastAPI · MongoDB · Telegram Bot API

---

## 1. Overview

Backend bertugas sebagai inti sistem: mengelola autentikasi via Telegram, menyimpan dan memvalidasi data booking, serta mengirimkan notifikasi ke grup Telegram. Dibangun dengan FastAPI dan MongoDB sebagai database utama.

---

## 2. Tech Stack & Dependencies

| Komponen | Teknologi |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| Database | MongoDB (via Motor - async driver) |
| ODM | Beanie (MongoDB ODM untuk Python) |
| Auth | JWT (python-jose) + Telegram Hash Verification |
| Bot Telegram | python-telegram-bot v20+ |
| Validasi | Pydantic v2 |
| Testing | Pytest + httpx |
| Linting | Ruff + Black |

---

## 3. Struktur Folder

```
backend/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── core/
│   │   ├── config.py            # Settings dari .env
│   │   ├── database.py          # Koneksi MongoDB (Motor)
│   │   └── security.py          # JWT + Telegram hash verifier
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py          # Endpoint auth Telegram
│   │   │   ├── bookings.py      # CRUD booking
│   │   │   ├── rooms.py         # CRUD ruangan
│   │   │   ├── settings.py      # App settings (jam ops, grup TG)
│   │   │   └── admin.py         # Admin-only endpoints
│   │   └── deps.py              # Dependency injection
│   ├── models/                  # Beanie Document models (MongoDB)
│   │   ├── user.py
│   │   ├── room.py
│   │   ├── booking.py
│   │   ├── booking_history.py
│   │   └── setting.py
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── booking.py
│   │   ├── room.py
│   │   └── admin.py
│   ├── services/
│   │   ├── booking_service.py   # Business logic booking
│   │   ├── conflict_service.py  # Conflict checker
│   │   └── telegram_service.py  # Kirim notifikasi Telegram
│   └── bot/
│       ├── bot.py               # Setup bot & dispatcher
│       ├── handlers/
│       │   ├── start.py         # /start
│       │   ├── mybooking.py     # /mybooking
│       │   ├── schedule.py      # /schedule
│       │   └── cancel.py        # /cancel
│       └── webhook.py           # Webhook handler (terintegrasi FastAPI)
├── tests/
│   ├── test_auth.py
│   ├── test_bookings.py
│   └── test_conflict.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## 4. MongoDB Collections & Document Schema

### 4.1 Collection: `users`
```json
{
  "_id": "ObjectId",
  "telegram_id": 123456789,
  "full_name": "Budi Santoso",
  "username": "budisantoso",
  "avatar_url": "https://...",
  "division": "Engineering",
  "is_admin": false,
  "is_active": true,
  "created_at": "2025-02-01T08:00:00Z",
  "last_login_at": "2025-02-20T09:00:00Z"
}
```
**Index:** `telegram_id` (unique)

---

### 4.2 Collection: `rooms`
```json
{
  "_id": "ObjectId",
  "name": "Ruang Meeting 1",
  "capacity": 10,
  "facilities": ["proyektor", "AC", "whiteboard", "TV"],
  "location": "Lantai 2",
  "is_active": true,
  "created_at": "2025-02-01T08:00:00Z"
}
```

---

### 4.3 Collection: `bookings`
```json
{
  "_id": "ObjectId",
  "booking_number": "BK-00123",
  "user_id": "ObjectId",
  "user_snapshot": {
    "full_name": "Budi Santoso",
    "division": "Engineering",
    "telegram_id": 123456789
  },
  "room_id": "ObjectId",
  "room_snapshot": {
    "name": "Ruang Meeting 1"
  },
  "title": "Sprint Planning Q1",
  "division": "Engineering",
  "description": "Kick off sprint dengan seluruh tim dev",
  "start_time": "2025-02-24T09:00:00+07:00",
  "end_time": "2025-02-24T11:00:00+07:00",
  "status": "active",
  "cancelled_at": null,
  "cancelled_by": null,
  "created_at": "2025-02-20T10:00:00Z",
  "updated_at": "2025-02-20T10:00:00Z"
}
```
**Index:** `room_id + start_time + end_time` (compound, untuk conflict check)  
**Index:** `user_id`, `status`

> **Catatan:** `user_snapshot` dan `room_snapshot` disimpan sebagai embedded document untuk menjaga data historis tetap akurat meskipun data user/room berubah di kemudian hari.

---

### 4.4 Collection: `booking_history`
```json
{
  "_id": "ObjectId",
  "booking_id": "ObjectId",
  "booking_number": "BK-00123",
  "changed_by": "ObjectId",
  "action": "updated",
  "old_data": {
    "room_snapshot": { "name": "Ruang Meeting 1" },
    "start_time": "2025-02-24T09:00:00+07:00",
    "end_time": "2025-02-24T11:00:00+07:00"
  },
  "new_data": {
    "room_snapshot": { "name": "Ruang Meeting 2" },
    "start_time": "2025-02-24T13:00:00+07:00",
    "end_time": "2025-02-24T15:00:00+07:00"
  },
  "changed_at": "2025-02-20T11:00:00Z"
}
```

---

### 4.5 Collection: `settings`
```json
[
  { "key": "operating_hours_start", "value": "08:00", "description": "Jam mulai operasional booking" },
  { "key": "operating_hours_end",   "value": "18:00", "description": "Jam selesai operasional booking" },
  { "key": "telegram_group_id",     "value": "-1001234567890", "description": "ID grup Telegram tujuan notifikasi" },
  { "key": "booking_counter",       "value": "0", "description": "Counter untuk generate booking number" }
]
```
Semua dokumen settings menyertakan `updated_at` dan `updated_by` (ObjectId user).

---

## 5. API Endpoints

### 5.1 Auth
| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| POST | `/api/v1/auth/telegram` | Login via Telegram Login Widget | Public |
| POST | `/api/v1/auth/tma` | Login via Telegram Mini App initData | Public |
| GET | `/api/v1/auth/me` | Data user yang sedang login | 🔒 User |

**Verifikasi Telegram Hash:**  
Backend melakukan verifikasi `hash` menggunakan `HMAC-SHA256` dengan `BOT_TOKEN`. Jika valid, generate JWT dan return ke client. Jika gagal → 401.

---

### 5.2 Rooms
| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/v1/rooms` | List semua ruangan aktif | 🔒 User |
| GET | `/api/v1/rooms/{id}/schedule` | Jadwal ruangan by date range | 🔒 User |

**Query params `/schedule`:** `?start=2025-02-24&end=2025-02-24`

---

### 5.3 Bookings
| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/v1/bookings` | List booking milik user sendiri | 🔒 User |
| POST | `/api/v1/bookings` | Buat booking baru | 🔒 User |
| GET | `/api/v1/bookings/{id}` | Detail booking | 🔒 User |
| PATCH | `/api/v1/bookings/{id}` | Edit / reschedule booking | 🔒 Owner |
| DELETE | `/api/v1/bookings/{id}` | Cancel booking | 🔒 Owner |

**Request Body POST `/bookings`:**
```json
{
  "room_id": "ObjectId string",
  "title": "Sprint Planning Q1",
  "division": "Engineering",
  "description": "Kick off sprint dengan seluruh tim dev",
  "start_time": "2025-02-24T09:00:00+07:00",
  "end_time": "2025-02-24T11:00:00+07:00"
}
```

**Response Error Conflict (409):**
```json
{
  "detail": "Ruangan sudah dibooking oleh Andi (Engineering) pukul 09:00–11:00 WIB"
}
```

---

### 5.4 Admin
| Method | Endpoint | Deskripsi | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/bookings` | Semua booking semua user | 🔒 Admin |
| DELETE | `/api/v1/admin/bookings/{id}` | Cancel booking siapapun | 🔒 Admin |
| GET | `/api/v1/admin/rooms` | Kelola ruangan | 🔒 Admin |
| POST | `/api/v1/admin/rooms` | Tambah ruangan | 🔒 Admin |
| PATCH | `/api/v1/admin/rooms/{id}` | Edit ruangan | 🔒 Admin |
| PATCH | `/api/v1/admin/rooms/{id}/toggle` | Aktif / nonaktif ruangan | 🔒 Admin |
| GET | `/api/v1/admin/settings` | Lihat semua settings | 🔒 Admin |
| PATCH | `/api/v1/admin/settings/{key}` | Update setting | 🔒 Admin |
| POST | `/api/v1/admin/settings/test-notification` | Test kirim notif ke grup Telegram | 🔒 Admin |
| GET | `/api/v1/admin/users` | List semua user terdaftar | 🔒 Admin |

---

## 6. Business Logic

### 6.1 Conflict Checker

```
Saat booking baru / edit masuk:
  1. Ambil jam operasional dari collection settings
  2. Validasi start_time dan end_time berada dalam jam operasional
  3. Validasi durasi minimal 15 menit
  4. Query MongoDB untuk cek overlap di room yang sama:
       - room_id sama
       - status = "active"
       - start_time < new_end_time  (booking lama mulai sebelum baru selesai)
       - end_time   > new_start_time (booking lama selesai setelah baru mulai)
       - Untuk EDIT: exclude _id milik booking sendiri
  5. Jika ditemukan → return 409 dengan detail info booking yang bentrok
  6. Jika bersih → simpan, increment booking_counter, kirim notifikasi Telegram
```

### 6.2 Booking Number Generator

Format: `BK-XXXXX` (zero-padded 5 digit)  
Gunakan MongoDB `findOneAndUpdate` dengan `$inc` pada `settings.booking_counter` untuk atomic increment.

### 6.3 Admin Override

Jika `current_user.is_admin == true`, conflict checker dan validasi jam operasional dilewati. Admin dapat booking kapan saja.

---

## 7. Telegram Bot

### 7.1 Mode: Webhook

Bot berjalan mode webhook, terintegrasi langsung dalam FastAPI di endpoint:
```
POST /api/v1/webhook/telegram
```

### 7.2 Commands

| Command | Deskripsi |
|---|---|
| `/start` | Sambutan + panduan singkat + link app |
| `/mybooking` | Tampilkan booking aktif milik user (lookup by telegram_id) |
| `/schedule` | Jadwal hari ini semua ruangan |
| `/schedule DD-MM-YYYY` | Jadwal tanggal tertentu semua ruangan |
| `/cancel BK-XXXXX` | Cancel booking milik sendiri via Telegram |

Jika user belum terdaftar (telegram_id tidak ditemukan di collection users), bot membalas:
> "Kamu belum terdaftar. Silakan login dulu di [link app] menggunakan akun Telegram kamu."

### 7.3 Format Notifikasi ke Grup

**Booking Baru:**
```
Informasi Penggunaan Ruang Meeting

Budi Santoso dari Divisi Engineering telah menjadwalkan penggunaan ruangan:

Ruang: Ruang Meeting 1
Tanggal: Senin, 24 Februari 2025
Waktu: 09.00 sampai 11.00 WIB
Keperluan: Sprint Planning Q1
Deskripsi: Kick off sprint dengan seluruh tim dev.

PIC: Budi Santoso (@budisantoso)
Booking: #BK-00123

Mohon koordinasi dengan PIC bila diperlukan.

Pesan otomatis dari Bot Booking Room.
```

**Booking Diubah:**
```
Perubahan Penggunaan Ruang Meeting

Budi Santoso dari Divisi Engineering telah memperbarui jadwal penggunaan ruangan:

Perubahan:
• Ruangan
• Tanggal/jam

Ruang: Ruang Meeting 2
Tanggal: Senin, 24 Februari 2025
Waktu: 13.00 sampai 15.00 WIB
Keperluan: Sprint Planning Q1

PIC: Budi Santoso (@budisantoso)
Booking: #BK-00123

Mohon gunakan jadwal terbaru ini sebagai acuan.

Pesan otomatis dari Bot Booking Room.
```

**Booking Dibatalkan:**
```
Pembatalan Penggunaan Ruang Meeting

Budi Santoso dari Divisi Engineering telah membatalkan penggunaan ruangan berikut:

Ruang: Ruang Meeting 1
Tanggal: Senin, 24 Februari 2025
Waktu: 09.00 sampai 11.00 WIB
Keperluan: Sprint Planning Q1

PIC: Budi Santoso (@budisantoso)
Booking: #BK-00123

Ruangan tersedia kembali pada jadwal tersebut.

Pesan otomatis dari Bot Booking Room.
```

---

## 8. Environment Variables

```env
# App
APP_ENV=development
SECRET_KEY=your-jwt-secret-key-min-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080        # 7 hari

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=booking_app

# Telegram
BOT_TOKEN=123456:ABC-DEF...
WEBHOOK_BASE_URL=https://yourdomain.com
ADMIN_TELEGRAM_ID=123456789     # Telegram ID super admin (untuk set is_admin=true otomatis saat pertama login)
```

---

## 9. Validasi & Error Handling

| HTTP Code | Kondisi |
|---|---|
| 400 | Input tidak valid (durasi < 15 menit, jam di luar operasional, format salah) |
| 401 | Token tidak ada / expired / hash Telegram invalid |
| 403 | Akses ditolak (bukan owner atau bukan admin) |
| 404 | Booking / Room tidak ditemukan |
| 409 | Jadwal bentrok dengan booking lain |
| 422 | Pydantic validation error (field wajib kosong, tipe data salah) |
| 500 | Internal server error |

---

## 10. Security

- Semua endpoint (kecuali `/auth/*`) memerlukan JWT Bearer token di header `Authorization`
- Telegram Login Widget: hash diverifikasi dengan HMAC-SHA256 menggunakan `BOT_TOKEN`
- Telegram Mini App: `initData` diverifikasi dengan cara yang sama
- Admin endpoint dicek via dependency `require_admin` — return 403 jika bukan admin
- Edit & cancel booking hanya bisa dilakukan oleh owner atau admin
- Webhook Telegram menggunakan secret token di URL untuk mencegah request palsu

---

## 11. Out of Scope (v1.0)

- Multi-grup Telegram per ruangan (hanya 1 grup global)
- Reminder otomatis sebelum meeting dimulai
- Recurring booking (booking berulang harian/mingguan)
- Integrasi kalender eksternal (Google Calendar, Outlook)
- Setup deployment & CI/CD

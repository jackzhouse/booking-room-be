# Telegram Group Verification Feature

## Overview

Fitur ini memungkinkan admin untuk memverifikasi dan mengambil informasi grup Telegram secara otomatis hanya dengan menggunakan Group ID, tanpa perlu mengetik nama grup secara manual.

## API Endpoints

### 1. Verify Telegram Group

**Endpoint:** `GET /api/v1/telegram-groups/{group_id}/verify`

**Authentication:** Required (Admin only)

**Description:**
Memverifikasi dan mengambil informasi grup Telegram dari Telegram API. Berguna untuk memastikan bot memiliki akses ke grup dan mengambil nama grup secara otomatis.

**Request Parameters:**
- `group_id` (path parameter, required): Telegram Group Chat ID (dapat berupa angka negatif untuk grup)

**Response (Success - 200 OK):**
```json
{
  "group_id": -1001234567890,
  "group_name": "General Announcement",
  "group_type": "supergroup"
}
```

**Response Fields:**
- `group_id` (int): ID grup Telegram yang diminta
- `group_name` (str): Nama grup dari Telegram API
- `group_type` (str): Tipe grup (`group`, `supergroup`, `channel`, atau `private`)

**Error Responses:**

**400 Bad Request** - Bot tidak memiliki akses ke grup atau group_id tidak valid:
```json
{
  "detail": "Grup tidak ditemukan. Pastikan bot sudah ditambahkan ke grup ini."
}
```

Contoh error messages:
- "Grup tidak ditemukan. Pastikan bot sudah ditambahkan ke grup ini."
- "Bot diblokir di grup ini."
- "Bot bukan member dari grup ini atau tidak memiliki akses yang cukup."
- "Gagal mengambil info grup: [detail error]"

**401 Unauthorized** - User tidak terautentikasi:
```json
{
  "detail": "Not authenticated"
}
```

**403 Forbidden** - User bukan admin:
```json
{
  "detail": "Not enough permissions"
}
```

**500 Internal Server Error** - Error server:
```json
{
  "detail": "Internal server error: [detail error]"
}
```

---

### 2. Create Telegram Group

**Endpoint:** `POST /api/v1/telegram-groups`

**Authentication:** Required (Admin only)

**Description:**
Menambahkan grup Telegram baru ke sistem. `group_name` sekarang bersifat optional dan dapat diisi secara manual atau diambil otomatis dari hasil verify.

**Request Body:**
```json
{
  "group_id": -1001234567890,
  "group_name": "General Announcement"
}
```

Atau tanpa `group_name` (akan auto-fetch dari Telegram):
```json
{
  "group_id": -1001234567890
}
```

**Request Fields:**
- `group_id` (int, required): ID unik grup Telegram
- `group_name` (str, optional): Nama grup untuk display. Jika tidak diisi, akan diambil otomatis dari Telegram API

**Response (Success - 201 Created):**
```json
{
  "_id": "650abc123def456789",
  "group_id": -1001234567890,
  "group_name": "General Announcement",
  "is_active": true,
  "created_at": "2026-02-21T08:00:00.000Z",
  "updated_at": "2026-02-21T08:00:00.000Z"
}
```

---

## Usage Flow

### Flow Rekomendasi di Frontend:

1. **User mengisi Group ID**
   ```
   Input: -1001234567890
   ```

2. **User klik tombol "Cek Grup"**
   ```
   GET /api/v1/telegram-groups/-1001234567890/verify
   Headers: Authorization: Bearer <token>
   ```

3. **Backend memproses dan mengembalikan info grup**
   ```json
   {
     "group_id": -1001234567890,
     "group_name": "General Announcement",
     "group_type": "supergroup"
   }
   ```

4. **Frontend menampilkan hasil dan auto-fill form**
   ```
   ✅ Nama Grup: General Announcement
   ✅ Tipe: Supergroup
   
   Form fields otomatis terisi:
   - Group ID: -1001234567890 (readonly)
   - Group Name: General Announcement (editable)
   ```

5. **User konfirmasi dan submit form**
   ```
   POST /api/v1/telegram-groups
   Body: {
     "group_id": -1001234567890,
     "group_name": "General Announcement"
   }
   ```

---

## Error Handling Best Practices

### Di Frontend:

1. **Handle error saat verify:**
   - Tampilkan pesan error yang jelas dari backend
   - Berikan saran solusi (misal: "Pastikan bot sudah di-add ke grup")

2. **Validasi input sebelum verify:**
   - Pastikan group_id adalah angka yang valid
   - Group ID biasanya format negatif untuk grup (misal: -1001234567890)

3. **Loading state:**
   - Tampilkan spinner saat memanggil endpoint verify
   - Disable tombol submit sampai verify berhasil

4. **User feedback:**
   - Tampilkan pesan sukses dengan nama grup yang ditemukan
   - Izinkan user untuk edit nama grup jika diperlukan

---

## Technical Implementation

### Backend Service Function:

**Function:** `get_telegram_chat_info(chat_id: int)`

**Dependencies:**
- `telegram.Bot.get_chat()` method dari Telegram Bot API
- Error handling untuk berbagai Telegram API errors

**Returns:**
```python
{
    "group_id": int,
    "group_name": str,
    "group_type": str
}
```

**Raises:**
- `ValueError`: Untuk error Telegram API dengan pesan user-friendly
- `Exception`: Untuk error internal server

---

## Prerequisites

Untuk menggunakan fitur ini:

1. **Bot Telegram sudah harus di-add ke grup target**
   - Bot harus menjadi member dari grup yang akan ditambahkan
   - Bot harus memiliki permission untuk membaca informasi grup

2. **Group ID harus valid**
   - Group ID dapat diperoleh dari:
     - Forward message dari grup ke @userinfobot
     - Menggunakan Telegram Client API
     - Forward message ke grup lain dan inspect raw data

3. **Bot Token valid**
   - Pastikan `BOT_TOKEN` di environment variables sudah terisi dengan benar

---

## Example Use Cases

### Use Case 1: Admin Menambahkan Grup Baru

1. Admin membuka halaman "Tambah Telegram Group"
2. Admin mengisi Group ID: `-1001234567890`
3. Admin klik "Cek Grup"
4. Sistem menampilkan: "✅ Grup ditemukan: General Announcement"
5. Form group_name otomatis terisi dengan "General Announcement"
6. Admin klik "Simpan"
7. Grup berhasil ditambahkan ke sistem

### Use Case 2: Error Handling - Bot Belum Di-add

1. Admin mengisi Group ID: `-1009876543210`
2. Admin klik "Cek Grup"
3. Sistem menampilkan error: "❌ Grup tidak ditemukan. Pastikan bot sudah ditambahkan ke grup ini."
4. Admin mendapat feedback yang jelas dan bisa memperbaiki

### Use Case 3: Custom Group Name

1. Admin mengisi Group ID dan klik "Cek Grup"
2. Sistem menampilkan nama asli: "Marketing Team Updates"
3. Admin mengubah nama menjadi: "Marketing Team - Updates (Official)"
4. Admin simpan dengan nama custom

---

## Testing

### Manual Testing dengan cURL:

**Test verify endpoint:**
```bash
curl -X GET "https://your-api.com/api/v1/telegram-groups/-1001234567890/verify" \
  -H "Authorization: Bearer <your-admin-token>"
```

**Expected Success Response:**
```json
{
  "group_id": -1001234567890,
  "group_name": "General Announcement",
  "group_type": "supergroup"
}
```

**Test create group with auto-fetch name:**
```bash
curl -X POST "https://your-api.com/api/v1/telegram-groups" \
  -H "Authorization: Bearer <your-admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "group_id": -1001234567890,
    "group_name": "General Announcement"
  }'
```

---

## Notes

- Endpoint verify menggunakan Telegram Bot API yang memiliki rate limit
- Pastikan bot memiliki permission yang cukup di grup
- Group ID negatif menandakan supergroup atau channel
- Nama grup yang diambil adalah nama saat ini dari Telegram (real-time)
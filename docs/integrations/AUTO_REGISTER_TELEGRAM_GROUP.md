# Auto-Registration Telegram Group

## 📖 Overview

Sistem ini memungkinkan bot Telegram secara otomatis mendeteksi saat diinvite ke grup dan langsung membuat record baru di tabel `telegram_groups` di database.

## 🎯 Fitur

### 1. Auto-Registration Grup
- Saat bot diinvite ke grup Telegram baru, sistem otomatis:
  - Mendeteksi event invite melalui update `chat_member`
  - Mengambil informasi grup (ID dan nama)
  - Membuat record baru di database
  - Mengirim pesan konfirmasi ke grup

### 2. Duplicate Protection
- Jika bot diinvite ulang ke grup yang sudah terdaftar:
  - Sistem akan mendeteksi dan skip registrasi
  - Mengirim pesan konfirmasi bahwa grup sudah terdaftar

### 3. Auto-Deactivation
- Jika bot dihapus/kick dari grup:
  - Status grup diubah menjadi `is_active = False`
  - Data tetap tersimpan di database untuk histori

## 🏗️ Arsitektur

### File yang Dibuat/Diubah

#### 1. Baru: `app/bot/handlers/chat_member.py`
Handler untuk mendeteksi perubahan membership bot di grup.

**Fungsi Utama:**
- `handle_chat_member_update()` - Handle event chat_member
- `get_chat_member_handler()` - Return ChatMemberHandler

**Logic:**
```python
# Cek apakah update melibatkan bot sendiri
if new_member.user.id == bot_id:
    # Cek apakah status baru adalah "member"
    if new_member.status == "member":
        # Register grup ke database
        new_group = TelegramGroup(
            group_id=chat.id,
            group_name=chat.title,
            is_active=True
        )
        await new_group.insert()
```

#### 2. Edit: `app/bot/webhook.py`
Update konfigurasi webhook untuk menerima update `chat_member`.

**Perubahan:**
- Import `get_chat_member_handler`
- Registrasi `chat_member_handler` ke application
- Update `allowed_updates` menjadi: `["message", "callback_query", "chat_member"]`

## 🔍 Cara Kerja

### Flow Saat Bot Diinvite ke Grup Baru

1. **User invite bot ke grup**
   - User dengan admin access di grup menginvite bot

2. **Telegram mengirim update chat_member**
   - Telegram mengirim update dengan tipe `chat_member`
   - Update berisi info: `new_chat_member`, `old_chat_member`, `chat`

3. **Handler menerima update**
   - `ChatMemberHandler` di `webhook.py` menangkap update
   - Memicu fungsi `handle_chat_member_update()`

4. **Validasi**
   - Cek: Apakah update melibatkan bot sendiri?
   - Cek: Apakah status baru adalah `member`?
   - Cek: Apakah grup sudah terdaftar di database?

5. **Registrasi Grup**
   - Buat record baru di tabel `telegram_groups`
   - Field yang disimpan:
     - `group_id`: ID Telegram grup
     - `group_name`: Nama grup
     - `is_active`: `True`
     - `created_at`: Timestamp otomatis
     - `updated_at`: Timestamp otomatis

6. **Kirim Pesan Konfirmasi**
   - Bot mengirim pesan welcome ke grup
   - Berisi info grup dan command yang tersedia

## 📝 Response Pesan

### Saat Grup Baru Terdaftar:
```
🎉 *Bot Berhasil Bergabung!*

Grup ini telah terdaftar di sistem:
📝 Nama: [Nama Grup]
🆔 ID: [Grup ID]

Bot sekarang siap digunakan di grup ini!

Command yang tersedia:
📅 /schedule - Lihat jadwal ruangan
📋 /schedule DD-MM-YYYY - Lihat jadwal tanggal tertentu

Happy booking! 🚀
```

### Saat Grup Sudah Terdaftar:
```
✅ Bot sudah terdaftar di grup ini!

Grup ID: [Grup ID]
Nama: [Nama Grup]

Silakan lanjutkan menggunakan bot untuk booking ruangan.
```

### Saat Terjadi Error:
```
❌ Terjadi kesalahan saat mendaftarkan grup ini.
Silakan hubungi admin.

Error: [Error message]
```

## 🧪 Cara Testing

### 1. Setup Environment
Pastikan semua environment variable sudah terkonfigurasi:
```bash
BOT_TOKEN=<your-bot-token>
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=booking_app
```

### 2. Deploy Aplikasi
```bash
# Deploy ke production
vercel --prod

# Atau run locally
python -m uvicorn app.main:app --reload
```

### 3. Invite Bot ke Grup Baru

1. Buka Telegram grup baru
2. Pergi ke grup settings
3. Klik "Members" → "Add Member"
4. Cari nama bot Anda
5. Pilih dan invite bot

### 4. Verifikasi Hasil

**Expected Output:**
- Bot akan otomatis bergabung
- Bot akan mengirim pesan welcome ke grup
- Record baru akan terbuat di database

**Cek Database:**
```bash
# Connect ke MongoDB
mongosh

# Switch ke database
use booking_app

# Cek collection telegram_groups
db.telegram_groups.find().pretty()

# Expected output:
{
  "_id": ObjectId("..."),
  "group_id": -1001234567890,
  "group_name": "Test Group",
  "is_active": true,
  "created_at": ISODate("2026-02-23T04:59:00Z"),
  "updated_at": ISODate("2026-02-23T04:59:00Z")
}
```

### 5. Test Duplicate Protection

1. Kick bot dari grup
2. Invite bot kembali ke grup yang sama
3. Bot akan mengirim pesan "Bot sudah terdaftar"
4. Cek database: tidak ada duplicate record

### 6. Test Auto-Deactivation

1. Kick/remove bot dari grup
2. Cek database: `is_active` berubah menjadi `false`
3. Invite bot kembali: `is_active` berubah menjadi `true`

## 🔧 Troubleshooting

### Bot tidak auto-register saat diinvite

**Masalah:** Bot diinvite tapi tidak ada record di database

**Solusi:**
1. Cek apakah webhook sudah di-set dengan `allowed_updates` yang benar:
   ```bash
   # Cek webhook info
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

2. Pastikan `chat_member` ada di `allowed_updates`:
   ```json
   {
     "url": "https://your-domain.com/webhook/telegram/YOUR_TOKEN",
     "allowed_updates": ["message", "callback_query", "chat_member"]
   }
   ```

3. Cek logs aplikasi untuk error:
   ```bash
   # Jika deploy di Vercel
   vercel logs

   # Jika run locally
   # Logs akan muncul di terminal
   ```

### Pesan welcome tidak muncul

**Masalah:** Grup terdaftar tapi pesan welcome tidak dikirim

**Solusi:**
1. Pastikan bot memiliki permission untuk mengirim pesan di grup
2. Cek apakah bot diinvite dengan admin access
3. Verifikasi group tidak dalam mode "silent" atau restriction

### Error database connection

**Masalah:** Error saat menyimpan record ke database

**Solusi:**
1. Cek connection string MongoDB di `.env`
2. Pastikan database accessible dari server
3. Verifikasi collection `telegram_groups` sudah ada

## 📊 Database Schema

### Collection: `telegram_groups`

```javascript
{
  _id: ObjectId,
  group_id: Number (unique, indexed),
  group_name: String,
  is_active: Boolean (default: true, indexed),
  created_at: ISODate,
  updated_at: ISODate,
  updated_by: ObjectId (optional)
}
```

**Indexes:**
- `group_id`: Unique index
- `is_active`: Regular index

## 🔒 Security Considerations

1. **Bot Permission**: Bot tidak memerlukan admin access di grup
2. **Data Privacy**: Hanya menyimpan group_id dan group_name
3. **Access Control**: Grup yang terdaftar bisa diaktifkan/dinonaktifkan melalui admin panel
4. **Validation**: Semua input divalidasi sebelum disimpan ke database

## 🚀 Next Steps

Fitur tambahan yang bisa ditambahkan:

1. **Admin Notification**: Notifikasi ke admin saat grup baru terdaftar
2. **Group Categories**: Kategori grup (department, project, dll)
3. **Custom Commands**: Custom command per grup
4. **Group Analytics**: Statistik penggunaan bot per grup
5. **Bulk Management**: Batch aktifkan/nonaktifkan grup

## 📚 Referensi

- [Telegram Bot API - ChatMember](https://core.telegram.org/bots/api#chatmember)
- [python-telegram-bot - ChatMemberHandler](https://docs.python-telegram-bot.org/en/stable/telegram.ext.chatmemberhandler.html)
- [MongoDB Documentation](https://docs.mongodb.com/)

## 👥 Support

Jika ada masalah atau pertanyaan:
- Cek logs aplikasi
- Verifikasi konfigurasi webhook
- Hubungi admin sistem
# Fitur Konsumsi - Dokumentasi Implementasi

## 📋 Ringkasan

Fitur ini menambahkan kemampuan untuk booking ruangan dengan konsumsi, termasuk multi-group notifications dan notifikasi otomatis untuk perapian ruangan setelah meeting berakhir.

## 🎯 Fitur Utama

### 1. **Form Booking dengan Konsumsi**
- Checkbox "Tambah Konsumsi" di form booking
- Textarea untuk catatan detail konsumsi
- Pilihan grup notifikasi (dapat override default dari setting)

### 2. **Multi-Group Notifications**
Saat booking dipublish, notifikasi dikirim ke:
- **Grup yang dipilih** (user selection) - Format lengkap
- **Grup Verifikasi** (default setting) - Format lengkap (SELALU dikirim)
- **Grup Konsumsi** (default setting) - Format simpel (HANYA jika dicentang)

### 3. **Notifikasi Perapian Otomatis**
Scheduler berjalan setiap 5 menit untuk:
- Mengecek booking yang sudah berakhir
- Mengirim notifikasi perapian ke grup verifikasi
- Menandai booking sebagai sudah dinotifikasi

### 4. **Setting Grup Default**
Admin dapat mengatur:
- `default_consumption_group_id` - Grup default untuk notifikasi konsumsi
- `default_verification_group_id` - Grup default untuk notifikasi verifikasi & perapian

---

## 📱 Format Pesan Telegram

### 1. Grup Konsumsi (Simpel)
```
🍽️ Permintaan Konsumsi Meeting

📍 Ruang: Ruang Meeting 1
📅 Waktu: Senin, 24 Feb 2026 | 09:00 – 11:00 WIB
👤 PIC: Budi Santoso — (Engineering)

📝 Detail Konsumsi:
Mohon disediakan:
- 20 pcs snack box
- 20 botol air mineral

Mohon bantu menyiapkan konsumsi sesuai permintaan. Terima kasih.
```

### 2. Grup Terpilih / Verifikasi (Format Lengkap)
```
📍  Informasi Booking Ruangan, Ruang Meeting 1

📅 Senin, 24 Feb 2026 | 09:00 – 11:00 WIB

📋 Detail Booking:
• Keperluan: Sprint Planning Q1
• Deskripsi: Kick off sprint dengan seluruh tim dev engineering
• PIC: Budi Santoso — (Engineering) — @budisantoso

Rekan-rekan yang membutuhkan ruangan pada jam tersebut diharapkan dapat berkoordinasi langsung dengan @budisantoso. Terima kasih.
```

### 3. Grup Verifikasi (Perapian)
```
✅ Meeting Selesai

📍 Ruang: Ruang Meeting 1
📅 Meeting Berakhir: Senin, 24 Feb 2026 | 11:00 WIB
👤 PIC: Budi Santoso — (Engineering)

Mohon bantu dilakukan perapian/kebersihan ruangan setelah penggunaan. Terima kasih.
```

---

## 🗄️ Perubahan Database

### Model Booking (`app/models/booking.py`)
Tambah 6 field baru:
- `has_consumption: bool` - Apakah ada konsumsi
- `consumption_note: Optional[str]` - Catatan detail konsumsi
- `consumption_facilities: List[str]` - Fasilitas ruangan yang dipilih user untuk kebutuhan konsumsi
- `consumption_group_id: Optional[int]` - ID grup konsumsi (snapshot)
- `verification_group_id: Optional[int]` - ID grup verifikasi (snapshot)
- `hrd_notified: bool = False` - Flag notifikasi perapian

---

## 🔌 API Endpoints

### 1. Booking API (`/api/v1/bookings`)

#### POST `/api/v1/bookings` - Create Booking
Body request baru:
```json
{
  "room_id": "...",
  "telegram_group_id": -1001234567890,
  "title": "Meeting Title",
  "division": "Engineering",
  "description": "...",
  "start_time": "2026-02-24T09:00:00+07:00",
  "end_time": "2026-02-24T11:00:00+07:00",
  "has_consumption": true,
  "consumption_note": "Mohon disediakan 20 snack box",
  "consumption_facilities": ["proyektor", "AC"],
  "consumption_group_id": -1001111111111,  // Optional, default dari setting
  "verification_group_id": -1002222222222  // Optional, default dari setting
}
```

Behavior tambahan:
- Booking baru tetap disimpan sebagai draft (`published=false`)
- Booking baru akan ditolak jika `start_time` sudah lewat saat request dibuat
- `consumption_facilities` harus cocok dengan fasilitas pada ruangan yang dipilih
- Tidak ada auto-publish untuk draft yang sudah lewat start time

#### POST `/api/v1/bookings/{id}/publish` - Publish Booking
Mengirim multi-group notifications:
1. Grup yang dipilih (selalu)
2. Grup verifikasi (selalu, jika dikonfigurasi)
3. Grup konsumsi (hanya jika ada konsumsi/fasilitas dan dikonfigurasi)

Behavior tambahan:
- Draft yang start time-nya sudah lewat tetap boleh dipublish manual
- Update booking published menyebut field yang berubah pada pesan update
- Jika target grup utama/verifikasi berubah, grup baru menerima update dan grup lama menerima info bahwa target booking sudah dipindahkan
- Jika konsumsi dimatikan atau grup konsumsi diganti pada booking published, grup konsumsi lama menerima notifikasi pembatalan

### 2. Admin API (`/api/v1/admin`)

#### GET `/api/v1/admin/settings/group-ids` - Get Default Groups
Response:
```json
{
  "default_consumption_group_id": -1001111111111,
  "default_verification_group_id": -1002222222222
}
```

#### PUT `/api/v1/admin/settings/group-ids` - Update Default Groups
Request:
```json
{
  "default_consumption_group_id": -1001111111111,
  "default_verification_group_id": -1002222222222
}
```

---

## 🔧 Alur Notification

### Booking TANPA Konsumsi:
```
Create Booking → Publish → 
  ├─ Kirim ke Grup yang Dipilih (format lengkap)
  └─ Kirim ke Grup Verifikasi (format lengkap)
```

### Booking DENGAN Konsumsi:
```
Create Booking → Publish → 
  ├─ Kirim ke Grup yang Dipilih (format lengkap)
  ├─ Kirim ke Grup Verifikasi (format lengkap)
  └─ Kirim ke Grup Konsumsi (format simpel)

Scheduler (setiap 5 menit) → Meeting Berakhir → 
  └─ Kirim ke Grup Verifikasi (format perapian)
```

---

## ⚙️ Scheduler Configuration

Scheduler menggunakan **APScheduler** dan berjalan otomatis:

- **Interval**: Setiap 5 menit
- **Task**: `check_and_notify_ended_bookings()`
- **Filter**: Booking yang:
  - status = "active"
  - published = true
  - end_time < now
  - hrd_notified = false

---

## 📦 Dependencies

Package baru:
```txt
apscheduler==3.10.4
```

Dependencies otomatis:
- tzlocal
- pytz

---

## 🎨 Customization

### Mengubah Format Pesan
Edit di `app/services/telegram_service.py`:
- `notify_consumption_group()` - Format grup konsumsi
- `notify_verification_group_booking()` - Format grup verifikasi (booking)
- `notify_verification_group_cleanup()` - Format grup verifikasi (perapian)
- `notify_new_booking()` - Format grup yang dipilih

### Mengubah Interval Scheduler
Edit di `app/main.py` (lifespan function):
```python
scheduler.add_job(
    check_and_notify_ended_bookings,
    'interval',
    minutes=5,  # Ubah interval di sini
    id='cleanup_notifications',
    name='Send cleanup notifications for ended bookings',
    replace_existing=True
)
```

---

## 🚀 Cara Penggunaan

### 1. Setup Grup Default (Admin)
```bash
# Get current settings
GET /api/v1/admin/settings/group-ids

# Update default groups
PUT /api/v1/admin/settings/group-ids
{
  "default_consumption_group_id": -1001111111111,
  "default_verification_group_id": -1002222222222
}
```

### 2. Booking dengan Konsumsi (User)
```bash
POST /api/v1/bookings
{
  "room_id": "...",
  "telegram_group_id": -1001234567890,
  "title": "Sprint Planning",
  "has_consumption": true,
  "consumption_note": "Mohon 20 snack box dan 20 air mineral",
  "start_time": "2026-02-24T09:00:00+07:00",
  "end_time": "2026-02-24T11:00:00+07:00"
}
```

### 3. Publish Booking
```bash
POST /api/v1/bookings/{booking_id}/publish
```

Result:
- Grup yang dipilih menerima notifikasi lengkap
- Grup verifikasi menerima notifikasi lengkap
- Grup konsumsi menerima notifikasi simpel

### 4. Otomatis: Notifikasi Perapian
- Scheduler berjalan setiap 5 menit
- Setelah meeting berakhir, grup verifikasi menerima notifikasi perapian
- Booking ditandai `hrd_notified = true`

---

## 🧪 Testing

### 1. Test Create Booking
```python
# Create booking dengan konsumsi
booking_data = {
    "room_id": "...",
    "telegram_group_id": -1001234567890,
    "title": "Test Meeting",
    "has_consumption": True,
    "consumption_note": "Test consumption note",
    "start_time": "2026-02-24T09:00:00+07:00",
    "end_time": "2026-02-24T10:00:00+07:00"
}
```

### 2. Test Scheduler
```python
from app.services.scheduler_service import check_and_notify_ended_bookings

# Manual trigger scheduler check
await check_and_notify_ended_bookings()
```

### 3. Test API Settings
```bash
# Get group settings
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/admin/settings/group-ids

# Update group settings
curl -X PUT -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"default_consumption_group_id": -1001111111111}' \
  http://localhost:8000/api/v1/admin/settings/group-ids
```

---

## 📝 Notes

1. **Grup ID Format**: Gunakan format negatif untuk grup (e.g., -1001234567890)
2. **Default Behavior**: Jika user tidak pilih grup konsumsi/verifikasi, otomatis pakai default dari setting
3. **Validation**: Booking hanya dikirim ke grup yang aktif dan ada di database
4. **Snapshot**: Group ID disimpan sebagai snapshot di booking untuk consistency
5. **Scheduler**: Hanya mengirim notifikasi perapian sekali per booking (di-check via `hrd_notified` flag)

---

## 🔍 Troubleshooting

### Scheduler tidak berjalan?
- Cek logs: `[Scheduler] Found X bookings needing cleanup notification`
- Pastikan APScheduler terinstall: `pip3 install apscheduler==3.10.4`
- Cek apakah app dijalankan dengan lifespan yang benar

### Notifikasi tidak terkirim?
- Cek grup ID (harus format negatif)
- Cek grup aktif di database
- Cek bot token valid
- Cek bot sudah ditambahkan ke grup

### Booking tidak ada data konsumsi?
- Cek `has_consumption = true` di request
- Cek field `consumption_note` dan `consumption_group_id` terisi

---

## 📅 Changelog

### v1.0.0 (2026-02-23)
- ✅ Tambah model field konsumsi
- ✅ Multi-group notifications
- ✅ Scheduler untuk notifikasi perapian
- ✅ API untuk manage grup default
- ✅ Format pesan Telegram friendly & formal

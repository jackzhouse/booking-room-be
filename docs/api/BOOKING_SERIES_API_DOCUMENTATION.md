# Booking Multi-Hari (Series) API

Satu permintaan membuat booking untuk beberapa hari (maks 14) dengan detail yang sama dan jam per hari yang boleh berbeda. Tiap hari tetap satu dokumen `Booking` (cek bentrok, edit, batal, dan penutupan otomatis berjalan per hari); hari-hari itu dihubungkan lewat `series_id`. Semua endpoint butuh login, di `/api/v1/bookings/series...`.

## Alur

1. `POST /bookings/series` → semua hari tersimpan sebagai **draft** (tanpa notifikasi).
2. `POST /bookings/series/{series_id}/publish` → **satu pesan Telegram gabungan** per grup (utama, verifikasi, konsumsi bila ada). Memanggil `POST /bookings/{id}/publish` pada salah satu hari juga mempublish seluruh seri.
3. Ubah jam satu hari: `PUT /bookings/{id}` → pesan gabungan **diedit di tempat** (hari yang berubah ditandai "(diubah)"), tidak ada pesan baru.
4. Batal satu hari: `POST /bookings/{id}/cancel` → pesan pembatalan baru untuk hari itu, pesan gabungan diedit (hari itu dicoret).
5. Batal semua: `POST /bookings/series/{series_id}/cancel` → satu pesan pembatalan baru per grup berisi semua tanggal yang dibatalkan, pesan gabungan diedit.
6. Selesai (scheduler) tetap per hari.

## POST `/bookings/series`

```json
{
  "room_id": "507f1f77bcf86cd799439012",
  "telegram_group_id": -1001234567890,
  "title": "Onboarding Sales",
  "division": "Sales",
  "description": null,
  "slots": [
    {"start_time": "2026-10-21T09:00:00+07:00", "end_time": "2026-10-21T11:00:00+07:00"},
    {"start_time": "2026-10-22T09:00:00+07:00", "end_time": "2026-10-22T11:00:00+07:00"},
    {"start_time": "2026-10-23T13:00:00+07:00", "end_time": "2026-10-23T15:00:00+07:00"}
  ],
  "has_consumption": false,
  "consumption_note": null,
  "consumption_facilities": [],
  "consumption_group_id": null,
  "verification_group_id": null
}
```

Field selain `slots` sama dengan `POST /bookings`. `201`:

```json
{ "series_id": "9f1c...", "bookings": [ { "...BookingResponse...": "..." } ] }
```

`bookings` terurut menurut `start_time`; setiap item punya `series_id`.

Aturan:
- 1–14 slot, satu slot per tanggal WIB (tanggal tidak boleh dobel), `end_time` setelah `start_time` di hari yang sama.
- Setiap hari divalidasi seperti booking biasa: jam sudah lewat, jam operasional dan durasi minimal (non-admin), bentrok dengan booking aktif lain.
- **Semua-atau-tidak-sama-sekali.** Bila ada hari yang gagal, tidak ada booking tersimpan dan respons `409`:

```json
{
  "detail": {
    "message": "Ada hari yang tidak bisa dibooking. Tidak ada booking yang disimpan.",
    "conflicts": [
      {"date": "2026-10-22", "reason": "Ruangan sudah dipakai ..."}
    ]
  }
}
```

- Kesalahan lain (ruangan/grup tidak ditemukan, slot tidak valid) → `409` dengan `detail` berupa string, sama seperti `POST /bookings`. Bila penyimpanan hari ke-n gagal setelah validasi, hari yang sudah tersimpan dihapus (tanpa transaksi Mongo, jadi best-effort).

## GET `/bookings/series/{series_id}`

Semua hari dalam seri (termasuk yang dibatalkan/selesai), terurut. Semua user login boleh melihat, seperti detail booking. `404` bila tidak ada.

## POST `/bookings/series/{series_id}/publish`

Publish semua hari draft yang masih aktif. Hanya pemilik atau admin. `400` bila seri tidak ada, tidak punya akses, atau tidak ada draft ("Booking sudah dipublish").

## POST `/bookings/series/{series_id}/cancel`

Batalkan semua hari aktif yang belum berakhir (hari yang sudah lewat tidak disentuh). Hanya pemilik atau admin. `400` bila tidak ada hari yang bisa dibatalkan.

## Edit hari dalam seri (`PUT /bookings/{id}`)

Untuk anggota seri hanya **jam** yang bisa diubah, karena judul, ruangan, grup, dan konsumsi tampil di satu pesan gabungan. Mengirim ulang nilai yang sama (seperti form edit) diterima; nilai berbeda ditolak `409`:

- `Booking bagian dari seri, hanya jam yang bisa diubah. Tidak bisa mengubah: judul, ...`
- `Tanggal booking dalam seri tidak bisa diubah. Batalkan hari ini dan buat booking baru.`

## Catatan teknis

- `Booking.series_id` opsional (index); booking lama dan booking tunggal bernilai `null`. Tidak perlu migrasi.
- `generate_booking_number` sekarang satu operasi atomik (`find_one_and_update` dengan pipeline) agar booking beruntun tidak mendapat nomor sama. Baris counter harus sudah ada (sudah di production); index `settings.key` saat ini tidak unik, jadi pembuatan pertama secara paralel bisa menggandakan baris counter.
- Referensi pesan Telegram (`telegram_messages`) disimpan identik di semua hari seri.

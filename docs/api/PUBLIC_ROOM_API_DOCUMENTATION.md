# Public Room API

Endpoint tanpa login untuk halaman yang dibuka dari QR code ruangan (`/r/<room_id>` di frontend). Hanya baca. Tersedia di `/api/v1/public/...` (dan `/booking/api/v1/public/...`).

## GET `/api/v1/public/rooms/{room_id}`

Detail ruangan.

```json
{
  "id": "507f1f77bcf86cd799439012",
  "name": "Ruang Meeting 1",
  "capacity": 10,
  "location": "Lantai 2",
  "facilities": ["AC", "Proyektor"],
  "photo_url": "/api/v1/rooms/507f1f77bcf86cd799439012/photo?v=1760000000"
}
```

`404` bila ruangan tidak ada, ID bukan ObjectId valid, atau ruangan nonaktif (status nonaktif tidak dibocorkan).

## GET `/api/v1/public/rooms/{room_id}/schedule?date=YYYY-MM-DD`

Booking aktif ruangan pada satu hari. Hari dihitung dalam WIB (Asia/Jakarta), bukan zona server.

```json
[
  {
    "start_time": "2026-05-04T02:00:00Z",
    "end_time": "2026-05-04T03:30:00Z",
    "title": "Sprint Planning",
    "division": "Teknologi"
  }
]
```

- Waktu dalam UTC (`Z`); tampilkan dalam WIB di klien.
- Hanya `status == "active"`. Booking draft (belum dipublish) tetap memblokir slot tetapi `title`-nya `"Terisi"`.
- Tidak mengembalikan nama pemesan, deskripsi, konsumsi, nomor atau ID booking.
- `404` seperti endpoint detail. Satu hari per permintaan.

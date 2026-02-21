# Frontend Changes - Draft/Publish Booking Workflow

## Overview
Dokumentasi ini menjelaskan perubahan yang diperlukan di Frontend untuk mendukung workflow Draft/Publish booking.

---

## Table of Contents

1. [Booking List View](#1-booking-list-view)
2. [Booking Detail View](#2-booking-detail-view)
3. [Create Booking Form](#3-create-booking-form)
4. [Publish Function](#4-implement-publish-booking-function)
5. [User Display](#5-update-user-display)
6. [Success Messages](#6-update-notification-messages)
7. [Styling](#7-styling-recommendations)

---

## 1. Booking List View

### Perubahan yang Diperlukan

#### A. Tampilkan Status Booking
Gunakan field `booking.published` untuk menampilkan status.

```typescript
interface Booking {
  id: string;
  title: string;
  published: boolean; // Field baru
  // ... fields lainnya
}
```

#### B. Status Badge
Tampilkan badge status yang berbeda antara Draft dan Published.

```jsx
const BookingCard = ({ booking }) => {
  return (
    <div className="booking-card">
      <h3>{booking.title}</h3>
      
      {/* Status Badge */}
      <div className={`status-badge ${booking.published ? 'published' : 'draft'}`}>
        {booking.published ? '✅ Published' : '📝 Draft'}
      </div>
      
      {/* Tombol Publish - hanya muncul jika draft */}
      {!booking.published && (
        <button 
          className="btn-publish"
          onClick={() => handlePublish(booking.id)}
        >
          📢 Publish Booking
        </button>
      )}
    </div>
  );
};
```

#### C. Filter Berdasarkan Status
Tambahkan filter untuk melihat semua, hanya draft, atau hanya published.

```jsx
const [statusFilter, setStatusFilter] = useState('all');

const filteredBookings = bookings.filter(booking => {
  if (statusFilter === 'all') return true;
  if (statusFilter === 'draft') return !booking.published;
  if (statusFilter === 'published') return booking.published;
  return true;
});

// Filter UI
<select 
  value={statusFilter} 
  onChange={(e) => setStatusFilter(e.target.value)}
>
  <option value="all">Semua Booking</option>
  <option value="draft">Draft Saja</option>
  <option value="published">Published Saja</option>
</select>
```

---

## 2. Booking Detail View

### Perubahan yang Diperlukan

#### A. Tampilkan Status Lengkap
Tampilkan status dengan informasi lebih jelas.

```jsx
const BookingDetail = ({ booking }) => {
  return (
    <div className="booking-detail">
      <h1>{booking.title}</h1>
      
      {/* Status Header */}
      <div className="status-section">
        <div className={`status-badge ${booking.published ? 'published' : 'draft'}`}>
          {booking.published ? '✅ Published' : '📝 Draft'}
        </div>
        
        {!booking.published && (
          <p className="status-info">
            ⚠️ Booking ini masih Draft dan belum muncul di jadwal ruangan.
          </p>
        )}
      </div>
      
      {/* Action Buttons */}
      <div className="action-buttons">
        {/* Tombol Publish - hanya untuk draft */}
        {!booking.published && (
          <button 
            className="btn btn-publish"
            onClick={() => handlePublish(booking.id)}
          >
            📢 Publish Booking
          </button>
        )}
        
        {/* Tombol Edit - selalu tersedia */}
        <button 
          className="btn btn-edit"
          onClick={() => handleEdit(booking.id)}
        >
          ✏️ Edit
        </button>
        
        {/* Tombol berbeda tergantung status */}
        {booking.published ? (
          <button 
            className="btn btn-cancel"
            onClick={() => handleCancel(booking.id)}
          >
            ❌ Cancel
          </button>
        ) : (
          <button 
            className="btn btn-delete"
            onClick={() => handleDelete(booking.id)}
          >
            🗑️ Delete
          </button>
        )}
      </div>
    </div>
  );
};
```

#### B. Draft vs Published State

**Draft Booking:**
- Tampilkan tombol: **Edit**, **Delete**, **Publish**
- Pesan: "Booking belum dipublish dan belum muncul di jadwal"

**Published Booking:**
- Tampilkan tombol: **Edit**, **Cancel**
- Pesan: "Booking sudah aktif dan muncul di jadwal"

---

## 3. Create Booking Form

### Perubahan yang Diperlukan

#### A. Pesan Sukses Update
Ubah pesan sukses setelah create booking.

```jsx
const BookingForm = () => {
  const [formData, setFormData] = useState({
    room_id: '',
    title: '',
    division: '',
    description: '',
    start_time: '',
    end_time: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const token = localStorage.getItem('token');
      
      await fetch('/api/v1/bookings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });
      
      // Show success message
      alert('✅ Booking berhasil dibuat sebagai Draft!');
      
      // Redirect ke booking list
      window.location.href = '/bookings';
      
    } catch (error) {
      console.error('Error creating booking:', error);
      alert('❌ Gagal membuat booking');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields */}
      <input
        type="text"
        placeholder="Judul Acara"
        value={formData.title}
        onChange={(e) => setFormData({...formData, title: e.target.value})}
        required
      />
      
      <textarea
        placeholder="Deskripsi"
        value={formData.description}
        onChange={(e) => setFormData({...formData, description: e.target.value})}
      />
      
      {/* Informasi Draft */}
      <div className="info-box">
        ℹ️ Booking akan disimpan sebagai Draft dan belum dikirim ke Telegram.
        <br />
        📢 Anda harus publish booking agar muncul di jadwal.
      </div>
      
      <button type="submit" className="btn-primary">
        💾 Simpan sebagai Draft
      </button>
    </form>
  );
};
```

---

## 4. Implement Publish Booking Function

### Fungsi Publish Booking

```jsx
// API service untuk publish booking
const bookingService = {
  publishBooking: async (bookingId) => {
    try {
      const token = localStorage.getItem('token');
      
      const response = await fetch(`/api/v1/bookings/${bookingId}/publish`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to publish booking');
      }
      
      return await response.json();
    } catch (error) {
      console.error('Error publishing booking:', error);
      throw error;
    }
  }
};

// Handler di component
const handlePublish = async (bookingId) => {
  if (!confirm('Apakah Anda yakin ingin publish booking ini?')) {
    return;
  }
  
  try {
    await bookingService.publishBooking(bookingId);
    
    // Show success message
    alert('✅ Booking berhasil dipublish!');
    
    // Refresh booking list
    window.location.reload();
    
  } catch (error) {
    console.error('Error publishing booking:', error);
    alert('❌ Gagal mempublish booking');
  }
};
```

---

## 5. Update User Display

### Handle Username Display

Backend sekarang menyimpan `username` di `UserSnapshot`. Tampilkan dengan format `@username` jika tersedia.

```jsx
const UserInfo = ({ userSnapshot }) => {
  // Format username dengan @ jika ada, fallback ke full_name
  const usernameDisplay = userSnapshot.username
    ? `@${userSnapshot.username}`
    : userSnapshot.full_name;
  
  const userDisplay = userSnapshot.username
    ? `${userSnapshot.full_name} (${userSnapshot.division || 'N/A'}) — @${userSnapshot.username}`
    : userSnapshot.full_name;

  return (
    <div className="user-info">
      <span className="user-name">{userDisplay}</span>
    </div>
  );
};

// Contoh penggunaan di booking card
const BookingCard = ({ booking }) => {
  return (
    <div className="booking-card">
      <h3>{booking.title}</h3>
      
      <div className="booking-details">
        <UserInfo userSnapshot={booking.user_snapshot} />
      </div>
    </div>
  );
};
```

---

## 6. Update Notification Messages

### Pesan Sukses yang Sesuai

#### A. Create Booking (Draft)
```javascript
// Success
alert('✅ Booking berhasil dibuat sebagai Draft!');

// Atau dengan modal
showModal({
  title: 'Booking Berhasil',
  message: 'Booking telah disimpan sebagai Draft. Booking akan muncul di jadwal setelah dipublish.',
  type: 'success',
  actions: [
    {
      label: 'Lihat Booking',
      onClick: () => navigate(`/bookings/${bookingId}`)
    },
    {
      label: 'Publish Sekarang',
      onClick: () => handlePublish(bookingId),
      primary: true
    }
  ]
});
```

#### B. Publish Booking
```javascript
// Success
alert('✅ Booking berhasil dipublish!');

// Atau dengan modal
showModal({
  title: 'Booking Published',
  message: 'Booking telah dipublish dan notifikasi telah dikirim ke Telegram grup.',
  type: 'success',
  actions: [
    {
      label: 'Lihat Jadwal',
      onClick: () => navigate('/rooms')
    }
  ]
});
```

#### C. Update Booking
```javascript
// Success
alert('✅ Booking berhasil diupdate!');

// Info tambahan
showModal({
  title: 'Booking Diupdate',
  message: 'Perubahan booking berhasil. Notifikasi telah dikirim ke Telegram grup.',
  type: 'success',
  actions: [
    {
      label: 'OK',
      onClick: () => closeModal()
    }
  ]
});
```

#### D. Cancel Booking
```javascript
// Success
alert('✅ Booking berhasil dibatalkan!');

// Info tambahan
showModal({
  title: 'Booking Dibatalkan',
  message: 'Booking telah dibatalkan. Notifikasi telah dikirim ke Telegram grup.',
  type: 'warning',
  actions: [
    {
      label: 'OK',
      onClick: () => closeModal()
    }
  ]
});
```

---

## 7. Styling Recommendations

### CSS untuk Status dan Tombol

```css
/* Status Badges */
.status-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 14px;
  text-align: center;
  margin-bottom: 12px;
}

.status-badge.draft {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
  color: white;
  box-shadow: 0 2px 4px rgba(255, 152, 0, 0.3);
}

.status-badge.published {
  background: linear-gradient(135deg, #4caf50 0%, #2e7d32 100%);
  color: white;
  box-shadow: 0 2px 4px rgba(76, 175, 80, 0.3);
}

/* Info Box */
.info-box {
  background-color: #e3f2fd;
  border-left: 4px solid #2196f3;
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 20px;
  color: #1565c0;
}

/* Buttons */
.btn-publish {
  background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
  color: white;
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(33, 150, 243, 0.3);
}

.btn-publish:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(33, 150, 243, 0.4);
}

.btn-edit {
  background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.btn-delete {
  background: linear-gradient(135deg, #f44336 0%, #d32f2f 100%);
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

.btn-cancel {
  background: linear-gradient(135deg, #ff5722 0%, #e64a19 100%);
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
}

/* Action Buttons Container */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}

/* Status Section */
.status-section {
  margin-bottom: 24px;
}

.status-info {
  margin-top: 8px;
  color: #666;
  font-size: 14px;
  padding: 8px;
  background-color: #fff3cd;
  border-radius: 4px;
}
```

---

## Summary Checklist

### Booking List
- [ ] Tampilkan status badge (Draft/Published)
- [ ] Tambah tombol "Publish" untuk draft bookings
- [ ] Implement filter berdasarkan status
- [ ] Handle conditional button display

### Booking Detail
- [ ] Tampilkan status dengan pesan informatif
- [ ] Tampilkan tombol berbeda (Publish/Edit/Delete vs Edit/Cancel)
- [ ] Tambah informasi state booking

### Create Form
- [ ] Update pesan sukses untuk draft
- [ ] Tambah informasi tentang draft workflow
- [ ] Redirect ke booking list setelah create

### Publish Function
- [ ] Implement API call untuk publish
- [ ] Tambah konfirmasi dialog
- [ ] Handle success/error states
- [ ] Refresh booking list setelah publish

### User Display
- [ ] Handle username dengan @ tag
- [ ] Fallback ke full_name jika tidak ada username
- [ ] Tampilkan division jika tersedia

### Notifications
- [ ] Update pesan create booking
- [ ] Update pesan publish booking
- [ ] Update pesan update booking
- [ ] Update pesan cancel booking

### Styling
- [ ] Implement CSS untuk status badges
- [ ] Styling untuk action buttons
- [ ] Responsive design untuk mobile

---

## Important Notes

### Backend Behavior
1. **Draft bookings TIDAK muncul** di jadwal ruangan
2. **Draft bookings bisa diedit** kapan saja
3. **Draft bookings bisa dihapus** tanpa notifikasi
4. **Hanya published bookings** yang kirim notifikasi ke Telegram
5. **Username otomatis terupdate** saat user login (tidak perlu perubahan di FE)
6. **Title dan description otomatis Capitalize (Title Case)** (backend handle)

### API Endpoints
- `POST /api/v1/bookings` - Create booking (draft)
- `POST /api/v1/bookings/{id}/publish` - Publish booking
- `PATCH /api/v1/bookings/{id}` - Update booking
- `DELETE /api/v1/bookings/{id}` - Cancel booking
- `GET /api/v1/bookings` - List bookings
- `GET /api/v1/rooms/{id}/schedule` - Room schedule (hanya published)

### Response Structure
```typescript
interface BookingResponse {
  _id: string;
  booking_number: string;
  title: string;
  division?: string;
  description?: string;
  start_time: string; // ISO datetime
  end_time: string; // ISO datetime
  status: 'active' | 'cancelled';
  published: boolean; // Field baru
  user_snapshot: {
    full_name: string;
    username?: string; // Field baru
    division?: string;
    telegram_id: number;
  };
  room_snapshot: {
    name: string;
  };
  created_at: string;
  updated_at: string;
}
```

---

## Testing Checklist

### Draft Workflow
- [ ] Create booking → status menjadi Draft
- [ ] Draft tidak muncul di jadwal ruangan
- [ ] Edit draft booking → berhasl
- [ ] Delete draft booking → berhasl

### Publish Workflow
- [ ] Publish draft booking → status Published
- [ ] Published muncul di jadwal ruangan
- [ ] Notifikasi dikirim ke Telegram
- [ ] Tombol Publish hilang setelah published

### Update/Cancel Workflow
- [ ] Update published booking → notifikasi dikirim
- [ ] Cancel published booking → notifikasi dikirim
- [ ] Username tampil dengan @ tag
- [ ] Title dan description dalam Capitalize (Title Case)

---

## Contact

Untuk pertanyaan atau masalah terkait implementasi ini:
- Backend: Check API documentation di `/docs`
- Issues: Report via GitHub issues

---

**Versi Dokumen:** 1.0  
**Tanggal:** 21 Februari 2026  
**Status:** Ready for Implementation
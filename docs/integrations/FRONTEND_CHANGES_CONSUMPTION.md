# Perubahan Frontend - Fitur Konsumsi

## 📋 Ringkasan

Dokumentasi ini berisi perubahan yang perlu dilakukan di Frontend untuk mendukung fitur konsumsi yang baru diimplementasikan di Backend.

---

## 🎯 Perubahan Utama

### 1. **Form Booking**
- Tambah checkbox "Tambah Konsumsi"
- Tambah textarea untuk catatan konsumsi
- Tambah pilihan grup konsumsi & verifikasi (opsional, override default)

### 2. **Booking Response**
- Handle field baru di response
- Tampilkan info konsumsi di UI

### 3. **Admin Panel**
- Tambah UI untuk manage setting grup default
- Get/Update default group IDs

---

## 📝 Perubahan Detail

### 1. Form Booking (`/booking/create` atau `/booking/edit`)

#### 1.1 Tambah Field Konsumsi

```tsx
// Example: BookingForm.tsx

interface BookingFormData {
  room_id: string;
  telegram_group_id: number;
  title: string;
  division?: string;
  description?: string;
  start_time: string;  // ISO format
  end_time: string;    // ISO format
  // FIELD BARU:
  has_consumption: boolean;
  consumption_note?: string;
  consumption_group_id?: number;      // Optional, default dari setting
  verification_group_id?: number;    // Optional, default dari setting
}

const [formData, setFormData] = useState<BookingFormData>({
  room_id: '',
  telegram_group_id: 0,
  title: '',
  division: '',
  description: '',
  start_time: '',
  end_time: '',
  // FIELD BARU:
  has_consumption: false,
  consumption_note: '',
  consumption_group_id: undefined,
  verification_group_id: undefined
});
```

#### 1.2 Tambah UI Elements

```tsx
{/* Checkbox Tambah Konsumsi */}
<div className="form-group">
  <label className="checkbox-label">
    <input
      type="checkbox"
      checked={formData.has_consumption}
      onChange={(e) => setFormData({
        ...formData,
        has_consumption: e.target.checked
      })}
    />
    <span>Tambah Konsumsi *Untuk Tamu</span>
  </label>
</div>

{/* Field yang hanya muncul jika has_consumption = true */}
{formData.has_consumption && (
  <>
    {/* Textarea Catatan Konsumsi */}
    <div className="form-group">
      <label htmlFor="consumption_note">
        Catatan Konsumsi
      </label>
      <textarea
        id="consumption_note"
        value={formData.consumption_note || ''}
        onChange={(e) => setFormData({
          ...formData,
          consumption_note: e.target.value
        })}
        placeholder="Mohon disediakan..."
        rows={4}
      />
    </div>

    {/* Pilihan Grup Konsumsi (Opsional) */}
    <div className="form-group">
      <label htmlFor="consumption_group_id">
        Grup Konsumsi (Opsional)
      </label>
      <select
        id="consumption_group_id"
        value={formData.consumption_group_id || ''}
        onChange={(e) => setFormData({
          ...formData,
          consumption_group_id: e.target.value ? parseInt(e.target.value) : undefined
        })}
      >
        <option value="">Default dari Setting</option>
        {telegramGroups.map(group => (
          <option key={group.group_id} value={group.group_id}>
            {group.group_name}
          </option>
        ))}
      </select>
      <small className="form-text">
        Biarkan kosong untuk menggunakan grup default dari setting
      </small>
    </div>
  </>
)}

{/* Pilihan Grup Verifikasi (Opsional - Selalu tersedia) */}
<div className="form-group">
  <label htmlFor="verification_group_id">
    Grup Verifikasi (Opsional)
  </label>
  <select
    id="verification_group_id"
    value={formData.verification_group_id || ''}
    onChange={(e) => setFormData({
      ...formData,
      verification_group_id: e.target.value ? parseInt(e.target.value) : undefined
    })}
  >
    <option value="">Default dari Setting</option>
    {telegramGroups.map(group => (
      <option key={group.group_id} value={group.group_id}>
        {group.group_name}
      </option>
    ))}
  </select>
  <small className="form-text">
    Biarkan kosong untuk menggunakan grup default dari setting
  </small>
</div>
```

#### 1.3 Update API Call

```typescript
// Example: api/booking.ts

export const createBooking = async (data: BookingFormData): Promise<Booking> => {
  const response = await fetch('/api/v1/bookings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Gagal membuat booking');
  }
  
  return response.json();
};

// Usage:
try {
  const booking = await createBooking(formData);
  // Success!
} catch (error) {
  // Handle error
  alert(error.message);
}
```

---

### 2. Booking Response Interface

#### 2.1 Update TypeScript Interface

```typescript
// types/booking.ts

export interface Booking {
  id: string;
  booking_number: string;
  user_id: string;
  user_snapshot: {
    full_name: string;
    username?: string;
    division?: string;
    telegram_id: number;
  };
  room_id: string;
  room_snapshot: {
    name: string;
  };
  telegram_group_id: number;
  title: string;
  division?: string;
  description?: string;
  start_time: string;
  end_time: string;
  status: 'active' | 'cancelled';
  published: boolean;
  cancelled_at?: string;
  cancelled_by?: string;
  // FIELD BARU:
  has_consumption: boolean;
  consumption_note?: string;
  consumption_group_id?: number;
  verification_group_id?: number;
  hrd_notified: boolean;
  created_at: string;
  updated_at: string;
}
```

#### 2.2 Tampilkan Info Konsumsi di UI

```tsx
// Example: BookingCard.tsx atau BookingDetail.tsx

interface BookingCardProps {
  booking: Booking;
}

export const BookingCard: React.FC<BookingCardProps> = ({ booking }) => {
  return (
    <div className="booking-card">
      {/* Info booking yang sudah ada */}
      <h3>{booking.title}</h3>
      <p>Ruang: {booking.room_snapshot.name}</p>
      <p>Waktu: {formatDate(booking.start_time)}</p>
      <p>PIC: {booking.user_snapshot.full_name}</p>
      
      {/* INFO KONSUMSI BARU */}
      {booking.has_consumption && (
        <div className="consumption-info">
          <h4>🍽️ Konsumsi</h4>
          <p>{booking.consumption_note || '-'}</p>
          {booking.consumption_group_id && (
            <small>Grup Konsumsi: {booking.consumption_group_id}</small>
          )}
        </div>
      )}
      
      {/* Info lain yang sudah ada */}
      <p>Status: {booking.status}</p>
      <p>Published: {booking.published ? 'Yes' : 'No'}</p>
    </div>
  );
};
```

---

### 3. Admin Panel - Setting Grup Default

#### 3.1 Buat Halaman/Modal Setting Grup

```tsx
// Example: AdminSettings.tsx atau components/GroupSettings.tsx

import React, { useState, useEffect } from 'react';

interface GroupSettings {
  default_consumption_group_id: number | null;
  default_verification_group_id: number | null;
}

export const GroupSettings: React.FC = () => {
  const [settings, setSettings] = useState<GroupSettings>({
    default_consumption_group_id: null,
    default_verification_group_id: null
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Fetch settings on mount
  useEffect(() => {
    fetchGroupSettings();
  }, []);
  
  const fetchGroupSettings = async () => {
    try {
      const response = await fetch('/api/v1/admin/settings/group-ids', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (err) {
      console.error('Failed to fetch group settings:', err);
    }
  };
  
  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/v1/admin/settings/group-ids', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(settings)
      });
      
      if (response.ok) {
        alert('Setting berhasil disimpan!');
      } else {
        const error = await response.json();
        setError(error.detail || 'Gagal menyimpan setting');
      }
    } catch (err) {
      setError('Gagal menyimpan setting');
    } finally {
      setLoading(false);
    }
  };
  
  // Mock telegram groups (seharusnya dari API /api/v1/telegram-groups)
  const telegramGroups = [
    { group_id: -1001111111111, group_name: 'Grup Konsumsi' },
    { group_id: -1002222222222, group_name: 'Grup Verifikasi' }
  ];
  
  return (
    <div className="group-settings">
      <h2>Setting Grup Default</h2>
      
      {error && (
        <div className="alert alert-danger">{error}</div>
      )}
      
      <form onSubmit={handleSave}>
        {/* Grup Konsumsi Default */}
        <div className="form-group">
          <label htmlFor="consumption_group">
            Grup Konsumsi Default
          </label>
          <select
            id="consumption_group"
            value={settings.default_consumption_group_id || ''}
            onChange={(e) => setSettings({
              ...settings,
              default_consumption_group_id: e.target.value ? parseInt(e.target.value) : null
            })}
          >
            <option value="">Belum di-set</option>
            {telegramGroups.map(group => (
              <option key={group.group_id} value={group.group_id}>
                {group.group_name}
              </option>
            ))}
          </select>
          <small className="form-text">
            Grup ini akan menerima notifikasi konsumsi secara default jika user tidak memilih grup konsumsi secara manual
          </small>
        </div>
        
        {/* Grup Verifikasi Default */}
        <div className="form-group">
          <label htmlFor="verification_group">
            Grup Verifikasi Default
          </label>
          <select
            id="verification_group"
            value={settings.default_verification_group_id || ''}
            onChange={(e) => setSettings({
              ...settings,
              default_verification_group_id: e.target.value ? parseInt(e.target.value) : null
            })}
          >
            <option value="">Belum di-set</option>
            {telegramGroups.map(group => (
              <option key={group.group_id} value={group.group_id}>
                {group.group_name}
              </option>
            ))}
          </select>
          <small className="form-text">
            Grup ini akan menerima notifikasi verifikasi dan perapian ruangan secara default
          </small>
        </div>
        
        <button type="submit" disabled={loading}>
          {loading ? 'Menyimpan...' : 'Simpan Setting'}
        </button>
      </form>
    </div>
  );
};
```

#### 3.2 Integrasi di Admin Dashboard

```tsx
// Example: AdminDashboard.tsx

import { GroupSettings } from './components/GroupSettings';

export const AdminDashboard: React.FC = () => {
  return (
    <div className="admin-dashboard">
      {/* Tab navigation */}
      <div className="tabs">
        <button className="tab active">Dashboard</button>
        <button className="tab">Users</button>
        <button className="tab">Rooms</button>
        <button className="tab">Bookings</button>
        <button className="tab">Settings</button>
      </div>
      
      {/* Tab content */}
      <div className="tab-content">
        {/* Settings tab */}
        <div className="tab-pane active">
          <h2>Application Settings</h2>
          <GroupSettings />
        </div>
      </div>
    </div>
  );
};
```

---

### 4. API Calls - Utility Functions

#### 4.1 Get Group Settings (Admin)

```typescript
// api/settings.ts

export interface GroupSettings {
  default_consumption_group_id: number | null;
  default_verification_group_id: number | null;
}

export const getGroupSettings = async (): Promise<GroupSettings> => {
  const response = await fetch('/api/v1/admin/settings/group-ids', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    throw new Error('Gagal mengambil setting grup');
  }
  
  return response.json();
};

export const updateGroupSettings = async (settings: GroupSettings): Promise<GroupSettings> => {
  const response = await fetch('/api/v1/admin/settings/group-ids', {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(settings)
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Gagal update setting grup');
  }
  
  return response.json();
};
```

---

## 🎨 UI/UX Recommendations

### 1. Form Layout

```
┌─────────────────────────────────────┐
│ Form Booking                       │
├─────────────────────────────────────┤
│ Ruangan: [Dropdown]              │
│ Judul: [Input]                    │
│ Deskripsi: [Textarea]              │
│ Waktu: [Start] - [End]           │
│ Grup: [Dropdown]                  │
├─────────────────────────────────────┤
│ ☑ Tambah Konsumsi *Untuk Tamu   │
│   (jika dicentang, munculkan:)    │
│   ┌─────────────────────────────┐   │
│   │ Catatan Konsumsi:         │   │
│   │ [Textarea]                │   │
│   │                          │   │
│   │ Grup Konsumsi: [Select]  │   │
│   └─────────────────────────────┘   │
├─────────────────────────────────────┤
│ Grup Verifikasi: [Select]           │
│ (Opsional, default dari setting)     │
├─────────────────────────────────────┤
│ [Cancel] [Submit]                 │
└─────────────────────────────────────┘
```

### 2. Color Coding untuk Konsumsi

```css
/* styles.css */
.consumption-info {
  background-color: #fff3cd;
  border-left: 4px solid #ffc107;
  padding: 12px;
  margin: 12px 0;
  border-radius: 4px;
}

.consumption-info h4 {
  color: #856404;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  cursor: pointer;
}
```

### 3. Feedback UX

```tsx
// Show loading state saat menyimpan setting
{loading && <div className="loading">Menyimpan setting...</div>}

// Show success message
{showSuccess && (
  <div className="alert alert-success">
    Setting berhasil disimpan!
  </div>
)}

// Show validation error
{error && (
  <div className="alert alert-danger">
    {error}
  </div>
)}
```

---

## 🧪 Testing Checklist

### 1. Form Booking
- [ ] Checkbox "Tambah Konsumsi" berfungsi
- [ ] Textarea konsumsi muncul hanya jika checkbox dicentang
- [ ] Textarea bersifat optional
- [ ] Pilihan grup konsumsi/verifikasi bisa dipilih atau dikosongkan
- [ ] Form submit berhasil dengan field baru
- [ ] Error handling berfungsi

### 2. Booking Display
- [ ] Info konsumsi ditampilkan di booking card
- [ ] Info konsumsi hanya muncul jika `has_consumption = true`
- [ ] Tampilan rapi dan mudah dibaca

### 3. Admin Settings
- [ ] Halaman setting grup default bisa diakses
- [ ] Data setting berhasil di-load
- [ ] Setting bisa di-update
- [ ] Success message ditampilkan setelah save
- [ ] Error handling berfungsi

### 4. Integration
- [ ] Booking dengan konsumsi berhasil dibuat
- [ ] Notifikasi terkirim ke grup yang benar
- [ ] Default group setting berfungsi

---

## 📦 File yang Perlu Diubah

### Core Files
- `types/booking.ts` - Update interface Booking
- `api/booking.ts` - Update create booking API call
- `components/BookingForm.tsx` - Tambah field konsumsi
- `components/BookingCard.tsx` - Tampilkan info konsumsi

### Admin Files
- `api/settings.ts` - Tambah API calls untuk group settings (baru)
- `components/GroupSettings.tsx` - Komponen setting grup (baru)
- `pages/AdminDashboard.tsx` - Integrasi setting grup

### Utility Files
- `utils/formatDate.ts` - Pastikan format tanggal sesuai
- `utils/api.ts` - Pastikan token handling benar

---

## 🔍 Common Issues & Solutions

### Issue 1: Field Konsumsi Tidak Tersimpan
**Solution**: Pastikan semua field baru dikirim di request body:
```typescript
const data = {
  ...existingFields,
  has_consumption: true,
  consumption_note: '...',
  // consumption_group_id & verification_group_id optional
};
```

### Issue 2: Type Error pada Booking Response
**Solution**: Update TypeScript interface dengan semua field baru:
```typescript
export interface Booking {
  // ...existing fields
  has_consumption: boolean;
  consumption_note?: string;
  consumption_group_id?: number;
  verification_group_id?: number;
  hrd_notified: boolean;
}
```

### Issue 3: Setting Grup Tidak Berfungsi
**Solution**: Pastikan API call menggunakan method PUT dan header yang benar:
```typescript
const response = await fetch('/api/v1/admin/settings/group-ids', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(settings)
});
```

---

## 📚 Additional Resources

### Backend Documentation
- Lihat `CONSUMPTION_FEATURE_DOCUMENTATION.md` untuk detail API
- Test API via Swagger: `http://localhost:8000/docs`

### API Endpoints
- `POST /api/v1/bookings` - Create booking dengan konsumsi
- `GET /api/v1/admin/settings/group-ids` - Get grup default
- `PUT /api/v1/admin/settings/group-ids` - Update grup default

---

## ✅ Summary of Changes

| Component | Changes | Priority |
|-----------|----------|-----------|
| BookingForm | Tambah checkbox, textarea, select grup | HIGH |
| Booking Types | Update interface dengan field konsumsi | HIGH |
| BookingCard | Tampilkan info konsumsi | MEDIUM |
| Admin Dashboard | Tambah tab/settings untuk grup | MEDIUM |
| API Services | Update calls & add new endpoints | HIGH |
| Styling | Tambah styles untuk konsumsi | LOW |

---

## 🚀 Next Steps

1. Update TypeScript interfaces untuk Booking
2. Modify booking form dengan field konsumsi
3. Test booking creation dengan konsumsi
4. Create admin settings page untuk grup default
5. Test all API endpoints
6. Deploy dan test secara end-to-end

Good luck! 🎉
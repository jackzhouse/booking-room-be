# Room Management API Documentation

Complete API documentation for room management endpoints. All endpoints require authentication.

## Base URL
```
https://booking-room-be.onrender.com/api/v1
```

## Authentication
All endpoints require `Authorization: Bearer {token}` header where `token` is the JWT token from authentication.

---

## Public Endpoints (All Authenticated Users)

### 1. List All Rooms

**Endpoint:** `GET /rooms`

**Query Parameters:**
- `active_only` (boolean, optional, default: `true`) - Filter only active rooms

**Request:**
```bash
curl -X GET "https://booking-room-be.onrender.com/api/v1/rooms?active_only=true" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "id": "507f1f77bcf86cd799439011",
    "name": "Ruang Meeting",
    "capacity": 10,
    "facilities": ["AC", "WiFi", "Projector", "Whiteboard"],
    "location": "Lantai 2",
    "is_active": true,
    "created_at": "2026-02-20T00:00:00.000Z"
  },
  {
    "id": "507f1f77bcf86cd799439012",
    "name": "Ruang Emphaty",
    "capacity": 6,
    "facilities": ["AC", "WiFi", "Whiteboard"],
    "location": "Lantai 1",
    "is_active": true,
    "created_at": "2026-02-20T00:00:00.000Z"
  }
]
```

---

### 2. Get Room Details

**Endpoint:** `GET /rooms/{room_id}`

**Request:**
```bash
curl -X GET "https://booking-room-be.onrender.com/api/v1/rooms/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Ruang Meeting",
  "capacity": 10,
  "facilities": ["AC", "WiFi", "Projector", "Whiteboard"],
  "location": "Lantai 2",
  "is_active": true,
  "created_at": "2026-02-20T00:00:00.000Z"
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Room not found"
}
```

---

### 3. Get Room Schedule

**Endpoint:** `GET /rooms/{room_id}/schedule`

**Query Parameters:**
- `start_date` (date, required) - Start date in YYYY-MM-DD format
- `end_date` (date, optional) - End date in YYYY-MM-DD format (defaults to start_date)

**Request:**
```bash
curl -X GET "https://booking-room-be.onrender.com/api/v1/rooms/507f1f77bcf86cd799439011/schedule?start_date=2026-02-20&end_date=2026-02-20" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response (200 OK):**
```json
[
  {
    "id": "507f1f77bcf86cd799439123",
    "booking_number": "BK-2026-02-20-001",
    "title": "Weekly Team Meeting",
    "user_name": "Joko Makruf",
    "division": "IT",
    "start_time": "2026-02-20T09:00:00",
    "end_time": "2026-02-20T10:00:00"
  }
]
```

---

## Admin Endpoints (Admin Only)

### 4. Create New Room

**Endpoint:** `POST /rooms`

**Request Body:**
```json
{
  "name": "Ruang Diskusi",
  "capacity": 4,
  "facilities": ["AC", "WiFi", "Whiteboard"],
  "location": "Lantai 1",
  "is_active": true
}
```

**Request:**
```bash
curl -X POST "https://booking-room-be.onrender.com/api/v1/rooms" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruang Diskusi",
    "capacity": 4,
    "facilities": ["AC", "WiFi", "Whiteboard"],
    "location": "Lantai 1",
    "is_active": true
  }'
```

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439013",
  "name": "Ruang Diskusi",
  "capacity": 4,
  "facilities": ["AC", "WiFi", "Whiteboard"],
  "location": "Lantai 1",
  "is_active": true,
  "created_at": "2026-02-20T00:00:00.000Z"
}
```

---

### 5. Update Room

**Endpoint:** `PATCH /rooms/{room_id}`

**Request Body (partial update supported):**
```json
{
  "name": "Ruang Meeting 1 (Updated)",
  "capacity": 12
}
```

**Request:**
```bash
curl -X PATCH "https://booking-room-be.onrender.com/api/v1/rooms/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruang Meeting 1 (Updated)",
    "capacity": 12
  }'
```

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Ruang Meeting 1 (Updated)",
  "capacity": 12,
  "facilities": ["AC", "WiFi", "Projector", "Whiteboard"],
  "location": "Lantai 2",
  "is_active": true,
  "created_at": "2026-02-20T00:00:00.000Z"
}
```

---

### 6. Toggle Room Status

**Endpoint:** `PATCH /rooms/{room_id}/toggle`

**Description:** Toggle room's active status (active ↔ inactive)

**Request:**
```bash
curl -X PATCH "https://booking-room-be.onrender.com/api/v1/rooms/507f1f77bcf86cd799439011/toggle" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Ruang Meeting",
  "is_active": false
}
```

---

### 7. Delete Room

**Endpoint:** `DELETE /rooms/{room_id}`

**Description:** Delete a room and cancel all its active bookings

**Request:**
```bash
curl -X DELETE "https://booking-room-be.onrender.com/api/v1/rooms/507f1f77bcf86cd799439011" \
  -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN"
```

**Response (200 OK):**
```json
{
  "message": "Room 'Ruang Meeting' deleted successfully",
  "cancelled_bookings": 3
}
```

**Note:** When a room is deleted, all active bookings for that room are automatically cancelled.

---

## Sample Rooms Data

### Default Rooms Created by Script

1. **Ruang Meeting**
   - Capacity: 10 people
   - Facilities: AC, WiFi, Projector, Whiteboard
   - Location: Lantai 2

2. **Ruang Emphaty**
   - Capacity: 6 people
   - Facilities: AC, WiFi, Whiteboard
   - Location: Lantai 1

3. **Ruang Mushola**
   - Capacity: 30 people
   - Facilities: AC, Speaker, Karpet
   - Location: Lantai 3

---

## Frontend Integration Guide

### React Example

```javascript
// Get all rooms
const getRooms = async () => {
  const response = await fetch(
    'https://booking-room-be.onrender.com/api/v1/rooms',
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  const rooms = await response.json();
  return rooms;
};

// Create new room (admin only)
const createRoom = async (roomData) => {
  const response = await fetch(
    'https://booking-room-be.onrender.com/api/v1/rooms',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(roomData)
    }
  );
  const room = await response.json();
  return room;
};

// Update room (admin only)
const updateRoom = async (roomId, roomData) => {
  const response = await fetch(
    `https://booking-room-be.onrender.com/api/v1/rooms/${roomId}`,
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(roomData)
    }
  );
  const room = await response.json();
  return room;
};

// Delete room (admin only)
const deleteRoom = async (roomId) => {
  const response = await fetch(
    `https://booking-room-be.onrender.com/api/v1/rooms/${roomId}`,
    {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${adminToken}`
      }
    }
  );
  const result = await response.json();
  return result;
};
```

---

## Error Codes

| Status Code | Description |
|-------------|-------------|
| 200 | Success |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Admin access required |
| 404 | Not found - Room does not exist |
| 422 | Validation error - Invalid request data |

---

## Database Setup

To populate your database with sample rooms, run:

```bash
python create_sample_rooms.py
```

This will create:
- Ruang Meeting (10 people)
- Ruang Emphaty (6 people)
- Ruang Mushola (30 people)

The script is safe to run multiple times - it will skip rooms that already exist.
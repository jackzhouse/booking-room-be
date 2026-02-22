# Non-Admin Endpoints Documentation

## Overview

This document describes updated endpoints that now support non-admin users in viewing schedules and telegram groups for booking purposes.

## Updated Endpoints

### 1. GET /bookings

View all published bookings across all rooms (with optional filters).

**Access Level:** All authenticated users (non-admin read-only)

**Purpose:** Allow users to see the schedule before making a booking

**Note:** To view only your own bookings, use `GET /bookings/my` instead.

**Query Parameters:**
- `room_id` (optional, string): Filter by specific room ID
- `start_date` (optional, date): Start date filter (YYYY-MM-DD format)
- `end_date` (optional, date): End date filter (YYYY-MM-DD format)

**Behavior:**
- Only returns published and active bookings
- Excludes draft and cancelled bookings
- Shows user name and division information
- If end_date is not provided, it defaults to start_date
- If no date filters are provided, returns all published bookings

**Example Requests:**

```bash
# Get all published bookings
GET /api/v1/bookings

# Get bookings for today
GET /api/v1/bookings?start_date=2026-02-22

# Get bookings for a specific room
GET /api/v1/bookings?room_id=507f1f77bcf86cd799439011

# Get bookings for a date range
GET /api/v1/bookings?start_date=2026-02-20&end_date=2026-02-25

# Get bookings for a specific room today
GET /api/v1/bookings?room_id=507f1f77bcf86cd799439011&start_date=2026-02-22

# Get only your own bookings
GET /api/v1/bookings/my
```

**Response Format:**

```json
[
  {
    "_id": "507f1f77bcf86cd799439011",
    "booking_number": "BK-00001",
    "user_id": "507f1f77bcf86cd799439012",
    "user_snapshot": {
      "full_name": "John Doe",
      "username": "johndoe",
      "division": "Engineering",
      "telegram_id": 123456789
    },
    "room_id": "507f1f77bcf86cd799439013",
    "room_snapshot": {
      "name": "Meeting Room A"
    },
    "telegram_group_id": -1001234567890,
    "title": "Team Standup",
    "division": "Engineering",
    "description": "Daily standup meeting",
    "start_time": "2026-02-22T09:00:00+07:00",
    "end_time": "2026-02-22T09:30:00+07:00",
    "status": "active",
    "published": true,
    "cancelled_at": null,
    "cancelled_by": null,
    "created_at": "2026-02-22T08:00:00+07:00",
    "updated_at": "2026-02-22T08:00:00+07:00"
  }
]
```

**Use Cases:**
1. User wants to see all bookings for a specific day before making a booking
2. User wants to check availability of a specific room
3. User wants to see what rooms are booked in a date range
4. Frontend displays schedule/calendar view

---

### 2. GET /telegram-groups

Get all active Telegram groups.

**Access Level:** All authenticated users (non-admin read-only)

**Purpose:** Allow users to see available telegram groups when creating bookings

**Query Parameters:** None

**Behavior:**
- Returns all active telegram groups
- Shows group ID and name
- Required for selecting notification target when creating bookings

**Example Request:**

```bash
# Get all telegram groups
GET /api/v1/telegram-groups
```

**Response Format:**

```json
{
  "groups": [
    {
      "_id": "507f1f77bcf86cd799439020",
      "group_id": -1001234567890,
      "group_name": "Engineering Team",
      "created_at": "2026-02-20T10:00:00+07:00"
    },
    {
      "_id": "507f1f77bcf86cd799439021",
      "group_id": -1009876543210,
      "group_name": "Marketing Team",
      "created_at": "2026-02-21T14:30:00+07:00"
    }
  ],
  "total": 2
}
```

**Use Cases:**
1. User selects which group to notify when creating a booking
2. Frontend displays dropdown of available groups in booking form

---

## Comparison with Existing Endpoints

### Bookings Endpoints

| Endpoint | Access | Returns | Purpose |
|----------|--------|---------|---------|
| `GET /bookings` | **All authenticated users** | All published bookings | **View schedule (UPDATED)** |
| `GET /bookings/my` | Current user only | User's own bookings | View personal bookings |
| `GET /bookings/{id}` | Owner or admin | Specific booking | View booking details |
| `POST /bookings` | All authenticated users | New booking | Create booking |
| `PUT /bookings/{id}` | Owner or admin | Updated booking | Update booking |
| `DELETE /bookings/{id}` | Owner or admin | Cancelled booking | Cancel booking |

### Telegram Groups Endpoints

| Endpoint | Access | Returns | Purpose |
|----------|--------|---------|---------|
| `GET /telegram-groups` | **All authenticated users** | All groups | **Select group for booking (UPDATED)** |
| `POST /telegram-groups` | Admin only | New group | Add group |
| `DELETE /telegram-groups/{id}` | Admin only | None | Delete group |
| `POST /telegram-groups/{id}/verify` | Admin only | Group info | Verify bot access |
| `POST /telegram-groups/{id}/test` | Admin only | Success message | Test notification |

---

## Security Considerations

1. **Read-Only Access:** Non-admin users can only view data, not modify it
2. **Published Bookings Only:** Only shows published bookings to avoid exposing draft/unpublished bookings
3. **No Sensitive Data:** Shows only necessary information (user name, division, not personal contact details)
4. **Authentication Required:** All endpoints require valid authentication token

---

## API Response Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid parameter format
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Not authorized (admin-only endpoints)
- `404 Not Found`: Resource not found

---

## Testing

Run the test script to verify functionality:

```bash
python test_non_admin_endpoints.py
```

This will:
1. Test fetching all published bookings
2. Test fetching telegram groups
3. Test room filter functionality

---

## Migration Notes

### For Frontend Developers

1. **Booking Creation Flow:**
   - Fetch available rooms: `GET /rooms`
   - Fetch telegram groups: `GET /telegram-groups` (now accessible by all users)
   - Fetch schedule: `GET /bookings?room_id={room_id}&start_date={date}` (simplified)
   - Create booking: `POST /bookings` with selected group_id

2. **Schedule Display:**
   - Use `GET /bookings` to show all published bookings
   - Use query parameters to filter by room and date
   - Display user name and division for transparency
   - Use `GET /bookings/my` to show only user's own bookings

3. **Backward Compatibility:**
   - Endpoints modified in place (no new endpoints created)
   - `/bookings/my` added for viewing own bookings
   - Response formats remain the same

---

## Implementation Details

### Files Modified:

1. **app/api/v1/bookings.py**
   - Modified `GET /bookings` to show all published bookings with filters
   - Added imports: `datetime`, `date`, `Query`
   - Implemented filtering logic for room and date
   - Changed `GET /bookings/my` to show only user's own bookings

2. **app/api/v1/telegram_groups.py**
   - Modified `GET /telegram-groups` to be accessible by all authenticated users
   - Changed dependency from `get_current_admin_user` to `get_current_active_user`
   - Removed redundant `/list` endpoint

### Database Queries:

The updated endpoints use the following query patterns:

**Bookings:**
```python
query = {
    "status": "active",
    "published": True
}
# Optional filters:
# "room_id": ObjectId(room_id)
# "start_time": {"$gte": start_datetime, "$lte": end_datetime}
```

**Telegram Groups:**
```python
# No filter - returns all active groups
```

---

## Future Enhancements

Potential improvements for future versions:

1. **Pagination:** Add pagination for large result sets
2. **Search:** Add search functionality for booking titles
3. **User Filter:** Allow filtering by user (for team leads)
4. **Export:** Add CSV/PDF export for schedule
5. **Recurring Bookings:** Support for recurring booking patterns
6. **Availability Slots:** Endpoint to get available time slots directly

---

## Support

For issues or questions:
1. Check this documentation first
2. Review API test results
3. Contact backend development team
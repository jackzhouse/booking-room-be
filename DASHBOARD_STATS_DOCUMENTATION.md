# Dashboard Statistics API Documentation

## Overview

New dashboard statistics endpoint has been added to provide comprehensive statistics for the admin dashboard.

## Endpoint

**GET** `/api/v1/admin/dashboard/stats`

### Description

Retrieves dashboard statistics including booking counts, room counts, and user counts. This endpoint is designed to provide all necessary data for the admin dashboard in a single API call.

### Authentication

**Required**: Admin user authentication via JWT token

Only users with `is_admin: true` can access this endpoint.

### Request Headers

```
Authorization: Bearer {access_token}
Content-Type: application/json
```

### Request Parameters

None (no query parameters or request body required)

### Response

**Status Code**: `200 OK`

**Response Body**:

```json
{
  "bookings_today": 15,
  "bookings_this_week": 87,
  "active_bookings_today": 12,
  "active_bookings_this_week": 75,
  "total_rooms": 5,
  "active_rooms": 4,
  "total_users": 42,
  "active_users": 40
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `bookings_today` | integer | Total bookings scheduled for today (all statuses: active + cancelled) |
| `bookings_this_week` | integer | Total bookings scheduled for this week (all statuses) |
| `active_bookings_today` | integer | Active (non-cancelled) bookings scheduled for today |
| `active_bookings_this_week` | integer | Active (non-cancelled) bookings scheduled for this week |
| `total_rooms` | integer | Total number of rooms in the system (active + inactive) |
| `active_rooms` | integer | Number of active rooms |
| `total_users` | integer | Total number of registered users (active + inactive) |
| `active_users` | integer | Number of active users |

### Timezone

All date/time calculations are performed using the configured timezone (`Asia/Jakarta`, UTC+7).

- **Today**: From 00:00:00 to 23:59:59 of the current day
- **This Week**: From Monday 00:00:00 to Sunday 23:59:59 of the current week

### Error Responses

#### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

#### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

## Example Usage

### cURL

```bash
curl -X GET "http://localhost:8000/api/v1/admin/dashboard/stats" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

### JavaScript/Fetch

```javascript
const response = await fetch('http://localhost:8000/api/v1/admin/dashboard/stats', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  }
});

const stats = await response.json();
console.log('Today\'s bookings:', stats.bookings_today);
console.log('Active users:', stats.active_users);
```

### React Example

```jsx
import { useEffect, useState } from 'react';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/v1/admin/dashboard/stats', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (!response.ok) {
          throw new Error('Failed to fetch dashboard stats');
        }
        
        const data = await response.json();
        setStats(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="dashboard">
      <div className="stat-card">
        <h3>Total Booking Hari Ini</h3>
        <p className="stat-value">{stats.bookings_today}</p>
      </div>
      
      <div className="stat-card">
        <h3>Booking Minggu Ini</h3>
        <p className="stat-value">{stats.bookings_this_week}</p>
      </div>
      
      <div className="stat-card">
        <h3>Total Ruangan</h3>
        <p className="stat-value">{stats.total_rooms}</p>
      </div>
      
      <div className="stat-card">
        <h3>Total User</h3>
        <p className="stat-value">{stats.total_users}</p>
      </div>
    </div>
  );
}
```

## Implementation Details

### Files Created/Modified

1. **New File**: `app/schemas/dashboard.py`
   - Defines `DashboardStats` schema for API response

2. **New File**: `app/services/dashboard_service.py`
   - Implements `get_dashboard_statistics()` function
   - Handles timezone-aware date calculations
   - Performs optimized database queries

3. **Modified File**: `app/api/v1/admin.py`
   - Added new endpoint `GET /admin/dashboard/stats`
   - Integrated dashboard service
   - Applied admin-only authentication

### Database Queries

The endpoint performs the following optimized queries:

1. Count bookings by date range (today/this week)
2. Count active bookings by date range
3. Count total rooms and active rooms
4. Count total users and active users

All queries leverage existing MongoDB indexes for optimal performance.

### Performance Considerations

- Single endpoint call reduces network overhead
- Database queries are optimized with proper indexing
- No complex aggregations needed - simple count queries
- Response size is minimal (~200 bytes)

## Testing

A test script `test_dashboard_stats.py` has been provided to verify the implementation:

```bash
python3 test_dashboard_stats.py
```

This test script will:
- Connect to the database
- Initialize Beanie models
- Fetch dashboard statistics
- Display results with integrity checks

## Future Enhancements

Potential future additions to the dashboard statistics:

- Monthly/yearly booking trends
- Most popular rooms
- User activity metrics
- Cancellation rate statistics
- Peak hours analysis
- Division-wise booking breakdown
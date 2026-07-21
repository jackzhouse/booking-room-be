# Frontend Changes - Dynamic Telegram Groups

## Overview

Backend now supports multiple Telegram groups. When creating a booking, users must select which Telegram group to send notifications to. This document outlines the required frontend changes.

---

## API Changes

### 1. New Endpoints (Admin Only)

#### Get All Telegram Groups
```
GET /api/v1/telegram-groups
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "groups": [
    {
      "id": "507f1f77bcf86cd799439011",
      "group_id": -1001234567890,
      "group_name": "General Announcement",
      "is_active": true,
      "created_at": "2025-02-21T14:00:00Z",
      "updated_at": "2025-02-21T14:00:00Z"
    },
    {
      "id": "507f1f77bcf86cd799439012",
      "group_id": -1009876543210,
      "group_name": "Engineering Team",
      "is_active": true,
      "created_at": "2025-02-21T14:30:00Z",
      "updated_at": "2025-02-21T14:30:00Z"
    }
  ],
  "total": 2
}
```

#### Add Telegram Group (Admin Only)
```
POST /api/v1/telegram-groups
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "group_id": -1001234567890,
  "group_name": "Marketing Team"
}
```

**Response:**
```json
{
  "id": "507f1f77bcf86cd799439013",
  "group_id": -1001234567890,
  "group_name": "Marketing Team",
  "is_active": true,
  "created_at": "2025-02-21T15:00:00Z",
  "updated_at": "2025-02-21T15:00:00Z"
}
```

**Error Responses:**
- `409 Conflict`: Group ID already exists
- `400 Bad Request`: Invalid data

#### Delete Telegram Group (Admin Only)
```
DELETE /api/v1/telegram-groups/{group_id}
Authorization: Bearer <admin_token>
```

**Response:** `204 No Content`

**Error Responses:**
- `404 Not Found`: Group not found

#### Test Telegram Notification (Admin Only)
```
POST /api/v1/telegram-groups/{group_id}/test
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "message": "Test notification sent successfully"
}
```

**Error Responses:**
- `400 Bad Request`: Failed to send (bot not in group, etc.)

---

### 2. Updated Booking API

#### Create Booking
```
POST /api/v1/bookings
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body (NEW - telegram_group_id is now REQUIRED):**
```json
{
  "room_id": "507f1f77bcf86cd799439012",
  "telegram_group_id": -1001234567890,
  "title": "Sprint Planning",
  "start_time": "2025-02-24T09:00:00+07:00",
  "end_time": "2025-02-24T11:00:00+07:00",
  "division": "Engineering",
  "description": "Weekly sprint planning meeting"
}
```

**Important Changes:**
- `telegram_group_id` field is now **REQUIRED**
- Value must be a valid Telegram group ID (integer, usually negative)
- Group must exist and be active in the system

**Error Responses:**
- `409 Conflict`: Group not found or inactive
- Other errors (conflicts, validation, etc.) remain the same

#### Get Booking Detail
```
GET /api/v1/bookings/{booking_id}
Authorization: Bearer <token>
```

**Response (NEW - includes telegram_group_id):**
```json
{
  "id": "507f1f77bcf86cd799439013",
  "booking_number": "BK-00001",
  "user_id": "507f1f77bcf86cd799439014",
  "user_snapshot": {
    "full_name": "Budi Santoso",
    "username": "budisantoso",
    "division": "Engineering",
    "telegram_id": 123456789
  },
  "room_id": "507f1f77bcf86cd799439012",
  "room_snapshot": {
    "name": "Ruang Meeting 1"
  },
  "telegram_group_id": -1001234567890,
  "title": "Sprint Planning",
  "division": "Engineering",
  "description": "Weekly sprint planning meeting",
  "start_time": "2025-02-24T09:00:00+07:00",
  "end_time": "2025-02-24T11:00:00+07:00",
  "status": "active",
  "published": false,
  "created_at": "2025-02-21T15:00:00Z",
  "updated_at": "2025-02-21T15:00:00Z"
}
```

**Important Changes:**
- Response now includes `telegram_group_id` field

---

## Frontend UI Changes Required

### 1. Create Booking Form

**Changes Needed:**

1. **Add Telegram Group Selector** (REQUIRED)
   - Add a dropdown/select field for `telegram_group_id`
   - This field is mandatory and cannot be empty
   - Load available groups from `/api/v1/telegram-groups` API
   - Display `group_name` to users, send `group_id` in request

2. **Form Validation**
   - Ensure `telegram_group_id` is selected before submission
   - Show error if no group is selected

**Example UI Structure:**

```html
<!-- Before form submission, fetch groups -->
const fetchTelegramGroups = async () => {
  const response = await fetch('/api/v1/telegram-groups', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  const data = await response.json();
  return data.groups;
};

// In form
<select 
  name="telegram_group_id" 
  required
  value={formData.telegram_group_id}
  onChange={(e) => setFormData({...formData, telegram_group_id: parseInt(e.target.value)})}
>
  <option value="">Select Telegram Group</option>
  {groups.map(group => (
    <option key={group.id} value={group.group_id}>
      {group.group_name}
    </option>
  ))}
</select>
```

### 2. Booking Detail Page

**Changes Needed:**

1. **Display Telegram Group Info**
   - Show the name of the Telegram group where the booking was published
   - Can use `telegram_group_id` from booking response to match with groups list
   - If group name is not available, display the group ID

**Example UI:**

```html
<div className="booking-details">
  {/* ... existing fields ... */}
  
  <div className="detail-item">
    <label>Telegram Group:</label>
    <span>{getGroupName(booking.telegram_group_id)}</span>
  </div>
</div>

// Helper function
const getGroupName = (groupId) => {
  const group = groups.find(g => g.group_id === groupId);
  return group ? group.group_name : `Group ${groupId}`;
};
```

### 3. Admin Panel - Telegram Groups Management (Optional)

**Recommended Features:**

1. **List All Groups**
   - Table showing all Telegram groups
   - Columns: Group Name, Group ID, Status, Created Date
   - Actions: Delete, Test Notification

2. **Add New Group**
   - Form with fields:
     - `group_id`: Input for Telegram group ID (number)
     - `group_name`: Input for display name (text)
   - Button to save

3. **Delete Group**
   - Confirmation dialog before deletion
   - Note: Deleting a group doesn't affect existing bookings

4. **Test Notification**
   - Button to send test message to a group
   - Useful for verifying bot permissions

**Example UI Structure:**

```html
<!-- List Groups -->
<table>
  <thead>
    <tr>
      <th>Group Name</th>
      <th>Group ID</th>
      <th>Status</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {groups.map(group => (
      <tr key={group.id}>
        <td>{group.group_name}</td>
        <td>{group.group_id}</td>
        <td>{group.is_active ? 'Active' : 'Inactive'}</td>
        <td>
          <button onClick={() => testGroup(group.group_id)}>Test</button>
          <button onClick={() => deleteGroup(group.group_id)}>Delete</button>
        </td>
      </tr>
    ))}
  </tbody>
</table>

<!-- Add Group Form -->
<form onSubmit={handleAddGroup}>
  <input 
    type="number" 
    name="group_id" 
    placeholder="Telegram Group ID (e.g., -1001234567890)"
    required
  />
  <input 
    type="text" 
    name="group_name" 
    placeholder="Display Name"
    required
  />
  <button type="submit">Add Group</button>
</form>
```

---

## Migration Notes

### For Existing Bookings

**Important:** Bookings created before this update will not have `telegram_group_id` field. These bookings:
- Can still be viewed and updated normally
- Cannot be published (will error if trying to publish)
- May need manual migration if notification is required

**Solution Options:**
1. Manual update: Admin updates old bookings via database directly
2. Data migration script: Use provided backend script to migrate
3. Frontend handling: Show a message for bookings without group

---

## Validation & Error Handling

### Create Booking Validation

1. **Fetch Groups First**
   ```javascript
   // Always fetch available groups before showing form
   const groups = await fetchTelegramGroups();
   
   if (groups.length === 0) {
     // Show error: No telegram groups available
     // Contact admin to add groups
   }
   ```

2. **Validate Selection**
   ```javascript
   if (!formData.telegram_group_id) {
     setError('Please select a Telegram group');
     return;
   }
   ```

3. **Handle API Errors**
   ```javascript
   try {
     const response = await createBooking(formData);
   } catch (error) {
     if (error.detail?.includes('Telegram group')) {
       // Specific error for telegram group
       setError('Invalid Telegram group selected');
     } else {
       // Handle other errors
     }
   }
   ```

### Admin Panel Validation

1. **Duplicate Group ID**
   - API returns 409 Conflict if group_id already exists
   - Show error to user: "This Telegram group ID is already registered"

2. **Test Notification Failure**
   - API returns 400 if bot cannot send to group
   - Show error: "Failed to send test. Ensure bot is added to the group."

---

## Testing Checklist

### User Flow
- [ ] Create booking form shows telegram group dropdown
- [ ] Dropdown loads all available groups
- [ ] Form validates that a group is selected
- [ ] Successful booking creation stores telegram_group_id
- [ ] Booking detail page shows telegram group name
- [ ] Publish booking sends notification to correct group

### Admin Flow
- [ ] Admin panel lists all telegram groups
- [ ] Admin can add new telegram group
- [ ] Admin can delete telegram group
- [ ] Admin can test notification to any group
- [ ] Duplicate group IDs are rejected
- [ ] Test notifications work correctly

### Edge Cases
- [ ] Handle case when no groups exist
- [ ] Handle case when all groups are inactive
- [ ] Show appropriate error messages
- [ ] Handle network errors gracefully

---

## Additional Resources

### Getting Telegram Group ID

To find a Telegram group ID:
1. Add your bot to the group
2. Send a message to the group
3. Use `getUpdates` API endpoint or a bot like @userinfobot
4. Group IDs are usually negative numbers (e.g., -1001234567890)

### Bot Permissions

Ensure your bot has these permissions in the group:
- Send messages
- Send notifications (optional, for updates)

---

## Questions?

If you have questions about these changes, please contact the backend team.
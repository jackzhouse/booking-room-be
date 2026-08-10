# Telegram Group Management API

Admin-only endpoints manage Telegram groups used for booking notifications.

## Update a group

`PUT /api/v1/telegram-groups/{group_id}`

`group_id` is Telegram chat ID, not database ObjectId.

Request body may include either or both fields:

```json
{
  "group_name": "General Announcement",
  "is_active": true
}
```

Returns updated group (`200`). Returns `404` when chat ID is not registered. Requires admin bearer token.

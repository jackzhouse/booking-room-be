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

## Notification topic (forum groups)

For a group with Topics enabled, booking notifications are posted in the topic named `tkiRoom` instead of the General topic. Group responses include:

```json
{
  "message_thread_id": 15,
  "topic_name": "tkiRoom"
}
```

Both are `null` when the group has no topic (notifications go to the main chat). The id is learned by the bot, not entered in the admin panel:

- The bot reads the service message when a topic named `tkiRoom` is created (or an existing topic is renamed to it) in a registered group.
- For a topic that already existed, a group admin sends `/settopic` inside the topic.
- `/settopic hapus` (group admin) clears it.

If Telegram reports the topic no longer exists, the bot clears the stored id and posts in the main chat.

The bot needs to be able to read messages in the group (make it an admin, or send the command as a reply to the bot).

## Booking message editing

When a published booking is edited, the bot edits its earlier message in each group instead of sending a new one. The message location is stored per booking in `telegram_messages` (`main`, `verification`, `consumption`; internal, not in `BookingResponse`). A booking published before this feature, or whose message was deleted, gets one new message and is edited from then on. Cancellation and "selesai" notifications are always new messages.

## List groups

`GET /api/v1/telegram-groups?isFilter=true|false` (semua user login)

- `isFilter=true` (default): grup yang sedang dipakai sebagai grup konsumsi/verifikasi default **tidak** ikut dikembalikan. Dipakai form booking untuk pilihan grup tujuan.
- `isFilter=false`: daftar lengkap grup aktif. Dipakai halaman admin (grup Telegram, pengaturan), pilihan grup konsumsi, dan pencarian nama grup pada detail booking.

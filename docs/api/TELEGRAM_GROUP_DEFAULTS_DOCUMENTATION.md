# Booking Telegram Group Defaults API

## Get booking group defaults

`GET /api/v1/telegram-groups/defaults`

Authentication: required. Any active user may call this endpoint; it exposes only the consumption default needed by the booking form, not admin settings.

Response:

```json
{
  "default_consumption_group_id": -1001234567890
}
```

When no valid setting exists, `default_consumption_group_id` is `null`.

The booking form uses this value when a user enables consumption. User may choose another group. Server-side booking creation still applies the same setting when no `consumption_group_id` is sent.

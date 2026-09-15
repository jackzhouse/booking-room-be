# Telegram Linking and Mini App API

## Identity model

`User.telegram_id` is the verified Telegram identity. `telegram_username` is display metadata and must not be used for authorization. Linking never overwrites Katalis name, email, role, or external identifiers.

## Create link code

`POST /api/v1/auth/telegram-link/code`

Requires an authenticated Booking Room user. Returns a cryptographically generated, single-use six-digit code owned by that user and valid for three minutes. Creating another code replaces older pending codes. Repeated creation within ten seconds returns `429 LINK_CODE_RATE_LIMITED`.

```json
{
  "success": true,
  "data": {
    "code": "123456",
    "expires_at": "2026-09-14T17:00:00+07:00",
    "expires_in": 180
  }
}
```

The bot `/authorize` handler passes verified Telegram user data to `AuthCodeService.complete_telegram_link`. The legacy login-code completion method deliberately rejects link codes. Each Telegram user is limited to five `/authorize` attempts per minute per running bot process.

## Poll link status

`GET /api/v1/auth/telegram-link/status?code=123456`

Requires authentication. A user can only inspect their own code. Status values:

- `pending`: waiting for Telegram verification.
- `linked`: Telegram ID saved on the requesting user.
- `expired`: missing, expired, or inaccessible code.
- `conflict`: Telegram ID or target account is already linked elsewhere.

## Disconnect own Telegram account

`DELETE /api/v1/auth/telegram-link`

Requires authentication. Clears `telegram_id` and `telegram_username`; other user data remains unchanged.

## Admin conflict recovery

`DELETE /api/v1/admin/users/{user_id}/telegram-link`

Requires admin access. Clears the selected user's Telegram link so the identity can be linked again. Accounts and bookings are never merged automatically.

## Mini App login

`POST /api/v1/auth/tma`

```json
{
  "init_data": "query_id=...&user=...&auth_date=...&hash=..."
}
```

The backend validates the Telegram signature and rejects `auth_date` older than five minutes. Login succeeds only when the verified Telegram ID is already linked to an active Booking Room user. It returns the normal Booking Room bearer JWT and does not create a new user.

Stable error codes are returned in `detail.code`:

- `INVALID_INIT_DATA`
- `INIT_DATA_EXPIRED`
- `TELEGRAM_NOT_LINKED`
- `USER_INACTIVE`

## Rollout dependency

Menu Button and BotFather configuration require the deployed HTTPS frontend URL. Configure them only after backend, bot, and frontend changes are deployed together.

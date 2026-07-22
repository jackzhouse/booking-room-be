# Production First Admin Bootstrap

## Purpose

Provision one Booking Room admin from Katalis SSO without running employee sync. This is intended for a new, empty production database.

## Required Katalis account-detail host

Set `KATALIS_ACCOUNT_DETAIL_BASE_URL=https://api.teknologikartu.com` and `KATALIS_ACCOUNT_DETAIL_PATH=/attendance/api/v1/admin/employees/account/detail` in production. Keep it separate from `KATALIS_BASE_URL`: `api.katalis.info` does not expose this route and returns `404`.

Consul is configuration source of truth. Set both keys in `new-config/psp-booking-room-be/setting`, then deploy/restart backend. Confirm startup log contains `account_detail_base_url=https://api.teknologikartu.com` and Attendance path. If response still contains `/api/v1/admin/employees/account/detail`, running container is old backend image or Consul still sets legacy `KATALIS_ACCOUNT_DETAIL_PATH`; redeploy after correcting Consul.

## Configuration

Set this production configuration before deploying:

| Key | Value |
| --- | --- |
| `INITIAL_ADMIN_ACCOUNT_ID` | Katalis `accountId` of the first Booking Room admin |

When deployment uses Consul, add the key to `new-config/psp-booking-room-be/setting`. Otherwise set it as the backend service environment variable. Use the exact `accountId` from Katalis `account/detail`; do not use username, employee number, or account display name.

## First Login

1. Deploy backend with an empty MongoDB database and `INITIAL_ADMIN_ACCOUNT_ID` configured.
2. Sign in once through normal Katalis login using that account.
3. Open Admin Dashboard. The account must have admin access.
4. Create rooms, update booking settings, and configure Telegram notification groups.

The matching account is made admin only when its local Booking Room user record is first created. No `sync-employees` request runs. Later role changes are stored in MongoDB and are not overwritten by future logins.

## Verification

- `GET /health` returns healthy after deploy.
- First-admin login can open admin pages and create a room.
- A different Katalis account is created as a non-admin user.
- User list shows only intended first admin before any role changes.

# Booking Room Backend API

Backend API for Meeting Room Booking System with Telegram integration. Built with FastAPI, MongoDB, and Telegram Bot API.

## Tech Stack

- **Framework**: FastAPI
- **Database**: MongoDB (via Motor - async driver)
- **ODM**: Beanie (MongoDB ODM for Python)
- **Auth**: JWT + Telegram Hash Verification
- **Bot**: python-telegram-bot v20+
- **Validation**: Pydantic v2

## Features

- ✅ User authentication via Telegram Login Widget or Mini App
- ✅ Room booking with conflict detection
- ✅ Operating hours validation
- ✅ Telegram bot for booking management
- ✅ Real-time notifications to Telegram group
- ✅ Admin override capabilities
- ✅ Booking history audit trail
- ✅ Beautiful Indonesian-formatted messages

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # Entry point FastAPI
│   ├── core/
│   │   ├── config.py            # Settings from .env
│   │   ├── database.py          # MongoDB connection
│   │   └── security.py          # JWT + Telegram verification
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py          # Auth endpoints
│   │   │   ├── bookings.py      # Booking CRUD
│   │   │   ├── rooms.py         # Room management
│   │   │   └── admin.py         # Admin endpoints
│   │   └── deps.py              # Dependency injection
│   ├── models/                  # Beanie Document models
│   │   ├── user.py
│   │   ├── room.py
│   │   ├── booking.py
│   │   ├── booking_history.py
│   │   └── setting.py
│   ├── schemas/                 # Pydantic schemas
│   │   ├── auth.py
│   │   ├── booking.py
│   │   ├── room.py
│   │   └── admin.py
│   ├── services/                # Business logic
│   │   ├── booking_service.py
│   │   ├── conflict_service.py
│   │   └── telegram_service.py
│   └── bot/
│       ├── bot.py               # Bot setup
│       ├── handlers/
│       │   ├── start.py
│       │   ├── mybooking.py
│       │   ├── schedule.py
│       │   └── cancel.py
│       └── webhook.py           # Webhook handler
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### Prerequisites

- Python 3.11+
- MongoDB (running locally or remote)
- Telegram Bot Token (from @BotFather)
- Telegram Group ID for notifications

### Setup Steps

1. **Clone the repository**
   ```bash
   cd /home/tki-mobile/Documents/Website_Development/booking-room-be
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

5. **Get Telegram Bot Token**
   - Open Telegram and search for @BotFather
   - Send `/newbot` command
   - Follow the instructions to create a bot
   - Copy the bot token (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

6. **Get Your Telegram ID**
   - Open Telegram and search for @userinfobot
   - Send any message to get your Telegram ID
   - This will be your `ADMIN_TELEGRAM_ID`

7. **Get Telegram Group ID**
   - Add your bot to the Telegram group where you want notifications
   - Forward a message from the group to @userinfobot
   - The bot will reply with the group ID (negative number, e.g., `-1001234567890`)
   - Update the `telegram_group_id` setting via admin endpoint

## Running the Application

### Development Mode

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc
- Health Check: http://localhost:8000/health

## API Endpoints

### Authentication
- `POST /api/v1/auth/telegram` - Login via Telegram Login Widget
- `POST /api/v1/auth/tma` - Login via Telegram Mini App
- `GET /api/v1/auth/me` - Get current user info

### Rooms
- `GET /api/v1/rooms` - List all active rooms
- `GET /api/v1/rooms/{id}` - Get room details
- `GET /api/v1/rooms/{id}/schedule` - Get room schedule by date
- `POST /api/v1/rooms` - Create room (Admin)
- `PATCH /api/v1/rooms/{id}` - Update room (Admin)
- `PATCH /api/v1/rooms/{id}/toggle` - Toggle room status (Admin)

### Bookings
- `GET /api/v1/bookings` - List user's bookings
- `GET /api/v1/bookings/{id}` - Get booking details
- `POST /api/v1/bookings` - Create booking
- `PATCH /api/v1/bookings/{id}` - Update booking
- `DELETE /api/v1/bookings/{id}` - Cancel booking

### Admin
- `GET /api/v1/admin/bookings` - Get all bookings
- `DELETE /api/v1/admin/bookings/{id}` - Cancel any booking
- `GET /api/v1/admin/rooms` - Get all rooms
- `GET /api/v1/admin/users` - Get all users
- `GET /api/v1/admin/settings` - Get all settings
- `GET /api/v1/admin/settings/{key}` - Get specific setting
- `PATCH /api/v1/admin/settings/{key}` - Update setting
- `POST /api/v1/admin/settings/test-notification` - Test Telegram notification

### Telegram Bot
- `POST /webhook/telegram/{BOT_TOKEN}` - Telegram webhook endpoint

## Telegram Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and instructions |
| `/help` | Show help information |
| `/mybooking` | View your active bookings |
| `/schedule` | View today's schedule |
| `/schedule DD-MM-YYYY` | View schedule for specific date |
| `/cancel BK-XXXXX` | Cancel a booking |

## Initial Setup

### 1. Create Admin User

The first user to login with `ADMIN_TELEGRAM_ID` will automatically get admin privileges.

### 2. Create Rooms

Use the admin endpoint to create rooms:

```bash
curl -X POST "http://localhost:8000/api/v1/rooms" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ruang Meeting 1",
    "capacity": 10,
    "facilities": ["proyektor", "AC", "whiteboard"],
    "location": "Lantai 2"
  }'
```

### 3. Configure Telegram Group ID

Update the `telegram_group_id` setting:

```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/settings/telegram_group_id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "-1001234567890"
  }'
```

### 4. Test Telegram Notification

```bash
curl -X POST "http://localhost:8000/api/v1/admin/settings/test-notification" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## Business Rules

### Booking Validation
- Booking time must be within operating hours (default: 08:00 - 18:00)
- Minimum booking duration: 15 minutes
- No overlapping bookings in the same room
- Admins bypass all validation rules

### Permissions
- Users can only view and manage their own bookings
- Admins can view and manage all bookings
- Only admins can create, update, and delete rooms
- Only admins can modify system settings

## Environment Variables

| Variable | Description | Required |
|----------|-------------|-----------|
| `APP_ENV` | Environment (development/production) | No |
| `SECRET_KEY` | JWT secret key (min 32 chars) | Yes |
| `JWT_ALGORITHM` | JWT algorithm (default: HS256) | No |
| `JWT_EXPIRE_MINUTES` | Token expiration time (default: 10080 = 7 days) | No |
| `MONGODB_URL` | MongoDB connection string | Yes |
| `MONGODB_DB_NAME` | Database name | Yes |
| `BOT_TOKEN` | Telegram bot token | Yes |
| `WEBHOOK_BASE_URL` | Base URL for webhook | Yes |
| `ADMIN_TELEGRAM_ID` | Admin Telegram ID | Yes |

## Testing

Run tests with pytest:

```bash
pytest
```

## Deployment

### Using Docker (Coming Soon)

Dockerfile and docker-compose.yml will be provided for production deployment.

## Troubleshooting

### MongoDB Connection Issues
- Ensure MongoDB is running: `mongosh` or `mongo`
- Check connection string in `.env`
- Verify firewall settings

### Telegram Webhook Issues
- Ensure `WEBHOOK_BASE_URL` is publicly accessible
- Check bot token is correct
- Verify webhook URL is set correctly

### Booking Conflicts
- Check operating hours settings
- Verify time format (ISO 8601 with timezone)
- Review existing bookings for overlaps

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please contact the development team.
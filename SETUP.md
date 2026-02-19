# Setup Guide - Booking Room Backend

Quick setup guide to get your Booking Room Backend running.

## Prerequisites Checklist

- [ ] Python 3.11+ installed
- [ ] MongoDB running locally (`mongosh` or `mongo` works)
- [ ] Telegram Bot Token (from @BotFather)
- [ ] Your Telegram ID (from @userinfobot)
- [ ] Telegram Group ID for notifications (optional, can set later)

## Quick Setup (5 minutes)

### 1. Create Virtual Environment

```bash
cd /home/tki-mobile/Documents/Website_Development/booking-room-be
python -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create .env File

```bash
cp .env.example .env
```

### 4. Edit .env File

Open `.env` in your editor and update:

```env
# App Configuration
APP_ENV=development
SECRET_KEY=generate-a-random-32-character-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=10080

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=booking_app

# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
WEBHOOK_BASE_URL=http://localhost:8000
ADMIN_TELEGRAM_ID=YOUR_TELEGRAM_ID_HERE
```

**Important:**
- `SECRET_KEY`: Generate a random string with at least 32 characters
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- `BOT_TOKEN`: Get from @BotFather on Telegram
- `ADMIN_TELEGRAM_ID`: Get from @userinfobot on Telegram
- `WEBHOOK_BASE_URL`: For local development, use `http://localhost:8000`

### 5. Start the Application

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
✅ Successfully connected to MongoDB: mongodb://localhost:27017
✅ Beanie ODM initialized with database: booking_app
✅ Initialized default setting: operating_hours_start
✅ Initialized default setting: operating_hours_end
✅ Initialized default setting: telegram_group_id
✅ Telegram webhook set to: http://localhost:8000/webhook/telegram/YOUR_BOT_TOKEN
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Initial Configuration

### Step 1: Test the API

Open your browser:
- http://localhost:8000 - Root endpoint
- http://localhost:8000/docs - Interactive API documentation
- http://localhost:8000/health - Health check

### Step 2: Login via Telegram (Get JWT Token)

You can test authentication using Postman or curl:

**Option 1: Using Telegram Login Widget (Web)**
- Create a simple HTML file with Telegram Login Widget
- Or test via API documentation at `/docs`

**Option 2: Quick Test with curl**
```bash
# This requires actual Telegram data from Login Widget
# For testing, you'll need to implement a simple frontend
```

### Step 3: Create First Room (Admin)

Using the interactive docs at http://localhost:8000/docs:

1. Go to `POST /api/v1/rooms`
2. Click "Try it out"
3. Add your JWT token in "Authorization" header: `Bearer YOUR_JWT_TOKEN`
4. Fill in room data:
   ```json
   {
     "name": "Ruang Meeting 1",
     "capacity": 10,
     "facilities": ["proyektor", "AC", "whiteboard"],
     "location": "Lantai 2"
   }
   ```
5. Click "Execute"

### Step 4: Configure Telegram Group ID (Optional)

If you want notifications to Telegram group:

1. Create a Telegram group for notifications
2. Add your bot to the group
3. Forward a message from the group to @userinfobot to get group ID
4. Update setting via API:

```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/settings/telegram_group_id" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "value": "-1001234567890"
  }'
```

5. Test notification:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/settings/test-notification" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Step 5: Test Telegram Bot

Open Telegram and search for your bot. Try these commands:

- `/start` - Should show welcome message
- `/help` - Should show help information
- `/schedule` - Should show today's schedule (empty initially)

## Common Issues

### MongoDB Connection Failed

**Error:** `Failed to connect to MongoDB`

**Solution:**
```bash
# Check if MongoDB is running
mongosh --eval "db.adminCommand('ping')"

# Start MongoDB if not running
sudo systemctl start mongod

# Or on macOS
brew services start mongodb-community
```

### Telegram Webhook Failed

**Error:** Webhook setup failed

**Solution:**
- Ensure `WEBHOOK_BASE_URL` in `.env` is correct
- For local development, use `http://localhost:8000`
- For production, use your public domain with HTTPS
- Check bot token is correct

### Import Errors

**Error:** `ModuleNotFoundError: No module named '...'`

**Solution:**
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### JWT Token Invalid

**Error:** `401 Unauthorized`

**Solution:**
- Make sure `SECRET_KEY` in `.env` is set
- Token must have at least 32 characters
- Regenerate token if changed

## Next Steps

1. **Build a Frontend**: Create a web or mobile app that uses this API
2. **Create More Rooms**: Add all meeting rooms to the system
3. **Test Booking Flow**: Create test bookings and verify notifications
4. **Deploy to Production**: Set up with Docker or cloud provider

## Useful Commands

### Run in development mode:
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run in production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Run tests (when implemented):
```bash
pytest
```

### Check MongoDB data:
```bash
mongosh
use booking_app
db.users.find().pretty()
db.bookings.find().pretty()
db.rooms.find().pretty()
```

## Support

For detailed documentation, see `README.md`

For issues or questions, please contact the development team.
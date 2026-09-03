import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, init_beanie_models
from app.api.v1 import auth, bookings, rooms, admin, telegram_groups
from app.bot.webhook import set_webhook, delete_webhook, handle_webhook_update, is_valid_webhook_secret
from app.services.scheduler_service import check_and_notify_ended_bookings
from telegram import Update

# Create scheduler instance
scheduler = AsyncIOScheduler()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Import all models for Beanie initialization
from app.models.user import User
from app.models.room import Room
from app.models.booking import Booking
from app.models.booking_history import BookingHistory
from app.models.setting import Setting
from app.models.auth_code import AuthCode
from app.models.telegram_group import TelegramGroup
from app.models.sync_task import SyncTask
from app.models.external_division import ExternalDivision


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await connect_to_mongo()
    
    # Initialize Beanie with all document models
    await init_beanie_models([
        User,
        Room,
        Booking,
        BookingHistory,
        Setting,
        AuthCode,
        TelegramGroup,
        SyncTask,
        ExternalDivision
    ])
    
    # Initialize default settings if not exist
    await initialize_default_settings()
    
    # Start scheduler for automatic cleanup notifications
    scheduler.add_job(
        check_and_notify_ended_bookings,
        'interval',
        minutes=5,
        id='cleanup_notifications',
        name='Send cleanup notifications for ended bookings',
        replace_existing=True
    )
    scheduler.start()
    print("✅ Scheduler started: Will check for ended bookings every 5 minutes")
    
    # Set Telegram webhook (for Vercel deployment)
    try:
        await set_webhook()
        print("✅ Telegram webhook configured successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not set Telegram webhook: {str(e)}")
        print("   Bot features will be limited until a valid webhook URL is provided.")
        print("   This is not critical - the application will continue running.")
        print("   You can manually set the webhook later using the Telegram API.")
        # Don't raise exception - allow app to continue even if webhook setup fails
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    print("✅ Scheduler stopped")
    
    await close_mongo_connection()
    
    # Note: Webhook is kept configured in Telegram for always-on bot functionality


# Create FastAPI application
app = FastAPI(
    title="Booking Room Backend API",
    description="Backend API for Meeting Room Booking System with Telegram integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS. Explicit origins required for credentialed browser requests.
configured_cors_origins = settings.CORS_ORIGINS or ""
cors_origins = [
    origin.strip().rstrip("/")
    for origin in configured_cors_origins.split(",")
    if origin.strip()
]
if settings.FRONTEND_URL.rstrip("/") not in cors_origins:
    cors_origins.append(settings.FRONTEND_URL.rstrip("/"))
if "https://booking-room.teknologikartu.com" not in cors_origins:
    cors_origins.append("https://booking-room.teknologikartu.com")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(bookings.router, prefix="/api/v1")
app.include_router(rooms.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(telegram_groups.router, prefix="/api/v1")

# Public proxy compatibility: api.teknologikartu.com exposes Booking under /booking.
# Keep internal /api/v1 routes while accepting unstripped /booking/api/v1 paths.
app.include_router(auth.router, prefix="/booking/api/v1", include_in_schema=False)
app.include_router(bookings.router, prefix="/booking/api/v1", include_in_schema=False)
app.include_router(rooms.router, prefix="/booking/api/v1", include_in_schema=False)
app.include_router(admin.router, prefix="/booking/api/v1", include_in_schema=False)
app.include_router(telegram_groups.router, prefix="/booking/api/v1", include_in_schema=False)


@app.post("/api/v1/webhook/telegram")
@app.post("/webhook/telegram", include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
):
    """
    Telegram webhook endpoint.
    Receives updates from Telegram and passes them to the bot handler.
    """
    if not is_valid_webhook_secret(x_telegram_bot_api_secret_token):
        logger.warning("Telegram webhook rejected: invalid secret")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook secret",
        )

    try:
        data = await request.json()
        logger.info(
            "Telegram webhook received: update_id=%s types=%s",
            data.get("update_id"),
            sorted(key for key in data if key != "update_id"),
        )
        await handle_webhook_update(data, None)
    except Exception:
        logger.exception("Telegram webhook processing failed")
        raise

    logger.info("Telegram webhook dispatched successfully: update_id=%s", data.get("update_id"))
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Booking Room Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "booking-room-backend"
    }


async def initialize_default_settings():
    """Initialize default settings if they don't exist"""
    default_settings = [
        {
            "key": "operating_hours_start",
            "value": "08:00",
            "description": "Jam mulai operasional booking"
        },
        {
            "key": "operating_hours_end",
            "value": "18:00",
            "description": "Jam selesai operasional booking"
        },
        {
            "key": "min_booking_duration_minutes",
            "value": "15",
            "description": "Durasi minimal booking dalam menit"
        },
        {
            "key": "telegram_group_id",
            "value": "",
            "description": "ID grup Telegram tujuan notifikasi"
        },
        {
            "key": "default_consumption_group_id",
            "value": "",
            "description": "ID grup Telegram default untuk notifikasi konsumsi"
        },
        {
            "key": "default_verification_group_id",
            "value": "",
            "description": "ID grup Telegram default untuk notifikasi verifikasi dan perapian"
        }
    ]
    
    for setting_data in default_settings:
        existing = await Setting.find_one(Setting.key == setting_data["key"])
        if not existing:
            setting = Setting(**setting_data)
            await setting.insert()
            print(f"✅ Initialized default setting: {setting_data['key']}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

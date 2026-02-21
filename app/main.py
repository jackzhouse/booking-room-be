import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, init_beanie_models
from app.api.v1 import auth, bookings, rooms, admin, telegram_groups
from app.bot.webhook import set_webhook, delete_webhook, handle_webhook_update
from telegram import Update
from fastapi import Request

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
        TelegramGroup
    ])
    
    # Initialize default settings if not exist
    await initialize_default_settings()
    
    # Set Telegram webhook (for Vercel deployment)
    try:
        await set_webhook()
        print("✅ Telegram webhook configured successfully")
    except Exception as e:
        print(f"⚠️  Warning: Could not set Telegram webhook: {str(e)}")
        print("   Bot features will be limited until a valid BOT_TOKEN is provided.")
    
    yield
    
    # Shutdown
    await close_mongo_connection()
    
    # Note: Webhook is kept configured in Telegram for always-on bot functionality


# Create FastAPI application
app = FastAPI(
    title="Booking Room Backend API",
    description="Backend API for Meeting Room Booking System with Telegram integration",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # In production, specify allowed origins
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


@app.post("/webhook/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Telegram webhook endpoint.
    Receives updates from Telegram and passes them to the bot handler.
    """
    # Verify token matches
    if token != settings.BOT_TOKEN:
        return {"status": "error", "message": "Invalid token"}
    
    # Parse update from request
    data = await request.json()
    
    # Process the update (handler will get bot instance)
    await handle_webhook_update(data, None)
    
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
            "key": "telegram_group_id",
            "value": "",
            "description": "ID grup Telegram tujuan notifikasi"
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
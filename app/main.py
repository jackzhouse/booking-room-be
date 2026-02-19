import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection, init_beanie_models
from app.api.v1 import auth, bookings, rooms, admin
from app.bot.webhook import start_polling, stop_polling

# Import all models for Beanie initialization
from app.models.user import User
from app.models.room import Room
from app.models.booking import Booking
from app.models.booking_history import BookingHistory
from app.models.setting import Setting


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
        Setting
    ])
    
    # Initialize default settings if not exist
    await initialize_default_settings()
    
    # Start Telegram bot in polling mode (background task)
    bot_task = None
    try:
        bot_task = asyncio.create_task(start_polling())
        print("✅ Telegram bot polling started in background")
    except Exception as e:
        print(f"⚠️  Warning: Could not start Telegram bot: {str(e)}")
        print("   Bot features will be limited until a valid BOT_TOKEN is provided.")
    
    yield
    
    # Shutdown
    await close_mongo_connection()
    
    # Stop bot polling
    if bot_task:
        try:
            await stop_polling()
            if not bot_task.done():
                bot_task.cancel()
                try:
                    await bot_task
                except asyncio.CancelledError:
                    pass
        except Exception as e:
            print(f"⚠️  Warning: Error stopping bot: {str(e)}")


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
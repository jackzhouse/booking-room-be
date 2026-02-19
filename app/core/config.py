from pydantic import BaseSettings
from typing import Optional
from zoneinfo import ZoneInfo


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days
    FRONTEND_URL: str  = "https://localhost:3000"  # URL for the frontend application
    
    # Timezone
    TIMEZONE: str = "Asia/Jakarta"  # Default timezone for the application
    
    @property
    def timezone(self) -> ZoneInfo:
        """Get timezone as ZoneInfo object"""
        return ZoneInfo(self.TIMEZONE)

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "booking_app"

    # Telegram
    BOT_TOKEN: str
    WEBHOOK_BASE_URL: str = "https://localhost:8000"
    ADMIN_TELEGRAM_ID: int

    @property
    def webhook_url(self) -> str:
        """Full webhook URL for Telegram bot"""
        return f"{self.WEBHOOK_BASE_URL}/webhook/telegram/{self.BOT_TOKEN}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
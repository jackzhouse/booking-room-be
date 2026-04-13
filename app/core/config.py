from pydantic import BaseSettings, validator
from typing import Optional
from zoneinfo import ZoneInfo
import consul

import yaml


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"  # Default to development for local development
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days
    FRONTEND_URL: str = "https://booking-meeting-flax.vercel.app"  # Production frontend URL
    PREFIX_NAME: str = "/api/v1"  # API prefix

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
    BOT_TOKEN: Optional[str] = None
    WEBHOOK_BASE_URL: str = "https://localhost:8000"
    ADMIN_TELEGRAM_ID: Optional[int] = None

    # External App Integration (e.g., Katalis)
    # External apps use the same SECRET_KEY for JWT encoding/decoding
    KATALIS_PRODUCER: str = "katalis"  # Producer name for external app
    BASE_URL_KATALIS: Optional[str] = None  # Base URL for Katalis API

    @validator('SECRET_KEY', 'BOT_TOKEN', 'ADMIN_TELEGRAM_ID', pre=True, always=True)
    def validate_required_in_production(cls, v, field, values):
        app_env = values.get('APP_ENV', 'production')
        if app_env in ['production', 'staging'] and v is None:
            raise ValueError(f'{field.name} is required in production environment')
        return v

    @property
    def webhook_url(self) -> str:
        """Full webhook URL for Telegram bot"""
        if not self.BOT_TOKEN:
            return ""
        return f"{self.WEBHOOK_BASE_URL}/webhook/telegram/{self.BOT_TOKEN}"

    class Config:
        case_sensitive = True


def load_settings_from_consul():
    """Load settings from Consul key-value store"""
    # Get Consul connection details from environment variables
    c = consul.Consul(host='consul', port=8500)
    index, data = c.kv.get('new-config/psp-booking-room-be/setting')
    config = yaml.load(data['Value'],Loader=yaml.SafeLoader)
    return config


# Load settings from Consul and create Settings instance
if Settings().APP_ENV in ['production', 'staging']:
    consul_settings = load_settings_from_consul()
    settings = Settings(**consul_settings)
else:
    # For development, use default values
    settings = Settings()
from typing import Optional
from zoneinfo import ZoneInfo
import consul
import logging

import yaml
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_ENV: str = "production"  # Default to production for Vercel
    SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 10080  # 7 days
    FRONTEND_URL: str = "https://booking-meeting-flax.vercel.app"  # Production frontend URL

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
    WEBHOOK_SECRET_TOKEN: Optional[str] = None
    ADMIN_TELEGRAM_ID: Optional[int] = None

    # External App Integration (e.g., Katalis)
    # External apps use the same SECRET_KEY for JWT encoding/decoding
    KATALIS_PRODUCER: str = "katalis"  # Producer name for external app
    KATALIS_BASE_URL: str = "https://api.dev.katalis.info"
    KATALIS_ACCOUNT_DETAIL_BASE_URL: str = "https://api.dev.teknologikartu.com"
    KATALIS_DIRECTORY_BASE_URL: str = "https://api.dev.teknologikartu.com"
    KATALIS_CREDENTIAL_CHECK_PATH: str = "/katalis/user/credential/check"
    KATALIS_ACCOUNT_DETAIL_PATH: str = "/attendance/api/v1/admin/employees/account/detail"
    KATALIS_EMPLOYEES_PATH: str = "/attendance/api/v1/admin/employees"
    KATALIS_DIVISIONS_PATH: str = "/attendance/api/v1/admin/divisions"
    INITIAL_ADMIN_ACCOUNT_ID: Optional[str] = None

    @model_validator(mode="after")
    def validate_required_in_production(self):
        if self.APP_ENV != "production":
            return self

        required_fields = ("SECRET_KEY", "BOT_TOKEN", "WEBHOOK_SECRET_TOKEN", "ADMIN_TELEGRAM_ID")
        for field_name in required_fields:
            if getattr(self, field_name) is None:
                raise ValueError(f"{field_name} is required in production environment")

        return self

    @property
    def webhook_url(self) -> str:
        """Full public Telegram webhook URL, behind the Booking API prefix."""
        if not self.BOT_TOKEN:
            return ""
        return f"{self.WEBHOOK_BASE_URL.rstrip('/')}/api/v1/webhook/telegram"

def load_settings_from_consul():
    """Load settings from Consul key-value store"""
    # Local development may not have Consul; fall back to .env/environment.
    try:
        c = consul.Consul(host='consul', port=8500)
        index, data = c.kv.get('new-config/psp-booking-room-be/setting')
        if not data or not data.get('Value'):
            return {}
        config = yaml.load(data['Value'], Loader=yaml.SafeLoader)
        return config or {}
    except Exception as exc:
        logger.warning("Failed to load settings from Consul, using local environment: %s", exc)
        return {}


# Load settings from Consul and create Settings instance
consul_settings = load_settings_from_consul()
settings = Settings(**consul_settings)
logger.info(
    "Katalis SSO config loaded: account_detail_base_url=%s account_detail_path=%s",
    settings.KATALIS_ACCOUNT_DETAIL_BASE_URL,
    settings.KATALIS_ACCOUNT_DETAIL_PATH,
)

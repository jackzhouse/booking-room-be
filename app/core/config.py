from pydantic import BaseSettings, validator
from typing import Optional
from zoneinfo import ZoneInfo
import consul
import os


class Settings(BaseSettings):
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
    ADMIN_TELEGRAM_ID: Optional[int] = None

    @validator('SECRET_KEY', 'BOT_TOKEN', 'ADMIN_TELEGRAM_ID', pre=True, always=True)
    def validate_required_in_production(cls, v, field, values):
        app_env = values.get('APP_ENV', 'production')
        if app_env == "production" and v is None:
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
    consul_host = os.getenv('CONSUL_HOST', 'localhost')
    consul_port = int(os.getenv('CONSUL_PORT', 8500))

    # Check if Consul is available
    consul_available = False
    try:
        test_client = consul.Consul(host=consul_host, port=consul_port)
        test_client.status.leader()  # Test connection
        consul_available = True
    except:
        consul_available = False

    settings_dict = {}

    if consul_available:
        # Create Consul client
        client = consul.Consul(host=consul_host, port=consul_port)

        # Define the keys to load from Consul
        consul_keys = [
            'APP_ENV',
            'SECRET_KEY',
            'JWT_ALGORITHM',
            'JWT_EXPIRE_MINUTES',
            'FRONTEND_URL',
            'TIMEZONE',
            'MONGODB_URL',
            'MONGODB_DB_NAME',
            'BOT_TOKEN',
            'WEBHOOK_BASE_URL',
            'ADMIN_TELEGRAM_ID'
        ]

        # Load each key from Consul
        for key in consul_keys:
            try:
                index, data = client.kv.get(key)
                if data and data.get('Value'):
                    # Decode bytes to string
                    value = data['Value'].decode('utf-8')
                    # Convert to appropriate type
                    if key in ['JWT_EXPIRE_MINUTES', 'ADMIN_TELEGRAM_ID']:
                        settings_dict[key] = int(value)
                    else:
                        settings_dict[key] = value
            except Exception as e:
                print(f"Warning: Could not load {key} from Consul: {e}")
                # Fall back to environment variable if available
                env_value = os.getenv(key)
                if env_value:
                    if key in ['JWT_EXPIRE_MINUTES', 'ADMIN_TELEGRAM_ID']:
                        settings_dict[key] = int(env_value)
                    else:
                        settings_dict[key] = env_value
    else:
        print("Consul not available, using environment variables and defaults")
        # Default to development when Consul is not available
        settings_dict['APP_ENV'] = 'development'

    return settings_dict


# Load settings from Consul and create Settings instance
consul_settings = load_settings_from_consul()
settings = Settings(**consul_settings)
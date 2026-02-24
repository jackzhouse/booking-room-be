from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field, EmailStr


class User(Document):
    """User model for Telegram-authenticated users"""
    
    telegram_id: Indexed(int, unique=True)  # Unique index for telegram_id
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    division: Optional[str] = None
    email: Optional[EmailStr] = None
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"
        indexes = [
            "telegram_id",
            "username",
            "is_admin",
            "is_active"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "telegram_id": 123456789,
                "full_name": "Budi Santoso",
                "username": "budisantoso",
                "avatar_url": "https://...",
                "division": "Engineering",
                "is_admin": False,
                "is_active": True
            }
        }

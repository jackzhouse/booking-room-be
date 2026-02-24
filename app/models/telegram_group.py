from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field
from bson import ObjectId


class TelegramGroup(Document):
    """Model for storing Telegram group configurations"""
    
    group_id: Indexed(int, unique=True)  # Telegram group chat ID
    group_name: str  # Human-readable name for display
    is_active: bool = Field(default=True)  # Active/inactive status
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[ObjectId] = None  # Admin who last updated
    
    class Settings:
        name = "telegram_groups"
        indexes = [
            "group_id",
            "is_active"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "group_id": -1001234567890,
                "group_name": "General Announcement",
                "is_active": True,
                "created_at": "2025-02-21T14:00:00Z",
                "updated_at": "2025-02-21T14:00:00Z"
            }
        }
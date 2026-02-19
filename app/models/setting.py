from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field
from bson import ObjectId


class Setting(Document):
    """Settings model for application configuration"""
    
    key: Indexed(str, unique=True)
    value: str
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[ObjectId] = None
    
    class Settings:
        name = "settings"
        indexes = [
            "key"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "key": "operating_hours_start",
                "value": "08:00",
                "description": "Jam mulai operasional booking"
            }
        }

from datetime import datetime
from typing import List, Optional
from beanie import Document
from pydantic import Field


class Room(Document):
    """Room model for meeting rooms"""
    
    name: str
    capacity: int
    facilities: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "rooms"
        indexes = [
            "name",
            "is_active"
        ]
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Ruang Meeting 1",
                "capacity": 10,
                "facilities": ["proyektor", "AC", "whiteboard", "TV"],
                "location": "Lantai 2",
                "is_active": True
            }
        }
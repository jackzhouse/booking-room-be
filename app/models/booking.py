from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import BaseModel, Field
from bson import ObjectId


class UserSnapshot(BaseModel):
    """Snapshot of user data at booking time"""
    full_name: str
    username: Optional[str] = None
    division: Optional[str] = None
    telegram_id: int


class RoomSnapshot(BaseModel):
    """Snapshot of room data at booking time"""
    name: str


class Booking(Document):
    """Booking model for room reservations"""
    
    booking_number: Indexed(str, unique=True)  # Unique booking number
    user_id: ObjectId
    user_snapshot: UserSnapshot
    room_id: ObjectId
    room_snapshot: RoomSnapshot
    title: str
    division: Optional[str] = None
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: str = Field(default="active")  # active, cancelled
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[ObjectId] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "bookings"
        indexes = [
            [("room_id", 1), ("start_time", 1), ("end_time", 1)],  # Compound index for conflict check
            "user_id",
            "status",
            "booking_number"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "booking_number": "BK-00123",
                "user_id": "507f1f77bcf86cd799439011",
                "user_snapshot": {
                    "full_name": "Budi Santoso",
                    "division": "Engineering",
                    "telegram_id": 123456789
                },
                "room_id": "507f1f77bcf86cd799439012",
                "room_snapshot": {
                    "name": "Ruang Meeting 1"
                },
                "title": "Sprint Planning Q1",
                "division": "Engineering",
                "description": "Kick off sprint dengan seluruh tim dev",
                "start_time": "2025-02-24T09:00:00+07:00",
                "end_time": "2025-02-24T11:00:00+07:00",
                "status": "active"
            }
        }
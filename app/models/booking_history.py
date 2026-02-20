from datetime import datetime
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from bson import ObjectId


class HistoryData(BaseModel):
    """Generic structure for old/new data in history"""
    room_snapshot: Optional[dict] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    division: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class BookingHistory(Document):
    """Audit trail for booking changes"""
    
    booking_id: Indexed(PydanticObjectId)
    booking_number: str
    changed_by: PydanticObjectId
    action: str  # created, updated, cancelled
    old_data: Optional[HistoryData] = None
    new_data: Optional[HistoryData] = None
    changed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "booking_history"
        indexes = [
            "booking_id",
            "booking_number",
            "changed_by",
            "action",
            "changed_at"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "booking_id": "507f1f77bcf86cd799439011",
                "booking_number": "BK-00123",
                "changed_by": "507f1f77bcf86cd799439011",
                "action": "updated",
                "old_data": {
                    "room_snapshot": {"name": "Ruang Meeting 1"},
                    "start_time": "2025-02-24T09:00:00+07:00",
                    "end_time": "2025-02-24T11:00:00+07:00"
                },
                "new_data": {
                    "room_snapshot": {"name": "Ruang Meeting 2"},
                    "start_time": "2025-02-24T13:00:00+07:00",
                    "end_time": "2025-02-24T15:00:00+07:00"
                },
                "changed_at": "2025-02-20T11:00:00Z"
            }
        }
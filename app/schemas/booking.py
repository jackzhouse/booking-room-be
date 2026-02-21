from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserSnapshotResponse(BaseModel):
    """Snapshot of user data at booking time"""
    full_name: str
    username: Optional[str] = None
    division: Optional[str] = None
    telegram_id: int


class RoomSnapshotResponse(BaseModel):
    """Snapshot of room data at booking time"""
    name: str


class BookingCreate(BaseModel):
    """Schema for creating a new booking"""
    room_id: str
    title: str
    division: Optional[str] = None
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime


class BookingUpdate(BaseModel):
    """Schema for updating an existing booking"""
    room_id: Optional[str] = None
    title: Optional[str] = None
    division: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class BookingResponse(BaseModel):
    """Response schema for booking data"""
    id: str = Field(alias="_id")
    booking_number: str
    user_id: str
    user_snapshot: UserSnapshotResponse
    room_id: str
    room_snapshot: RoomSnapshotResponse
    title: str
    division: Optional[str] = None
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: str
    published: bool
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class ConflictResponse(BaseModel):
    """Response schema when booking conflicts occur"""
    detail: str
    conflicting_booking: Optional[BookingResponse] = None
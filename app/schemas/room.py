from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.room import Room


class RoomCreate(BaseModel):
    """Schema for creating a new room"""
    name: str
    capacity: int
    facilities: List[str] = Field(default_factory=list)
    location: Optional[str] = None


class RoomUpdate(BaseModel):
    """Schema for updating an existing room"""
    name: Optional[str] = None
    capacity: Optional[int] = None
    facilities: Optional[List[str]] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class RoomResponse(BaseModel):
    """Response schema for room data"""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    name: str
    capacity: int
    facilities: List[str]
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    photo_url: Optional[str] = None


def room_to_response(room: Room) -> RoomResponse:
    """Build the API response for a room, including the cache-busted photo URL."""
    photo_url = None
    if room.photo_updated_at is not None:
        version = int(room.photo_updated_at.timestamp())
        photo_url = f"/api/v1/rooms/{room.id}/photo?v={version}"

    return RoomResponse(
        _id=str(room.id),
        name=room.name,
        capacity=room.capacity,
        facilities=room.facilities,
        location=room.location,
        is_active=room.is_active,
        created_at=room.created_at,
        photo_url=photo_url,
    )

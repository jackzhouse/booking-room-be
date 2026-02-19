from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


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
    id: str = Field(alias="_id")
    name: str
    capacity: int
    facilities: List[str]
    location: Optional[str] = None
    is_active: bool
    created_at: datetime
    
    class Config:
        populate_by_name = True
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class TelegramGroupCreate(BaseModel):
    """Schema for creating a new Telegram group"""
    group_id: int
    group_name: str = None  # Can be None if using auto-fetch from Telegram


class TelegramGroupUpdate(BaseModel):
    """Schema for updating a Telegram group"""
    group_name: Optional[str] = None
    is_active: Optional[bool] = None


class TelegramGroupResponse(BaseModel):
    """Response schema for Telegram group data"""
    id: str = Field(alias="_id")
    group_id: int
    group_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True


class TelegramGroupListResponse(BaseModel):
    """Response schema for list of Telegram groups"""
    groups: List[TelegramGroupResponse]
    total: int
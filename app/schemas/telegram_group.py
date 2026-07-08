from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class TelegramGroupCreate(BaseModel):
    """Schema for creating a new Telegram group"""
    group_id: int
    group_name: Optional[str] = None  # Can be None if using auto-fetch from Telegram


class TelegramGroupUpdate(BaseModel):
    """Schema for updating a Telegram group"""
    group_name: Optional[str] = None
    is_active: Optional[bool] = None


class TelegramGroupResponse(BaseModel):
    """Response schema for Telegram group data"""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    group_id: int
    group_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
class TelegramGroupListResponse(BaseModel):
    """Response schema for list of Telegram groups"""
    groups: List[TelegramGroupResponse]
    total: int

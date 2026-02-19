from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class SettingResponse(BaseModel):
    """Response schema for settings"""
    id: str = Field(alias="_id")
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    
    class Config:
        populate_by_name = True


class SettingUpdate(BaseModel):
    """Schema for updating a setting"""
    value: str
    description: Optional[str] = None
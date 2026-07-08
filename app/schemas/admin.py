from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from bson import ObjectId


class SettingResponse(BaseModel):
    """Response schema for settings"""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    key: str
    value: str
    description: Optional[str] = None
    updated_at: datetime
    updated_by: Optional[str] = None
    
class SettingUpdate(BaseModel):
    """Schema for updating a setting"""
    value: str
    description: Optional[str] = None

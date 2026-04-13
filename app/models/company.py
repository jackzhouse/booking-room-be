"""
Company model for organization/company data.
"""
from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field


class Company(Document):
    """Company/Organization model."""
    
    name: str = Field(..., description="Company name")
    initial: str = Field(..., description="Company initial abbreviation")
    is_active: bool = Field(default=True, description="Whether company is active")
    
    # Audit fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None  # ObjectId as string
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None  # ObjectId as string
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    class Settings:
        name = "companies"
        indexes = [
            "initial",
            "is_active",
            "is_deleted"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "name": "PT Teknologi Kartu Indonesia",
                "initial": "TKI",
                "is_active": True
            }
        }

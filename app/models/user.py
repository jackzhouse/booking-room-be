from datetime import datetime, timezone
from typing import Optional
from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, EmailStr

from app.core.enums import RoleEnum, GenderEnum, UserTypeEnum


class User(Document):
    """User model supporting multiple authentication types: Telegram, External, Internal."""
    
    # Identity fields
    telegram_id: Optional[Indexed(int, unique=True)] = None
    account_id: Optional[PydanticObjectId] = None  # External account ObjectId (e.g., accountId)
    external_user_id: Optional[str] = None
    username: Optional[str] = None
    
    # Profile fields
    full_name: str
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    division: Optional[str] = None
    
    # External app fields
    external_company_id: Optional[str] = None
    external_producer: Optional[str] = None  # e.g., "katalis"
    telegram_username: Optional[str] = None  # For external users
    
    # Access control fields
    role: Optional[RoleEnum] = None  # User role (Admin, Teacher, Student, etc.)
    is_active: bool = True
    user_type: UserTypeEnum = UserTypeEnum.TELEGRAM
    
    # Company association
    company_id: Optional[str] = None  # ObjectId as string (references Company)
    
    # Password for internal users (Teacher, Admin)
    password: Optional[str] = None  # Hashed password
    nip: Optional[str] = None  # Employee ID for teachers
    
    # Audit fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None  # ObjectId as string
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None  # ObjectId as string
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None
    
    # Login tracking
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"
        indexes = [
            "telegram_id",
            "account_id",
            "external_user_id",
            "username",
            "email",
            "is_active",
            "role",
            "company_id",
            "is_deleted",
            "user_type"
        ]
    
    class Config:
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "telegram_id": 123456789,
                "full_name": "Budi Santoso",
                "username": "budisantoso",
                "email": "budi@example.com",
                "avatar_url": "https://...",
                "role": "ROLE_USER",
                "is_active": True,
                "user_type": "TELEGRAM"
            }
        }

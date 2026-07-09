from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from beanie import Document, Indexed
from pydantic import ConfigDict, EmailStr, Field, model_validator


class User(Document):
    """User model for Telegram-authenticated users and external app users"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "telegram_id": 123456789,
                "full_name": "Budi Santoso",
                "username": "budisantoso",
                "avatar_url": "https://...",
                "division": "Engineering",
                "is_admin": False,
                "is_active": True
            }
        },
    )
    
    telegram_id: Optional[Indexed(int, unique=True)] = None  # Unique index for telegram_id, optional for external users
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    division: Optional[str] = None
    email: Optional[EmailStr] = None
    account_id: Optional[str] = None
    company_id: Optional[str] = None
    role: Optional[str] = None
    user_type: Optional[str] = None
    telegram_username: Optional[str] = None  # Telegram username for external users (optional)
    external_user_id: Optional[str] = None  # User ID from external app (e.g., Katalis)
    external_company_id: Optional[str] = None  # Company ID from external app
    external_producer: Optional[str] = None  # External app producer (e.g., "katalis")
    attendance_user_id: Optional[str] = None
    employee_no: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    manager_external_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_by: Optional[ObjectId] = None
    updated_by: Optional[ObjectId] = None
    deleted_by: Optional[ObjectId] = None
    gender: Optional[str] = None
    nip: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False
    is_admin: bool = False
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_login_at: Optional[datetime] = None
    
    class Settings:
        name = "users"
        indexes = [
            "telegram_id",
            "username",
            "is_admin",
            "is_active",
            "external_user_id",  # Index for external users lookup
            "employee_no",
            "department_id"
        ]

    @model_validator(mode="after")
    def apply_legacy_defaults(self):
        if self.role is None:
            self.role = "ROLE_SUPER_ADMIN" if self.is_admin else "ROLE_USER"

        if self.user_type is None:
            if self.telegram_id is not None:
                self.user_type = "TELEGRAM"
            elif self.external_producer:
                self.user_type = str(self.external_producer).upper()
            elif self.external_user_id or self.external_company_id:
                self.user_type = "EXTERNAL"

        return self
    

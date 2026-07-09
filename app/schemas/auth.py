from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from bson import ObjectId


class TelegramLoginRequest(BaseModel):
    """Request schema for Telegram Login Widget authentication"""
    model_config = ConfigDict(extra="allow")

    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str
    
class TelegramMiniAppRequest(BaseModel):
    """Request schema for Telegram Mini App authentication"""
    model_config = ConfigDict(extra="allow")

    init_data: str  # URL-encoded initData from Telegram


class UserResponse(BaseModel):
    """Response schema for user data"""
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    telegram_id: Optional[int] = None  # Optional for external users
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    division: Optional[str] = None
    email: Optional[str] = None
    account_id: Optional[str] = None
    company_id: Optional[str] = None
    role: Optional[str] = None
    user_type: Optional[str] = None
    telegram_username: Optional[str] = None  # Telegram username for external users
    external_user_id: Optional[str] = None  # User ID from external app
    external_company_id: Optional[str] = None  # Company ID from external app
    external_producer: Optional[str] = None  # External app producer
    attendance_user_id: Optional[str] = None
    employee_no: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
    manager_external_id: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    gender: Optional[str] = None
    nip: Optional[str] = None
    phone: Optional[str] = None
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False
    is_admin: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    @field_validator("id", "created_by", "updated_by", "deleted_by", mode="before")
    @classmethod
    def normalize_object_id(cls, value: Any) -> Any:
        if value is None:
            return value
        return str(value)

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
    
class TokenResponse(BaseModel):
    """Response schema for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SSOLoginRequest(BaseModel):
    """Request schema for exchanging external token into app auth."""
    model_config = ConfigDict(extra="allow")

    external_token: Optional[str] = None


class UserCreate(BaseModel):
    """Schema for creating/updating user profile"""
    full_name: Optional[str] = None
    division: Optional[str] = None
    email: Optional[str] = None


class AuthCodeGenerateRequest(BaseModel):
    """Request schema for generating auth code"""
    model_config = ConfigDict(extra="allow")

    telegram_user_id: Optional[int] = Field(None, description="Telegram user ID to authorize the code for (optional for web users)")


class AuthCodeData(BaseModel):
    """Inner data schema for auth code generation"""
    code: str
    expires_at: datetime
    expires_in: int  # Seconds until expiration


class AuthCodeResponse(BaseModel):
    """Response schema for auth code generation"""
    success: bool
    data: AuthCodeData


class AuthCodeUserData(BaseModel):
    """User data for verified auth code"""
    id: str
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    photo_url: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True

class AuthCodeVerifyData(BaseModel):
    """Data schema for auth code verification"""
    status: str  # "pending", "verified", or "expired"
    expires_at: Optional[datetime] = None
    expires_in: Optional[int] = None
    user: Optional[AuthCodeUserData] = None
    token: Optional[str] = None

class AuthCodeVerifyResponse(BaseModel):
    """Response schema for auth code verification"""
    success: bool
    data: AuthCodeVerifyData
    error: Optional[Dict[str, str]] = None


# External App Integration Schemas

class ExternalTokenVerifyRequest(BaseModel):
    """Request schema for verifying external app token"""
    model_config = ConfigDict(extra="allow")

    token: str


class ExternalTokenVerifyResponse(BaseModel):
    """Response schema for external token verification"""
    success: bool
    registered: bool
    user: Optional[UserResponse] = None
    user_id: Optional[str] = None
    company_id: Optional[str] = None


class ExternalRegisterRequest(BaseModel):
    """Request schema for registering external user"""
    model_config = ConfigDict(extra="allow")

    token: str
    full_name: str
    division: str
    email: str
    telegram_username: Optional[str] = None
class ExternalRegisterResponse(BaseModel):
    """Response schema for external user registration"""
    success: bool
    message: str
    user: UserResponse

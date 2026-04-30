from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from bson import ObjectId

from app.core.enums import RoleEnum, GenderEnum, UserTypeEnum


class TelegramLoginRequest(BaseModel):
    """Request schema for Telegram Login Widget authentication"""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: int
    hash: str
    
    class Config:
        extra = "allow"  # Allow extra fields from Telegram


class TelegramMiniAppRequest(BaseModel):
    """Request schema for Telegram Mini App authentication"""
    init_data: str  # URL-encoded initData from Telegram
    
    class Config:
        extra = "allow"


class UserResponse(BaseModel):
    """Response schema for user data"""
    id: str = Field(alias="_id")
    telegram_id: Optional[int] = None
    account_id: Optional[str] = Field(default=None, serialization_alias="accountId")
    external_user_id: Optional[str] = None
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    division: Optional[str] = None
    telegram_username: Optional[str] = None
    external_company_id: Optional[str] = None
    external_producer: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: bool = True
    user_type: UserTypeEnum = UserTypeEnum.TELEGRAM
    company_id: Optional[str] = None
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class TokenResponse(BaseModel):
    """Response schema for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    login_source: str
    user: UserResponse


class UserCreate(BaseModel):
    """Schema for creating/updating user profile"""
    full_name: Optional[str] = None
    division: Optional[str] = None
    email: Optional[str] = None


class AuthCodeGenerateRequest(BaseModel):
    """Request schema for generating auth code"""
    telegram_user_id: Optional[int] = Field(None, description="Telegram user ID to authorize the code for (optional for web users)")
    
    class Config:
        extra = "allow"


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
    is_admin: bool = Field(default=False, serialization_alias="isAdmin")
    is_active: bool = True

    class Config:
        populate_by_name = True

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
    """Request schema for verifying external user data"""
    account_id: str = Field(alias="accountId")
    
    class Config:
        extra = "allow"
        populate_by_name = True


class ExternalTokenVerifyResponse(BaseModel):
    """Response schema for external token verification"""
    success: bool
    registered: bool
    user: Optional[UserResponse] = None
    user_id: Optional[str] = None
    company_id: Optional[str] = None


class ExternalRegisterRequest(BaseModel):
    """Request schema for registering external user"""
    account_id: str = Field(alias="accountId")
    full_name: str = Field(alias="fullName")
    division: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None
    telegram_username: Optional[str] = Field(default=None)
    company_id: Optional[str] = Field(default=None)
    producer: Optional[str] = None
    role: Optional[str] = None
    roles: Optional[List[str]] = None
    user_id: Optional[str] = Field(default=None)
    
    class Config:
        extra = "allow"
        populate_by_name = True


class ExternalRegisterResponse(BaseModel):
    """Response schema for external user registration"""
    success: bool
    message: str
    user: UserResponse


# ===== Teacher/Admin User Schemas =====

class TokenLoginRequest(BaseModel):
    """Request schema for external user-data login"""
    account_id: str = Field(alias="accountId")
    full_name: Optional[str] = Field(default=None)
    username: Optional[str] = None
    email: Optional[str] = None
    division: Optional[str] = None
    telegram_username: Optional[str] = Field(default=None)
    company_id: Optional[str] = Field(default=None)
    producer: Optional[str] = None
    role: Optional[str] = None
    roles: Optional[List[str]] = None
    user_id: Optional[str] = Field(default=None)

    class Config:
        extra = "allow"
        populate_by_name = True


class TokenData(BaseModel):
    """Token data structure"""
    producer: str = "Booking Room"
    user_id: str = None
    username: str = None
    full_name: str = None
    role: Optional[RoleEnum] = None
    company_id: Optional[str] = None
    exp: Optional[int] = None


class TokenResponseLogin(BaseModel):
    """Response schema for login"""
    access_token: str
    token_type: str = "bearer"
    login_source: str
    user: UserResponse
    expires_in: int  # Seconds


class TeacherCreateRequest(BaseModel):
    """Request schema for creating teacher"""
    full_name: str
    username: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    nip: Optional[str] = None
    
    class Config:
        extra = "allow"


class AdminCreateRequest(BaseModel):
    """Request schema for creating admin"""
    full_name: str
    username: str
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    role: RoleEnum = RoleEnum.ADMIN
    
    class Config:
        extra = "allow"


class UserUpdateRequest(BaseModel):
    """Request schema for updating user profile"""
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    gender: Optional[GenderEnum] = None
    division: Optional[str] = None
    avatar_url: Optional[str] = None
    telegram_username: Optional[str] = Field(default=None)

    class Config:
        populate_by_name = True


class PasswordChangeRequest(BaseModel):
    """Request schema for changing password"""
    old_password: str
    new_password: str
    confirm_password: str


# ===== Company Schemas =====

class CompanyResponse(BaseModel):
    """Response schema for company data"""
    id: str = Field(alias="_id")
    name: str
    initial: str
    is_active: bool
    created_at: datetime
    
    class Config:
        populate_by_name = True


class CompanyCreateRequest(BaseModel):
    """Request schema for creating company"""
    name: str
    initial: str
    is_active: bool = True

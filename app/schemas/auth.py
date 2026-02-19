from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


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
    telegram_id: int
    full_name: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    division: Optional[str] = None
    email: Optional[str] = None
    is_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        populate_by_name = True


class TokenResponse(BaseModel):
    """Response schema for successful authentication"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserCreate(BaseModel):
    """Schema for creating/updating user profile"""
    full_name: Optional[str] = None
    division: Optional[str] = None
    email: Optional[str] = None


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

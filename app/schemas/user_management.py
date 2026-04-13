from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from app.core.enums import RoleEnum


class UserManagementResponse(BaseModel):
    """Response schema for user in user management"""
    id: str
    telegram_id: Optional[int] = None
    full_name: str
    username: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: bool
    avatar: Optional[str] = None  # Mapped from avatar_url
    created_at: datetime


class UserListResponse(BaseModel):
    """Response schema for user list"""
    users: List[UserManagementResponse]
    total: int


class UpdateAdminRequest(BaseModel):
    """Request schema for updating role"""
    role: RoleEnum


class UpdateStatusRequest(BaseModel):
    """Request schema for updating active status"""
    is_active: bool


class UpdateAvatarRequest(BaseModel):
    """Request schema for updating user avatar"""
    avatar: str


class SuccessResponse(BaseModel):
    """Generic success response wrapper"""
    success: bool = True
    data: dict


class ErrorDetail(BaseModel):
    """Error detail schema"""
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: ErrorDetail

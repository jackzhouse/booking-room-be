from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class UserManagementResponse(BaseModel):
    """Response schema for user in user management"""
    id: str
    telegram_id: int
    full_name: str
    username: Optional[str] = None
    is_admin: bool
    is_active: bool
    avatar: Optional[str] = None  # Mapped from avatar_url
    created_at: datetime


class UserListResponse(BaseModel):
    """Response schema for user list"""
    users: List[UserManagementResponse]
    total: int


class UpdateAdminRequest(BaseModel):
    """Request schema for updating admin role"""
    is_admin: bool


class UpdateStatusRequest(BaseModel):
    """Request schema for updating active status"""
    is_active: bool


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
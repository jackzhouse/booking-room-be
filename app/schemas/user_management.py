from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any


class UserManagementResponse(BaseModel):
    """Response schema for user in user management"""
    id: str
    telegram_id: Optional[int] = None
    full_name: str
    username: Optional[str] = None
    account_id: Optional[str] = None
    company_id: Optional[str] = None
    role: Optional[str] = None
    user_type: Optional[str] = None
    external_user_id: Optional[str] = None
    external_company_id: Optional[str] = None
    external_producer: Optional[str] = None
    employee_no: Optional[str] = None
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    job_title: Optional[str] = None
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
    avatar: Optional[str] = None  # Mapped from avatar_url
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


class SyncTaskResponse(BaseModel):
    task_id: str
    task_type: str
    status: str
    progress: int
    message: str
    metadata: dict = Field(default_factory=dict)

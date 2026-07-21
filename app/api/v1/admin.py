from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.models.booking import Booking
from app.models.user import User
from app.models.room import Room
from app.models.setting import Setting
from app.models.sync_task import SyncTask
from app.models.external_division import ExternalDivision
from app.schemas.admin import SettingResponse, SettingUpdate
from app.schemas.dashboard import DashboardStats
from app.schemas.user_management import (
    UserManagementResponse,
    UserListResponse,
    UpdateAdminRequest,
    UpdateStatusRequest,
    UpdateAvatarRequest,
    UpdateUserRequest,
    SuccessResponse,
    ErrorResponse,
    SyncTaskResponse
)
from app.services.booking_service import cancel_booking
from app.services.dashboard_service import get_dashboard_statistics
from app.services.scheduler_service import get_pending_cleanup_count, get_recent_ended_bookings
from app.core.config import settings
from app.api.deps import get_current_admin_user, security
from app.schemas.booking import BookingResponse
from app.schemas.room import RoomResponse
from app.schemas.auth import UserResponse
from app.services.telegram_service import test_notification
from app.services.katalis_service import (
    ExternalAuthError,
    extract_external_user_id,
    get_display_name,
    katalis_service,
    now_utc,
    populate_user_from_employee,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def convert_booking_to_response(booking: Booking) -> BookingResponse:
    """
    Convert a Booking model to BookingResponse by converting ObjectId fields to strings.
    """
    booking_dict = booking.model_dump(by_alias=True)
    # Convert ObjectId fields to strings
    if "_id" in booking_dict and booking_dict["_id"] is not None:
        booking_dict["_id"] = str(booking_dict["_id"])
    if "user_id" in booking_dict and booking_dict["user_id"] is not None:
        booking_dict["user_id"] = str(booking_dict["user_id"])
    if "room_id" in booking_dict and booking_dict["room_id"] is not None:
        booking_dict["room_id"] = str(booking_dict["room_id"])
    if "cancelled_by" in booking_dict and booking_dict["cancelled_by"] is not None:
        booking_dict["cancelled_by"] = str(booking_dict["cancelled_by"])
    return BookingResponse(**booking_dict)


def convert_room_to_response(room: Room) -> RoomResponse:
    """
    Convert a Room model to RoomResponse by converting ObjectId fields to strings.
    """
    room_dict = room.model_dump(by_alias=True)
    if "_id" in room_dict and room_dict["_id"] is not None:
        room_dict["_id"] = str(room_dict["_id"])
    return RoomResponse(**room_dict)


def convert_user_to_response(user: User) -> UserResponse:
    """
    Convert a User model to UserResponse by converting ObjectId fields to strings.
    """
    user_dict = user.model_dump(by_alias=True)
    if "_id" in user_dict and user_dict["_id"] is not None:
        user_dict["_id"] = str(user_dict["_id"])
    return UserResponse(**user_dict)


def convert_user_to_management_response(user: User) -> UserManagementResponse:
    """
    Convert a User model to UserManagementResponse with proper field mapping.
    Maps avatar_url to avatar and preserves legacy user fields.
    """
    user_dict = user.model_dump(by_alias=True)
    return UserManagementResponse(
        id=str(user_dict.get("_id", "")),
        telegram_id=user_dict.get("telegram_id"),
        full_name=user_dict.get("full_name", ""),
        username=user_dict.get("username"),
        division=user_dict.get("division"),
        email=user_dict.get("email"),
        telegram_username=user_dict.get("telegram_username"),
        account_id=user_dict.get("account_id"),
        company_id=user_dict.get("company_id"),
        role=user_dict.get("role"),
        user_type=user_dict.get("user_type"),
        external_user_id=user_dict.get("external_user_id"),
        external_company_id=user_dict.get("external_company_id"),
        external_producer=user_dict.get("external_producer"),
        employee_no=user_dict.get("employee_no"),
        department_id=user_dict.get("department_id"),
        department_name=user_dict.get("department_name"),
        job_title=user_dict.get("job_title"),
        created_by=user_dict.get("created_by"),
        updated_by=user_dict.get("updated_by"),
        deleted_by=user_dict.get("deleted_by"),
        gender=user_dict.get("gender"),
        nip=user_dict.get("nip"),
        phone=user_dict.get("phone"),
        deleted_at=user_dict.get("deleted_at"),
        is_deleted=user_dict.get("is_deleted", False),
        is_admin=user_dict.get("is_admin", False),
        is_active=user_dict.get("is_active", True),
        avatar=user_dict.get("avatar_url"),  # Map avatar_url to avatar
        created_at=user_dict.get("created_at", datetime.now(timezone.utc)),
        updated_at=user_dict.get("updated_at"),
        last_synced_at=user_dict.get("last_synced_at"),
        last_login_at=user_dict.get("last_login_at"),
    )


def convert_task_to_response(task: SyncTask) -> SyncTaskResponse:
    return SyncTaskResponse(
        task_id=str(task.id),
        task_type=task.task_type,
        status=task.status,
        progress=task.progress,
        message=task.message,
        metadata=task.metadata,
    )

async def sync_external_divisions(token: str) -> int:
    divisions = await katalis_service.fetch_divisions(token)
    synced = 0

    for division in divisions:
        external_id = division.get("id") or division.get("_id")
        if not external_id:
            continue

        existing = await ExternalDivision.find_one(ExternalDivision.external_id == str(external_id))
        if not existing:
            existing = ExternalDivision(external_id=str(external_id), name=division.get("name") or "-")

        existing.name = division.get("name") or existing.name
        existing.description = division.get("description")
        existing.company_id = division.get("companyId") or division.get("company_id")
        existing.last_synced_at = now_utc()
        await existing.save()
        synced += 1

    return synced


async def sync_external_employees(token: str) -> int:
    employees = await katalis_service.fetch_employees(token)
    synced = 0

    for employee in employees:
        external_user_id = extract_external_user_id(employee)
        if not external_user_id:
            continue

        existing = await User.find_one(User.external_user_id == external_user_id)
        if not existing:
            existing = User(
                telegram_id=None,
                full_name=get_display_name(employee),
                external_user_id=external_user_id,
                is_admin=False,
                is_active=True,
            )
        populate_user_from_employee(existing, employee, allow_active_update=True)
        await existing.save()
        synced += 1

    return synced


async def run_employee_sync(task_id: str, token: str):
    task = await SyncTask.get(task_id)
    if not task:
        return

    try:
        task.status = "processing"
        task.progress = 10
        task.message = "Sinkronisasi divisi"
        task.updated_at = now_utc()
        await task.save()

        division_count = await sync_external_divisions(token)

        task.progress = 45
        task.message = "Sinkronisasi employee"
        task.metadata = {**task.metadata, "division_count": division_count}
        task.updated_at = now_utc()
        await task.save()

        employee_count = await sync_external_employees(token)

        task.status = "completed"
        task.progress = 100
        task.message = "Sinkronisasi employee selesai"
        task.metadata = {**task.metadata, "division_count": division_count, "employee_count": employee_count}
        task.completed_at = now_utc()
        task.updated_at = now_utc()
        await task.save()
    except ExternalAuthError as exc:
        task.status = "failed"
        task.progress = 100
        task.message = "Sinkronisasi employee gagal"
        task.metadata = {
            **task.metadata,
            "error_type": "ExternalAuthError",
            "endpoint": exc.endpoint,
            "status_code": exc.status_code,
        }
        task.completed_at = now_utc()
        task.updated_at = now_utc()
        await task.save()
    except Exception as exc:
        task.status = "failed"
        task.progress = 100
        task.message = "Sinkronisasi employee gagal"
        task.metadata = {**task.metadata, "error_type": exc.__class__.__name__}
        task.completed_at = now_utc()
        task.updated_at = now_utc()
        await task.save()


@router.get("/bookings", response_model=List[BookingResponse])
async def get_all_bookings(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all bookings from all users (Admin only).
    """
    bookings = await Booking.find().sort(-Booking.created_at).to_list()
    return [convert_booking_to_response(booking) for booking in bookings]


@router.delete("/bookings/{booking_id}", response_model=BookingResponse)
async def admin_cancel_booking(
    booking_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Cancel any booking (Admin only).
    """
    try:
        booking = await cancel_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            is_admin=True
        )
        
        return convert_booking_to_response(booking)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/rooms", response_model=List[RoomResponse])
async def get_all_rooms(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all rooms including inactive ones (Admin only).
    """
    rooms = await Room.find().sort(Room.name).to_list()
    return [convert_room_to_response(room) for room in rooms]


@router.get("/users", response_model=UserListResponse)
async def get_all_users(
    role: Optional[str] = Query("all", description="Filter by role: 'all' or 'admin'"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all registered users (Admin only).
    
    Query Parameters:
    - role: Filter users by role ('all' for all users, 'admin' for admin users only)
    """
    try:
        # Build query based on role filter
        if role == "admin":
            users = await User.find(User.is_admin == True).sort(-User.created_at).to_list()
        else:  # role == "all" or any other value
            users = await User.find().sort(-User.created_at).to_list()
        
        # Convert users to management response format
        user_responses = [convert_user_to_management_response(user) for user in users]
        
        return UserListResponse(users=user_responses, total=len(user_responses))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users"
        )


@router.post("/users/sync-employees", response_model=SyncTaskResponse)
async def start_employee_sync(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Start employee synchronization from external Katalis/Absensi source.
    """
    task = SyncTask(
        metadata={
            "requested_by": str(current_user.id),
            "requested_by_name": current_user.full_name,
            "requested_by_role": "admin" if current_user.is_admin else "user",
        }
    )
    await task.insert()

    background_tasks.add_task(run_employee_sync, str(task.id), credentials.credentials)
    return convert_task_to_response(task)


@router.get("/tasks/{task_id}", response_model=SyncTaskResponse)
async def get_sync_task(
    task_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get employee sync task progress.
    """
    task = await SyncTask.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    return convert_task_to_response(task)


@router.patch("/users/{user_id}/admin")
async def toggle_user_admin_role(
    user_id: str,
    request: UpdateAdminRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Toggle user admin role (Admin only).
    
    Updates the is_admin field for a specific user.
    """
    try:
        # Find user by ID
        user = await User.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update admin role
        user.is_admin = request.is_admin
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        
        # Return success response
        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user admin role"
        )


@router.patch("/users/{user_id}/status")
async def toggle_user_active_status(
    user_id: str,
    request: UpdateStatusRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Toggle user active status (Admin only).
    
    Updates the is_active field for a specific user.
    """
    try:
        # Find user by ID
        user = await User.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update active status
        user.is_active = request.is_active
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        
        # Return success response
        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )


@router.patch("/users/{user_id}/avatar")
async def update_user_avatar(
    user_id: str,
    request: UpdateAvatarRequest,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update user avatar (Admin only).
    
    Updates the avatar_url field for a specific user.
    """
    try:
        # Find user by ID
        user = await User.get(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update avatar
        user.avatar_url = request.avatar
        user.updated_at = datetime.now(timezone.utc)
        await user.save()
        
        # Return success response
        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.model_dump())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user avatar"
        )


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_admin_user),
):
    """Update admin-editable profile fields for a user (Admin only)."""
    try:
        user = await User.get(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user fields supplied",
            )

        for field, value in update_data.items():
            setattr(user, field, value)
        user.updated_by = current_user.id
        user.updated_at = datetime.now(timezone.utc)
        await user.save()

        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.model_dump())
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.get("/settings/group-ids")
async def get_group_ids(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get default group IDs for consumption and verification (Admin only).
    
    Returns:
        - default_consumption_group_id: Default Telegram group ID for consumption notifications
        - default_verification_group_id: Default Telegram group ID for verification and cleanup notifications
    """
    consumption_setting = await Setting.find_one(Setting.key == "default_consumption_group_id")
    verification_setting = await Setting.find_one(Setting.key == "default_verification_group_id")
    
    return {
        "default_consumption_group_id": int(consumption_setting.value) if consumption_setting and consumption_setting.value else None,
        "default_verification_group_id": int(verification_setting.value) if verification_setting and verification_setting.value else None
    }


class GroupIdsUpdate(BaseModel):
    """Schema for updating default group IDs"""
    default_consumption_group_id: Optional[int] = None
    default_verification_group_id: Optional[int] = None


@router.put("/settings/group-ids")
async def update_group_ids(
    data: GroupIdsUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update default group IDs for consumption and verification (Admin only).
    
    Args:
        - default_consumption_group_id: New default Telegram group ID for consumption notifications
        - default_verification_group_id: New default Telegram group ID for verification and cleanup notifications
    """
    # Update consumption group ID if provided
    if data.default_consumption_group_id is not None:
        consumption_setting = await Setting.find_one(Setting.key == "default_consumption_group_id")
        if consumption_setting:
            consumption_setting.value = str(data.default_consumption_group_id)
            consumption_setting.updated_by = current_user.id
            await consumption_setting.save()
        else:
            new_setting = Setting(
                key="default_consumption_group_id",
                value=str(data.default_consumption_group_id),
                description="ID grup Telegram default untuk notifikasi konsumsi",
                updated_by=current_user.id
            )
            await new_setting.insert()
    
    # Update verification group ID if provided
    if data.default_verification_group_id is not None:
        verification_setting = await Setting.find_one(Setting.key == "default_verification_group_id")
        if verification_setting:
            verification_setting.value = str(data.default_verification_group_id)
            verification_setting.updated_by = current_user.id
            await verification_setting.save()
        else:
            new_setting = Setting(
                key="default_verification_group_id",
                value=str(data.default_verification_group_id),
                description="ID grup Telegram default untuk notifikasi verifikasi dan perapian",
                updated_by=current_user.id
            )
            await new_setting.insert()
    
    return {
        "message": "Group IDs updated successfully",
        "default_consumption_group_id": data.default_consumption_group_id,
        "default_verification_group_id": data.default_verification_group_id
    }


@router.get("/settings", response_model=List[SettingResponse])
async def get_all_settings(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all application settings (Admin only).
    """
    settings_list = await Setting.find().sort(Setting.key).to_list()
    result = []
    for setting in settings_list:
        setting_dict = setting.model_dump(by_alias=True)
        if "_id" in setting_dict and setting_dict["_id"] is not None:
            setting_dict["_id"] = str(setting_dict["_id"])
        if "updated_by" in setting_dict and setting_dict["updated_by"] is not None:
            setting_dict["updated_by"] = str(setting_dict["updated_by"])
        result.append(SettingResponse(**setting_dict))
    return result


@router.get("/settings/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get a specific setting by key (Admin only).
    """
    setting = await Setting.find_one(Setting.key == key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    # Convert ObjectId fields to strings for response
    setting_dict = setting.model_dump(by_alias=True)
    if "_id" in setting_dict and setting_dict["_id"] is not None:
        setting_dict["_id"] = str(setting_dict["_id"])
    if "updated_by" in setting_dict and setting_dict["updated_by"] is not None:
        setting_dict["updated_by"] = str(setting_dict["updated_by"])
    
    return SettingResponse(**setting_dict)


@router.put("/settings/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    setting_data: SettingUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update a setting (Admin only).
    """
    setting = await Setting.find_one(Setting.key == key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting not found"
        )
    
    # Update fields
    if setting_data.value is not None:
        setting.value = setting_data.value
    if setting_data.description is not None:
        setting.description = setting_data.description
    
    setting.updated_by = current_user.id
    await setting.save()
    
    # Convert ObjectId fields to strings for response
    setting_dict = setting.model_dump(by_alias=True)
    if "_id" in setting_dict and setting_dict["_id"] is not None:
        setting_dict["_id"] = str(setting_dict["_id"])
    if "updated_by" in setting_dict and setting_dict["updated_by"] is not None:
        setting_dict["updated_by"] = str(setting_dict["updated_by"])
    
    return SettingResponse(**setting_dict)


@router.post("/settings/test-notification")
async def test_telegram_notification(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Send a test notification to the Telegram group (Admin only).
    """
    success = await test_notification()
    
    if success:
        return {"message": "Test notification sent successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification. Check bot configuration."
        )


@router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get dashboard statistics (Admin only).
    
    Returns:
        - bookings_today: Total bookings today (all statuses)
        - bookings_this_week: Total bookings this week (all statuses)
        - active_bookings_today: Active (non-cancelled) bookings today
        - active_bookings_this_week: Active bookings this week
        - total_rooms: Total rooms (active + inactive)
        - active_rooms: Active rooms only
        - total_users: Total users (active + inactive)
        - active_users: Active users only
    """
    stats = await get_dashboard_statistics()
    return DashboardStats(**stats)


@router.get("/scheduler/status")
async def get_scheduler_status(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of bookings to show"),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get scheduler status and pending cleanup notifications (Admin only).
    
    Returns:
        - pending_count: Number of bookings needing cleanup notification
        - recent_ended: List of recently ended bookings (pending or notified)
    """
    try:
        # Get pending cleanup count
        pending_count = await get_pending_cleanup_count()
        
        # Get recent ended bookings (both pending and notified)
        recent_ended = await get_recent_ended_bookings(limit=limit)
        
        # Convert bookings to response format
        bookings_data = []
        for booking in recent_ended:
            booking_dict = booking.model_dump(by_alias=True)
            if "_id" in booking_dict and booking_dict["_id"] is not None:
                booking_dict["_id"] = str(booking_dict["_id"])
            if "user_id" in booking_dict and booking_dict["user_id"] is not None:
                booking_dict["user_id"] = str(booking_dict["user_id"])
            if "room_id" in booking_dict and booking_dict["room_id"] is not None:
                booking_dict["room_id"] = str(booking_dict["room_id"])
            if "cancelled_by" in booking_dict and booking_dict["cancelled_by"] is not None:
                booking_dict["cancelled_by"] = str(booking_dict["cancelled_by"])
            
            # Skip ended_minutes_ago calculation for now to avoid timezone issues
            booking_dict["ended_minutes_ago"] = None
            
            bookings_data.append(booking_dict)
        
        return {
            "pending_count": pending_count,
            "recent_ended": bookings_data,
            "scheduler_info": {
                "runs_every_minutes": 5,
                "status": "active"
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting scheduler status: {str(e)}"
        )

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.models.booking import Booking
from app.models.user import User
from app.models.room import Room
from app.models.setting import Setting
from app.schemas.admin import SettingResponse, SettingUpdate
from app.schemas.dashboard import DashboardStats
from app.schemas.user_management import (
    UserManagementResponse,
    UserListResponse,
    UpdateAdminRequest,
    UpdateStatusRequest,
    SuccessResponse,
    ErrorResponse
)
from app.services.booking_service import cancel_booking
from app.services.dashboard_service import get_dashboard_statistics
from app.api.deps import get_current_admin_user
from app.schemas.booking import BookingResponse
from app.schemas.room import RoomResponse
from app.schemas.auth import UserResponse
from app.services.telegram_service import test_notification
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])


def convert_booking_to_response(booking: Booking) -> BookingResponse:
    """
    Convert a Booking model to BookingResponse by converting ObjectId fields to strings.
    """
    booking_dict = booking.dict(by_alias=True)
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
    room_dict = room.dict(by_alias=True)
    if "_id" in room_dict and room_dict["_id"] is not None:
        room_dict["_id"] = str(room_dict["_id"])
    return RoomResponse(**room_dict)


def convert_user_to_response(user: User) -> UserResponse:
    """
    Convert a User model to UserResponse by converting ObjectId fields to strings.
    """
    user_dict = user.dict(by_alias=True)
    if "_id" in user_dict and user_dict["_id"] is not None:
        user_dict["_id"] = str(user_dict["_id"])
    return UserResponse(**user_dict)


def convert_user_to_management_response(user: User) -> UserManagementResponse:
    """
    Convert a User model to UserManagementResponse with proper field mapping.
    Maps avatar_url to avatar.
    """
    user_dict = user.dict(by_alias=True)
    return UserManagementResponse(
        id=str(user_dict.get("_id", "")),
        telegram_id=user_dict.get("telegram_id", 0),
        full_name=user_dict.get("full_name", ""),
        username=user_dict.get("username"),
        is_admin=user_dict.get("is_admin", False),
        is_active=user_dict.get("is_active", True),
        avatar=user_dict.get("avatar_url"),  # Map avatar_url to avatar
        created_at=user_dict.get("created_at", datetime.utcnow())
    )


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
        user.updated_at = datetime.utcnow()
        await user.save()
        
        # Return success response
        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.dict())
        
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
        user.updated_at = datetime.utcnow()
        await user.save()
        
        # Return success response
        user_response = convert_user_to_management_response(user)
        return SuccessResponse(success=True, data=user_response.dict())
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )


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
        setting_dict = setting.dict(by_alias=True)
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
    setting_dict = setting.dict(by_alias=True)
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
    setting_dict = setting.dict(by_alias=True)
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

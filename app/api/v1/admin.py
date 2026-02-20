from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.booking import Booking
from app.models.user import User
from app.models.room import Room
from app.models.setting import Setting
from app.schemas.admin import SettingResponse, SettingUpdate
from app.services.booking_service import cancel_booking
from app.api.deps import get_current_admin_user
from app.schemas.booking import BookingResponse
from app.schemas.room import RoomResponse
from app.schemas.auth import UserResponse
from app.services.telegram_service import test_notification

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


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_admin_user)
):
    """
    Get all registered users (Admin only).
    """
    users = await User.find().sort(-User.created_at).to_list()
    return [convert_user_to_response(user) for user in users]


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


@router.patch("/settings/{key}", response_model=SettingResponse)
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
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.models.booking import Booking
from app.schemas.booking import (
    BookingCreate,
    BookingUpdate,
    BookingResponse
)
from app.services.booking_service import (
    create_booking,
    publish_booking,
    update_booking,
    cancel_booking,
    get_user_bookings
)
from app.api.deps import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/bookings", tags=["bookings"])


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


@router.get("/my", response_model=List[BookingResponse])
async def get_my_bookings(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all bookings for the current user (alias for /bookings).
    Optionally filter by status (active/cancelled).
    """
    bookings = await get_user_bookings(current_user.id, status)
    return [convert_booking_to_response(booking) for booking in bookings]


@router.get("", response_model=List[BookingResponse])
async def get_bookings(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all bookings for the current user.
    Optionally filter by status (active/cancelled).
    """
    bookings = await get_user_bookings(current_user.id, status)
    return [convert_booking_to_response(booking) for booking in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
async def get_booking(
    booking_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific booking.
    User can only view their own bookings.
    """
    try:
        # Convert string ID to ObjectId
        obj_id = ObjectId(booking_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID format"
        )
    
    booking = await Booking.get(obj_id)
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )
    
    # Check ownership or admin
    if booking.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this booking"
        )
    
    return convert_booking_to_response(booking)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_new_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new booking.
    
    Validation rules:
    - Must be within operating hours (08:00-18:00) unless admin
    - Minimum duration: 15 minutes unless admin
    - No conflicts with existing bookings in the same room
    """
    try:
        booking = await create_booking(
            user_id=current_user.id,
            room_id=booking_data.room_id,
            title=booking_data.title,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            division=booking_data.division,
            description=booking_data.description,
            is_admin=current_user.is_admin
        )
        
        return convert_booking_to_response(booking)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{booking_id}/publish", response_model=BookingResponse)
async def publish_existing_booking(
    booking_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Publish a draft booking and send notification to Telegram group.
    
    Only booking owner or admin can publish.
    """
    try:
        booking = await publish_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            is_admin=current_user.is_admin
        )
        
        return convert_booking_to_response(booking)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.patch("/{booking_id}", response_model=BookingResponse)
async def update_existing_booking(
    booking_id: str,
    booking_data: BookingUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an existing booking.
    
    Only the booking owner or admin can update.
    Same validation rules as creating a booking apply.
    """
    try:
        booking = await update_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            room_id=booking_data.room_id,
            title=booking_data.title,
            division=booking_data.division,
            description=booking_data.description,
            start_time=booking_data.start_time,
            end_time=booking_data.end_time,
            is_admin=current_user.is_admin
        )
        
        return convert_booking_to_response(booking)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{booking_id}", response_model=BookingResponse)
async def cancel_existing_booking(
    booking_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancel a booking.
    
    Only the booking owner or admin can cancel.
    """
    try:
        booking = await cancel_booking(
            booking_id=booking_id,
            user_id=current_user.id,
            is_admin=current_user.is_admin
        )
        
        return convert_booking_to_response(booking)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
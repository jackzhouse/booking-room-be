from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from bson import ObjectId

from app.models.room import Room
from app.models.booking import Booking
from app.schemas.room import RoomResponse, RoomCreate, RoomUpdate
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=List[RoomResponse])
async def get_rooms(
    active_only: bool = Query(True, description="Filter only active rooms"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of all rooms.
    By default returns only active rooms.
    """
    query = {}
    if active_only:
        query["is_active"] = True
    
    rooms = await Room.find(query).sort(Room.name).to_list()
    return [RoomResponse(
        _id=str(room.id),
        name=room.name,
        capacity=room.capacity,
        facilities=room.facilities,
        location=room.location,
        is_active=room.is_active,
        created_at=room.created_at
    ) for room in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific room.
    """
    room = await Room.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    return RoomResponse(
        _id=str(room.id),
        name=room.name,
        capacity=room.capacity,
        facilities=room.facilities,
        location=room.location,
        is_active=room.is_active,
        created_at=room.created_at
    )


@router.get("/{room_id}/schedule", response_model=List[dict])
async def get_room_schedule(
    room_id: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get schedule for a specific room within a date range.
    
    If end_date is not provided, defaults to start_date.
    """
    # Verify room exists
    room = await Room.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Set end_date to start_date if not provided
    if end_date is None:
        end_date = start_date
    
    # Create datetime range
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    # Query bookings for this room within date range
    bookings = await Booking.find({
        "room_id": ObjectId(room_id),
        "status": "active",
        "start_time": {"$gte": start_datetime, "$lte": end_datetime}
    }).sort(Booking.start_time).to_list()
    
    # Format response
    schedule = []
    for booking in bookings:
        schedule.append({
            "id": str(booking.id),
            "booking_number": booking.booking_number,
            "title": booking.title,
            "user_name": booking.user_snapshot.full_name,
            "division": booking.user_snapshot.division,
            "start_time": booking.start_time.isoformat(),
            "end_time": booking.end_time.isoformat()
        })
    
    return schedule


# Admin endpoints for room management

@router.post("", response_model=RoomResponse)
async def create_room(
    room_data: RoomCreate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Create a new room (Admin only).
    """
    room = Room(**room_data.dict())
    await room.insert()
    
    return RoomResponse(
        _id=str(room.id),
        name=room.name,
        capacity=room.capacity,
        facilities=room.facilities,
        location=room.location,
        is_active=room.is_active,
        created_at=room.created_at
    )


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: str,
    room_data: RoomUpdate,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Update an existing room (Admin only).
    """
    room = await Room.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Update fields
    update_data = room_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(room, field, value)
    
    await room.save()
    
    return RoomResponse(
        _id=str(room.id),
        name=room.name,
        capacity=room.capacity,
        facilities=room.facilities,
        location=room.location,
        is_active=room.is_active,
        created_at=room.created_at
    )


@router.patch("/{room_id}/toggle")
async def toggle_room_status(
    room_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Toggle room active status (Admin only).
    """
    room = await Room.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    room.is_active = not room.is_active
    await room.save()
    
    return {
        "id": str(room.id),
        "name": room.name,
        "is_active": room.is_active
    }


@router.delete("/{room_id}")
async def delete_room(
    room_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Delete a room (Admin only).
    Note: This will also cancel all active bookings for this room.
    """
    room = await Room.get(room_id)
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    # Cancel all active bookings for this room
    bookings = await Booking.find({
        "room_id": ObjectId(room_id),
        "status": "active"
    }).to_list()
    
    for booking in bookings:
        booking.status = "cancelled"
        await booking.save()
    
    # Delete room
    await room.delete()
    
    return {
        "message": f"Room '{room.name}' deleted successfully",
        "cancelled_bookings": len(bookings)
    }
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status, Query
from bson import ObjectId
import logging

from app.models.room import Room
from app.models.booking import Booking
from app.models.room_photo import RoomPhoto
from app.schemas.room import RoomResponse, RoomCreate, RoomUpdate, room_to_response
from app.api.deps import get_current_active_user, get_current_admin_user
from app.models.user import User

logger = logging.getLogger(__name__)

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
    logger.info(f"GET /rooms called - User: {current_user.id}, active_only: {active_only}")
    query = {}
    if active_only:
        query["is_active"] = True
    
    logger.info(f"Query: {query}")
    rooms = await Room.find(query).sort(Room.name).to_list()
    logger.info(f"Found {len(rooms)} rooms")
    
    result = []
    for room in rooms:
        try:
            response = room_to_response(room)
            result.append(response)
            logger.info(f"Successfully processed room: {room.name} (id: {room.id})")
        except Exception as e:
            logger.error(f"Error processing room {room.name}: {e}")
    
    logger.info(f"Returning {len(result)} rooms")
    return result


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific room.
    """
    logger.info(f"GET /rooms/{room_id} called - User: {current_user.id}")
    
    try:
        room = await Room.get(room_id)
    except Exception as e:
        logger.error(f"Error fetching room {room_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    
    if not room:
        logger.warning(f"Room {room_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    logger.info(f"Successfully retrieved room: {room.name}")
    return room_to_response(room)


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
    logger.info(f"GET /rooms/{room_id}/schedule called - User: {current_user.id}, start_date: {start_date}, end_date: {end_date}")
    
    # Verify room exists
    room = await Room.get(room_id)
    if not room:
        logger.warning(f"Room {room_id} not found for schedule request")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    
    logger.info(f"Found room: {room.name}")
    
    # Set end_date to start_date if not provided
    if end_date is None:
        end_date = start_date
    
    # Create datetime range
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    logger.info(f"Querying schedule from {start_datetime} to {end_datetime}")
    
    # Query bookings for this room within date range (only published bookings)
    bookings = await Booking.find({
        "room_id": ObjectId(room_id),
        "status": "active",
        "published": True,
        "start_time": {"$gte": start_datetime, "$lte": end_datetime}
    }).sort(Booking.start_time).to_list()
    
    logger.info(f"Found {len(bookings)} bookings")
    
    # Format response
    schedule = []
    for booking in bookings:
        try:
            schedule.append({
                "id": str(booking.id),
                "booking_number": booking.booking_number,
                "title": booking.title,
                "user_name": booking.user_snapshot.full_name,
                "division": booking.user_snapshot.division,
                "start_time": booking.start_time.isoformat(),
                "end_time": booking.end_time.isoformat()
            })
        except Exception as e:
            logger.error(f"Error processing booking {booking.id}: {e}")
    
    logger.info(f"Returning {len(schedule)} schedule items")
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
    room = Room(**room_data.model_dump())
    await room.insert()
    
    return room_to_response(room)


@router.put("/{room_id}", response_model=RoomResponse)
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
    update_data = room_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(room, field, value)
    
    await room.save()
    
    return room_to_response(room)


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
    await RoomPhoto.find(RoomPhoto.room_id == room.id).delete()
    await room.delete()
    
    return {
        "message": f"Room '{room.name}' deleted successfully",
        "cancelled_bookings": len(bookings)
    }


MAX_PHOTO_BYTES = 2 * 1024 * 1024


def _detect_image_type(data: bytes) -> Optional[str]:
    """Identify the image from its leading bytes; the client's Content-Type is not trusted."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _get_room_or_404(room_id: str) -> Room:
    try:
        room = await Room.get(room_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid room ID format"
        )
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room not found"
        )
    return room


@router.get("/{room_id}/photo")
async def get_room_photo(room_id: str):
    """
    Serve a room photo. Public so it can be used as an <img> source, which cannot send
    the bearer token. The URL carries a version query, so browsers may cache it for long.
    """
    try:
        photo = await RoomPhoto.find_one(RoomPhoto.room_id == ObjectId(room_id))
    except Exception:
        photo = None
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Room photo not found"
        )

    return Response(
        content=photo.data,
        media_type=photo.content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.post("/{room_id}/photo", response_model=RoomResponse)
async def upload_room_photo(
    room_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload or replace a room photo (Admin only). JPEG, PNG or WebP, up to 2 MB.
    """
    room = await _get_room_or_404(room_id)

    data = await file.read(MAX_PHOTO_BYTES + 1)
    if len(data) > MAX_PHOTO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Ukuran foto maksimal 2 MB"
        )
    content_type = _detect_image_type(data)
    if content_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Format foto harus JPEG, PNG, atau WebP"
        )

    now = datetime.utcnow()
    photo = await RoomPhoto.find_one(RoomPhoto.room_id == room.id)
    if photo:
        photo.content_type = content_type
        photo.data = data
        photo.updated_at = now
        await photo.save()
    else:
        await RoomPhoto(room_id=room.id, content_type=content_type, data=data, updated_at=now).insert()

    room.photo_updated_at = now
    await room.save()
    return room_to_response(room)


@router.delete("/{room_id}/photo", response_model=RoomResponse)
async def delete_room_photo(
    room_id: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    Remove a room photo (Admin only).
    """
    room = await _get_room_or_404(room_id)

    await RoomPhoto.find(RoomPhoto.room_id == room.id).delete()
    room.photo_updated_at = None
    await room.save()
    return room_to_response(room)

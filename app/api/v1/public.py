"""Read-only endpoints that need no login: the room page opened from a room's QR code."""
from datetime import date, timezone
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.core.timezone import local_day_bounds_utc
from app.models.booking import Booking
from app.models.room import Room
from app.schemas.room import room_to_response

router = APIRouter(prefix="/public", tags=["public"])

# Shown instead of the title for a draft, which is not announced to anyone yet.
DRAFT_TITLE = "Terisi"


class PublicRoomResponse(BaseModel):
    id: str
    name: str
    capacity: int
    location: Optional[str] = None
    facilities: List[str]
    photo_url: Optional[str] = None


class PublicScheduleSlot(BaseModel):
    start_time: str
    end_time: str
    title: str
    division: Optional[str] = None


async def _get_active_room(room_id: str) -> Room:
    """The room, or 404 for an unknown id, a malformed id and an inactive room alike."""
    try:
        object_id = ObjectId(room_id)
    except (InvalidId, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    room = await Room.get(object_id)
    if not room or not room.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


def _utc_iso(value) -> str:
    """ISO-8601 with an explicit UTC marker; stored datetimes come back naive."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/rooms/{room_id}", response_model=PublicRoomResponse)
async def get_public_room(room_id: str):
    """Room details for the page a room's QR code opens. No login."""
    room = room_to_response(await _get_active_room(room_id))
    return PublicRoomResponse(
        id=room.id,
        name=room.name,
        capacity=room.capacity,
        location=room.location,
        facilities=room.facilities,
        photo_url=room.photo_url,
    )


@router.get("/rooms/{room_id}/schedule", response_model=List[PublicScheduleSlot])
async def get_public_room_schedule(
    room_id: str,
    day: date = Query(..., alias="date", description="Day to show (YYYY-MM-DD, Asia/Jakarta)"),
):
    """
    Bookings of one room on one day. No login.

    Only time, title and division are returned. A draft keeps blocking its slot
    but shows "Terisi" instead of its title.
    """
    room = await _get_active_room(room_id)
    start, end = local_day_bounds_utc(day)

    bookings = await Booking.find({
        "room_id": room.id,
        "status": "active",
        "start_time": {"$lt": end},
        "end_time": {"$gt": start},
    }).sort(Booking.start_time).to_list()

    return [
        PublicScheduleSlot(
            start_time=_utc_iso(booking.start_time),
            end_time=_utc_iso(booking.end_time),
            title=booking.title if booking.published else DRAFT_TITLE,
            division=booking.user_snapshot.division,
        )
        for booking in bookings
    ]

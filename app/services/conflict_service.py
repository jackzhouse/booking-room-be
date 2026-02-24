from datetime import datetime, time
from typing import Optional, Tuple
from bson import ObjectId
from app.models.booking import Booking
from app.models.setting import Setting
from app.core.config import settings


async def get_operating_hours() -> Tuple[time, time]:
    """
    Get operating hours from settings.
    Returns (start_time, end_time) as time objects.
    """
    start_setting = await Setting.find_one(Setting.key == "operating_hours_start")
    end_setting = await Setting.find_one(Setting.key == "operating_hours_end")
    
    start_hour, start_minute = map(int, start_setting.value.split(":")) if start_setting else (8, 0)
    end_hour, end_minute = map(int, end_setting.value.split(":")) if end_setting else (18, 0)
    
    return time(start_hour, start_minute), time(end_hour, end_minute)


async def validate_operating_hours(
    start_time: datetime,
    end_time: datetime,
    is_admin: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate if booking time is within operating hours.
    Admins bypass this validation.
    
    Returns:
        (is_valid, error_message)
    """
    if is_admin:
        return True, None
    
    try:
        start_hour, end_hour = await get_operating_hours()
        
        # Extract time component from datetime (convert to UTC+7 for display)
        booking_start = start_time.astimezone(settings.timezone).time()
        booking_end = end_time.astimezone(settings.timezone).time()
        
        # Check if within operating hours
        if booking_start < start_hour or booking_end > end_hour:
            return False, (
                f"Jam operasional: {start_hour.strftime('%H:%M')} - {end_hour.strftime('%H:%M')}. "
                f"Booking Anda: {booking_start.strftime('%H:%M')} - {booking_end.strftime('%H:%M')}"
            )
        
        return True, None
        
    except Exception as e:
        print(f"Error validating operating hours: {e}")
        # If settings not found, allow booking but log error
        return True, None


async def validate_booking_duration(
    start_time: datetime,
    end_time: datetime,
    is_admin: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Validate if booking duration is at least 15 minutes.
    Admins bypass this validation.
    
    Returns:
        (is_valid, error_message)
    """
    if is_admin:
        return True, None
    
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    if duration_minutes < 15:
        return False, f"Durasi minimal booking adalah 15 menit. Anda memilih {int(duration_minutes)} menit."
    
    return True, None


async def check_booking_conflict(
    room_id: ObjectId,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[ObjectId] = None
) -> Tuple[bool, Optional[Booking]]:
    """
    Check if a booking conflicts with existing bookings in the same room.
    
    Conflict condition:
    - Same room
    - Status is "active"
    - Time overlap: (existing.start < new.end) AND (existing.end > new.start)
    
    Args:
        room_id: ID of the room to check
        start_time: Proposed booking start time
        end_time: Proposed booking end time
        exclude_booking_id: If provided, exclude this booking from conflict check (for updates)
    
    Returns:
        (has_conflict, conflicting_booking)
    """
    # Build base query
    query = {
        "room_id": room_id,
        "status": "active",
        # Time overlap logic
        "start_time": {"$lt": end_time},
        "end_time": {"$gt": start_time}
    }
    
    # Exclude current booking when updating
    if exclude_booking_id:
        query["_id"] = {"$ne": exclude_booking_id}
    
    # Find conflicting booking
    conflicting_booking = await Booking.find_one(query)
    
    return (conflicting_booking is not None), conflicting_booking


async def format_conflict_message(conflicting_booking: Booking) -> str:
    """
    Format a user-friendly conflict message.
    """
    user_name = conflicting_booking.user_snapshot.full_name
    division = conflicting_booking.user_snapshot.division or ""
    room_name = conflicting_booking.room_snapshot.name
    
    # Convert to UTC+7 for display in error message
    start_time_jkt = conflicting_booking.start_time.astimezone(settings.timezone)
    end_time_jkt = conflicting_booking.end_time.astimezone(settings.timezone)
    
    start_str = start_time_jkt.strftime("%H:%M")
    end_str = end_time_jkt.strftime("%H:%M")
    
    message = (
        f"Ruangan sudah dibooking oleh {user_name}"
    )
    
    if division:
        message += f" ({division})"
    
    message += f" pukul {start_str}–{end_str} WIB di {room_name}"
    
    return message

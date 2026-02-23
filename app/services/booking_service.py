from datetime import datetime
from typing import Optional, List
import re
from bson import ObjectId
from beanie import PydanticObjectId

from app.models.booking import Booking, UserSnapshot, RoomSnapshot
from app.models.booking_history import BookingHistory, HistoryData
from app.models.room import Room
from app.models.setting import Setting
from app.models.user import User
from app.services.conflict_service import (
    check_booking_conflict,
    validate_operating_hours,
    validate_booking_duration,
    format_conflict_message
)
from app.services.telegram_service import (
    get_telegram_group,
    notify_new_booking,
    notify_booking_updated,
    notify_booking_cancelled,
    notify_consumption_group,
    notify_verification_group_booking,
    notify_verification_group_cleanup
)
from app.core.config import settings


def format_text_with_links(text: Optional[str]) -> Optional[str]:
    """
    Format text with proper capitalization while preserving URLs in lowercase.
    
    Args:
        text: The text to format
        
    Returns:
        Formatted text with URLs in lowercase
    """
    if not text:
        return text
    
    # Pattern to match URLs (http, https, www) - case insensitive
    url_pattern = r'(?i)(https?://[^\s]+|www\.[^\s]+)'
    
    # Find all URLs and their positions
    urls = []
    def collect_urls(match):
        urls.append(match.group(0))
        return f"__URL_{len(urls)-1}__"
    
    # Replace URLs with placeholders
    text_with_placeholders = re.sub(url_pattern, collect_urls, text)
    
    # Split text into words and capitalize each word that's not a placeholder
    words = text_with_placeholders.split()
    formatted_words = []
    for word in words:
        if word.startswith("__URL_") and word.endswith("__"):
            # Keep placeholder as-is
            formatted_words.append(word)
        else:
            # Capitalize the word
            formatted_words.append(word.title())
    
    formatted_text = " ".join(formatted_words)
    
    # Replace placeholders with original URLs in lowercase
    for i, url in enumerate(urls):
        formatted_text = formatted_text.replace(f"__URL_{i}__", url.lower())
    
    return formatted_text


async def generate_booking_number() -> str:
    """
    Generate a unique booking number in format BK-XXXXX.
    Uses atomic increment in MongoDB settings.
    """
    # Use findOneAndUpdate to atomically increment counter
    setting = await Setting.find_one(Setting.key == "booking_counter")
    
    if not setting:
        # Initialize counter if not exists
        setting = Setting(
            key="booking_counter",
            value="1",
            description="Counter untuk generate booking number"
        )
        await setting.insert()
        counter = 1
    else:
        # Increment counter
        counter = int(setting.value) + 1
        setting.value = str(counter)
        await setting.save()
    
    # Format as BK-XXXXX (zero-padded 5 digits)
    return f"BK-{counter:05d}"


async def create_booking(
    user_id: ObjectId,
    room_id: str,
    telegram_group_id: int,
    title: str,
    start_time: datetime,
    end_time: datetime,
    division: Optional[str] = None,
    description: Optional[str] = None,
    has_consumption: bool = False,
    consumption_note: Optional[str] = None,
    consumption_group_id: Optional[int] = None,
    verification_group_id: Optional[int] = None,
    is_admin: bool = False
) -> Booking:
    """
    Create a new booking with validation.
    
    Raises:
        ValueError: If validation fails
        Exception: If room not found or other errors occur
    """
    # Get room
    room = await Room.get(room_id)
    if not room:
        raise ValueError("Ruangan tidak ditemukan")
    
    if not room.is_active:
        raise ValueError("Ruangan tidak aktif")
    
    # Get user for snapshot
    user = await User.get(user_id)
    if not user:
        raise ValueError("User tidak ditemukan")
    
    # Validate telegram_group_id
    telegram_group = await get_telegram_group(telegram_group_id)
    if not telegram_group:
        raise ValueError("Grup Telegram tidak ditemukan atau tidak aktif")
    
    # Validate operating hours (non-admin only)
    is_valid, error_msg = await validate_operating_hours(start_time, end_time, is_admin)
    if not is_valid:
        raise ValueError(error_msg)
    
    # Validate booking duration (non-admin only)
    is_valid, error_msg = await validate_booking_duration(start_time, end_time, is_admin)
    if not is_valid:
        raise ValueError(error_msg)
    
    # Capitalize title and format description (preserving URLs in lowercase)
    title = title.title() if title else title
    description = format_text_with_links(description)
    
    # Check for conflicts
    has_conflict, conflicting_booking = await check_booking_conflict(
        ObjectId(room_id),
        start_time,
        end_time
    )
    
    if has_conflict:
        error_msg = await format_conflict_message(conflicting_booking)
        raise ValueError(error_msg)
    
    # Handle consumption and verification group IDs
    # Use defaults from settings if not provided
    final_consumption_group_id = consumption_group_id
    final_verification_group_id = verification_group_id
    
    # Get default consumption group from settings if not provided and has consumption
    if has_consumption and not final_consumption_group_id:
        setting = await Setting.find_one(Setting.key == "default_consumption_group_id")
        if setting:
            try:
                final_consumption_group_id = int(setting.value)
            except (ValueError, TypeError):
                final_consumption_group_id = None
    
    # Get default verification group from settings if not provided
    if not final_verification_group_id:
        setting = await Setting.find_one(Setting.key == "default_verification_group_id")
        if setting:
            try:
                final_verification_group_id = int(setting.value)
            except (ValueError, TypeError):
                final_verification_group_id = None
    
    # Generate booking number
    booking_number = await generate_booking_number()
    
    # Create booking (as draft)
    booking = Booking(
        booking_number=booking_number,
        user_id=user_id,
        user_snapshot=UserSnapshot(
            full_name=user.full_name,
            username=user.username,
            division=user.division,
            telegram_id=user.telegram_id
        ),
        room_id=ObjectId(room_id),
        room_snapshot=RoomSnapshot(name=room.name),
        telegram_group_id=telegram_group_id,  # Store as snapshot
        title=title,
        division=division,
        description=description,
        start_time=start_time,
        end_time=end_time,
        status="active",
        published=False,  # Start as draft
        has_consumption=has_consumption,
        consumption_note=consumption_note,
        consumption_group_id=final_consumption_group_id,
        verification_group_id=final_verification_group_id
    )
    
    await booking.insert()
    
    # Create history record
    await create_history(
        booking_id=booking.id,
        booking_number=booking_number,
        changed_by=user_id,
        action="created",
        new_data=HistoryData(
            room_snapshot={"name": room.name},
            start_time=start_time,
            end_time=end_time,
            title=title,
            description=description,
            division=division
        )
    )
    
    # Note: No notification sent yet (booking is draft)
    # User must call publish_booking() to publish and send notification
    
    return booking


async def publish_booking(
    booking_id: str,
    user_id: ObjectId,
    is_admin: bool = False
) -> Booking:
    """
    Publish a draft booking and send notification to Telegram group.
    
    Raises:
        ValueError: If booking not found or no permission
    """
    # Convert booking_id string to ObjectId
    try:
        booking_obj_id = ObjectId(booking_id)
    except Exception:
        raise ValueError("Invalid booking ID format")
    
    # Get existing booking
    booking = await Booking.get(booking_obj_id)
    if not booking:
        raise ValueError("Booking tidak ditemukan")
    
    if booking.status != "active":
        raise ValueError("Booking sudah dibatalkan")
    
    if booking.published:
        raise ValueError("Booking sudah dipublish")
    
    # Check ownership or admin
    if booking.user_id != user_id and not is_admin:
        raise ValueError("Anda tidak memiliki akses untuk mempublish booking ini")
    
    # Mark as published
    booking.published = True
    booking.updated_at = datetime.now(settings.timezone)
    await booking.save()
    
    # Create history record
    await create_history(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        changed_by=user_id,
        action="published",
        new_data=HistoryData(
            room_snapshot={"name": booking.room_snapshot.name},
            start_time=booking.start_time,
            end_time=booking.end_time,
            title=booking.title,
            description=booking.description,
            division=booking.division
        )
    )
    
    # Send multi-group notifications
    
    # 1. Always send to selected group (existing behavior)
    await notify_new_booking(booking)
    
    # 2. Always send to verification group (if configured)
    if booking.verification_group_id:
        await notify_verification_group_booking(booking)
    
    # 3. Send to consumption group if has consumption (if configured)
    if booking.has_consumption and booking.consumption_group_id:
        await notify_consumption_group(booking)
    
    return booking


async def update_booking(
    booking_id: str,
    user_id: ObjectId,
    room_id: Optional[str] = None,
    title: Optional[str] = None,
    division: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    is_admin: bool = False
) -> Booking:
    """
    Update an existing booking with validation.
    
    Raises:
        ValueError: If validation fails or booking not found
    """
    # Convert booking_id string to ObjectId
    try:
        booking_obj_id = ObjectId(booking_id)
    except Exception:
        raise ValueError("Invalid booking ID format")
    
    # Get existing booking
    booking = await Booking.get(booking_obj_id)
    if not booking:
        raise ValueError("Booking tidak ditemukan")
    
    if booking.status != "active":
        raise ValueError("Booking sudah dibatalkan")
    
    # Store old data for history
    old_data = HistoryData(
        room_snapshot={"name": booking.room_snapshot.name},
        start_time=booking.start_time,
        end_time=booking.end_time,
        title=booking.title,
        description=booking.description,
        division=booking.division
    )
    
    # Check ownership or admin
    if booking.user_id != user_id and not is_admin:
        raise ValueError("Anda tidak memiliki akses untuk mengubah booking ini")
    
    # Get user info for admin check
    user = await User.get(user_id)
    
    # Track if room changed
    room_id_obj = booking.room_id
    room_name = booking.room_snapshot.name
    
    if room_id:
        room = await Room.get(room_id)
        if not room:
            raise ValueError("Ruangan tidak ditemukan")
        if not room.is_active:
            raise ValueError("Ruangan tidak aktif")
        
        room_id_obj = ObjectId(room_id)
        room_name = room.name
    
    # Update fields
    update_data = {}
    
    if title is not None:
        update_data["title"] = title.title() if title else title
    
    if division is not None:
        update_data["division"] = division
    
    if description is not None:
        update_data["description"] = format_text_with_links(description)
    
    if room_id is not None:
        update_data["room_id"] = room_id_obj
        update_data["room_snapshot"] = RoomSnapshot(name=room_name)
    
    # Time validation if times are being updated
    if start_time or end_time:
        new_start = start_time if start_time else booking.start_time
        new_end = end_time if end_time else booking.end_time
        
        # Validate operating hours (non-admin only)
        is_valid, error_msg = await validate_operating_hours(new_start, new_end, user.is_admin if user else is_admin)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Validate booking duration (non-admin only)
        is_valid, error_msg = await validate_booking_duration(new_start, new_end, user.is_admin if user else is_admin)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Check for conflicts
        has_conflict, conflicting_booking = await check_booking_conflict(
            room_id_obj,
            new_start,
            new_end,
            exclude_booking_id=booking.id
        )
        
        if has_conflict:
            error_msg = await format_conflict_message(conflicting_booking)
            raise ValueError(error_msg)
        
        update_data["start_time"] = new_start
        update_data["end_time"] = new_end
    
    # Apply updates
    for field, value in update_data.items():
        setattr(booking, field, value)
    
    booking.updated_at = datetime.now(settings.timezone)
    await booking.save()
    
    # Create history record
    await create_history(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        changed_by=user_id,
        action="updated",
        old_data=old_data,
        new_data=HistoryData(
            room_snapshot={"name": booking.room_snapshot.name},
            start_time=booking.start_time,
            end_time=booking.end_time,
            title=booking.title,
            description=booking.description,
            division=booking.division
        )
    )
    
    # Send notification
    await notify_booking_updated(booking, old_data.dict())
    
    return booking


async def cancel_booking(
    booking_id: str,
    user_id: ObjectId,
    is_admin: bool = False
) -> Booking:
    """
    Cancel a booking.
    
    Raises:
        ValueError: If booking not found or no permission
    """
    # Convert booking_id string to ObjectId
    try:
        booking_obj_id = ObjectId(booking_id)
    except Exception:
        raise ValueError("Invalid booking ID format")
    
    # Get existing booking
    booking = await Booking.get(booking_obj_id)
    if not booking:
        raise ValueError("Booking tidak ditemukan")
    
    if booking.status != "active":
        raise ValueError("Booking sudah dibatalkan")
    
    # Check ownership or admin
    if booking.user_id != user_id and not is_admin:
        raise ValueError("Anda tidak memiliki akses untuk membatalkan booking ini")
    
    # Cancel booking
    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(settings.timezone)
    booking.cancelled_by = user_id
    booking.updated_at = datetime.now(settings.timezone)
    await booking.save()
    
    # Create history record
    await create_history(
        booking_id=booking.id,
        booking_number=booking.booking_number,
        changed_by=user_id,
        action="cancelled",
        old_data=HistoryData(
            room_snapshot={"name": booking.room_snapshot.name},
            start_time=booking.start_time,
            end_time=booking.end_time,
            title=booking.title
        )
    )
    
    # Send notification
    await notify_booking_cancelled(booking)
    
    return booking


async def create_history(
    booking_id: PydanticObjectId,
    booking_number: str,
    changed_by: ObjectId,
    action: str,
    old_data: Optional[HistoryData] = None,
    new_data: Optional[HistoryData] = None
) -> BookingHistory:
    """Create a booking history record."""
    history = BookingHistory(
        booking_id=ObjectId(booking_id),
        booking_number=booking_number,
        changed_by=changed_by,
        action=action,
        old_data=old_data,
        new_data=new_data
    )
    await history.insert()
    return history


async def get_user_bookings(user_id: ObjectId, status: Optional[str] = None) -> List[Booking]:
    """Get all bookings for a user, optionally filtered by status."""
    query = {"user_id": user_id}
    if status:
        query["status"] = status
    
    return await Booking.find(query).sort(-Booking.created_at).to_list()


async def get_booking_by_number(booking_number: str) -> Optional[Booking]:
    """Get a booking by its booking number."""
    return await Booking.find_one(Booking.booking_number == booking_number)
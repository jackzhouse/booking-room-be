from datetime import datetime
from typing import Optional, List, Dict
from telegram import Bot, Chat
from telegram.error import TelegramError

from app.core.config import settings
from app.models.booking import Booking
from app.models.telegram_group import TelegramGroup


bot = Bot(token=settings.BOT_TOKEN)


async def send_telegram_message(chat_id: int, message: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message to a Telegram chat.
    
    Args:
        chat_id: Telegram chat ID (can be negative for groups)
        message: Message content
        parse_mode: Format (Markdown or HTML)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=parse_mode
        )
        return True
    except TelegramError as e:
        print(f"Error sending Telegram message: {e}")
        return False


async def get_telegram_group(group_id: int) -> Optional[TelegramGroup]:
    """
    Get Telegram group by ID.
    
    Args:
        group_id: Telegram group ID
        
    Returns:
        TelegramGroup object if found and active, None otherwise
    """
    group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
    
    if not group:
        print(f"Warning: Telegram group {group_id} not found")
        return None
    
    if not group.is_active:
        print(f"Warning: Telegram group {group_id} is inactive")
        return None
    
    return group


async def get_all_telegram_groups() -> List[TelegramGroup]:
    """
    Get all active Telegram groups.
    
    Returns:
        List of active TelegramGroup objects
    """
    return await TelegramGroup.find(TelegramGroup.is_active == True).to_list()


async def add_telegram_group(group_id: int, group_name: str) -> TelegramGroup:
    """
    Add a new Telegram group.
    
    Args:
        group_id: Telegram group chat ID
        group_name: Human-readable name for display
        
    Returns:
        Created TelegramGroup object
        
    Raises:
        ValueError: If group_id already exists
    """
    # Check if group_id already exists
    existing = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
    if existing:
        raise ValueError(f"Telegram group with ID {group_id} already exists")
    
    group = TelegramGroup(
        group_id=group_id,
        group_name=group_name,
        is_active=True
    )
    await group.insert()
    return group


async def delete_telegram_group(group_id: int) -> bool:
    """
    Delete a Telegram group by ID.
    
    Args:
        group_id: Telegram group chat ID
        
    Returns:
        True if deleted, False if not found
    """
    group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
    if not group:
        return False
    
    await group.delete()
    return True


async def get_telegram_chat_info(chat_id: int) -> Dict[str, any]:
    """
    Get Telegram chat information by chat ID.
    
    This function retrieves chat information from Telegram API including
    the chat name/title, type, and other metadata.
    
    Args:
        chat_id: Telegram chat ID (can be negative for groups)
        
    Returns:
        Dictionary with chat information:
        {
            "group_id": int,
            "group_name": str,
            "group_type": str  (e.g., "group", "supergroup", "channel")
        }
        
    Raises:
        ValueError: If chat not found or bot doesn't have access
        Exception: For other Telegram API errors
    """
    try:
        chat: Chat = await bot.get_chat(chat_id=chat_id)
        
        # Get chat name (title for groups, full_name for private chats)
        chat_name = chat.title
        if not chat_name and chat.full_name:
            chat_name = chat.full_name
        elif not chat_name:
            chat_name = str(chat_id)  # Fallback to ID if no name available
        
        # Determine chat type
        chat_type = chat.type  # "private", "group", "supergroup", "channel"
        
        return {
            "group_id": chat_id,
            "group_name": chat_name,
            "group_type": chat_type
        }
        
    except TelegramError as e:
        error_message = str(e)
        
        # Parse common Telegram errors
        if "chat not found" in error_message.lower():
            raise ValueError("Grup tidak ditemukan. Pastikan bot sudah ditambahkan ke grup ini.")
        elif "bot was blocked" in error_message.lower():
            raise ValueError("Bot diblokir di grup ini.")
        elif "not enough rights" in error_message.lower() or "bot is not a member" in error_message.lower():
            raise ValueError("Bot bukan member dari grup ini atau tidak memiliki akses yang cukup.")
        else:
            raise ValueError(f"Gagal mengambil info grup: {error_message}")


def format_date_indonesian(dt: datetime) -> str:
    """
    Format datetime to Indonesian date format.
    Example: Senin, 24 Feb 2025 | 09:00 – 11:00 WIB
    """
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", 
              "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    
    day_name = days[dt.weekday()]
    day = dt.day
    month = months[dt.month - 1]
    year = dt.year
    time_start = dt.strftime("%H:%M")
    
    return f"{day_name}, {day} {month} {year}"


def format_time_range(start: datetime, end: datetime) -> str:
    """Format time range."""
    return f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')} WIB"


async def notify_new_booking(booking: Booking):
    """
    Send notification for new booking to Telegram group.
    Uses telegram_group_id from booking object.
    """
    # Use telegram_group_id from booking (snapshot)
    group_id = booking.telegram_group_id
    
    # Format username with @ tag if available
    username_display = booking.user_snapshot.username if booking.user_snapshot.username else booking.user_snapshot.full_name
    
    # Format user info
    user_info = f"{booking.user_snapshot.full_name}"
    if booking.user_snapshot.division:
        user_info += f" ({booking.user_snapshot.division})"
    user_info += f" — @{username_display}"
    
    message = (
        f"📍 INFO BOOKING: {booking.room_snapshot.name.upper()}\n\n"
        f"Informasi reservasi untuk hari {format_date_indonesian(booking.start_time)}:\n\n"
        f"◽️ Keperluan: {booking.title}\n"
        f"◽️ Deskripsi: {booking.description if booking.description else '-'}\n"
        f"◽️ Jam: {format_time_range(booking.start_time, booking.end_time)}\n"
        f"◽️ PIC: {user_info}\n\n"
        f"Rekan-rekan yang membutuhkan ruangan pada jam tersebut diharapkan dapat berkoordinasi langsung dengan @{username_display}. Terima kasih."
    )
    
    await send_telegram_message(group_id, message)


async def notify_booking_updated(booking: Booking, old_data: dict):
    """
    Send notification for booking update to Telegram group.
    Uses telegram_group_id from booking object.
    """
    # Use telegram_group_id from booking (snapshot)
    group_id = booking.telegram_group_id
    
    # Format username with @ tag if available
    username_display = booking.user_snapshot.username if booking.user_snapshot.username else booking.user_snapshot.full_name
    
    message = (
        f"📍 UPDATE BOOKING: {booking.room_snapshot.name.upper()}\n"
        f"#{booking.booking_number}\n\n"
        f"Update reservasi:\n\n"
    )
    
    # Check what changed
    has_changes = False
    if old_data.get("title") and old_data["title"] != booking.title:
        message += f"◽️ Keperluan: {old_data['title']} → {booking.title}\n"
        has_changes = True
    
    if old_data.get("description") and old_data["description"] != booking.description:
        old_desc = old_data['description'] if old_data['description'] else '-'
        new_desc = booking.description if booking.description else '-'
        message += f"◽️ Deskripsi: {old_desc} → {new_desc}\n"
        has_changes = True
    
    if old_data.get("room_snapshot") and old_data["room_snapshot"].get("name") != booking.room_snapshot.name:
        message += f"◽️ Ruangan: {old_data['room_snapshot']['name']} → {booking.room_snapshot.name}\n"
        has_changes = True
    
    if old_data.get("start_time") and old_data.get("end_time"):
        new_time = format_time_range(booking.start_time, booking.end_time)
        message += f"◽️ Waktu baru: {new_time}\n"
        has_changes = True
    
    if has_changes:
        message += f"◽️ PIC: @{username_display}\n\n"
        message += f"Mohon perhatikan perubahan jadwal. Terima kasih."
    else:
        message += f"◽️ PIC: @{username_display}"
    
    await send_telegram_message(group_id, message)


async def notify_booking_cancelled(booking: Booking):
    """
    Send notification for booking cancellation to Telegram group.
    Uses telegram_group_id from booking object.
    """
    # Use telegram_group_id from booking (snapshot)
    group_id = booking.telegram_group_id
    
    # Format username with @ tag if available
    username_display = booking.user_snapshot.username if booking.user_snapshot.username else booking.user_snapshot.full_name
    
    message = (
        f"📍 CANCEL BOOKING: {booking.room_snapshot.name.upper()}\n"
        f"#{booking.booking_number}\n\n"
        f"Reservasi telah dibatalkan:\n\n"
        f"◽️ Keperluan: {booking.title}\n"
        f"◽️ Deskripsi: {booking.description if booking.description else '-'}\n"
        f"◽️ Waktu: {format_time_range(booking.start_time, booking.end_time)}\n"
        f"◽️ PIC: @{username_display}\n\n"
        f"Ruangan kini tersedia pada jam tersebut. Terima kasih."
    )
    
    await send_telegram_message(group_id, message)


async def test_notification(group_id: int) -> bool:
    """
    Send a test notification to a specific Telegram group.
    
    Args:
        group_id: Telegram group ID to send test notification to
        
    Returns:
        True if successful, False otherwise
    """
    # Validate that group exists and is active
    group = await get_telegram_group(group_id)
    if not group:
        return False
    
    message = (
        f"✅ *Test Notifikasi*\n\n"
        f"Notifikasi dari Booking Room Backend berhasil!\n"
        f"Grup: {group.group_name}\n"
        f"Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    
    return await send_telegram_message(group_id, message)
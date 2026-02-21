from datetime import datetime
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from app.core.config import settings
from app.models.booking import Booking


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


async def get_telegram_group_id() -> Optional[int]:
    """
    Get the Telegram group ID from settings.
    Returns None if not found or invalid.
    """
    from app.models.setting import Setting
    
    setting = await Setting.find_one(Setting.key == "telegram_group_id")
    
    if not setting:
        print("Warning: telegram_group_id not found in settings")
        return None
    
    try:
        return int(setting.value)
    except (ValueError, TypeError):
        print(f"Warning: Invalid telegram_group_id: {setting.value}")
        return None


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
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return
    
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
        f"◽️ Acara: {booking.title}\n"
        f"◽️ Oleh: {user_info}\n"
        f"◽️ Jam: {format_time_range(booking.start_time, booking.end_time)}\n\n"
        f"Rekan-rekan yang membutuhkan ruangan pada jam tersebut diharapkan dapat berkoordinasi langsung dengan @{username_display}. Terima kasih."
    )
    
    await send_telegram_message(group_id, message)


async def notify_booking_updated(booking: Booking, old_data: dict):
    """
    Send notification for booking update to Telegram group.
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return
    
    # Format username with @ tag if available
    username_display = booking.user_snapshot.username if booking.user_snapshot.username else booking.user_snapshot.full_name
    
    message = (
        f"📍 UPDATE BOOKING: {booking.room_snapshot.name.upper()}\n"
        f"#{booking.booking_number}\n\n"
        f"Update reservasi:\n\n"
    )
    
    # Check what changed
    has_changes = False
    if old_data.get("room_snapshot") and old_data["room_snapshot"].get("name") != booking.room_snapshot.name:
        message += f"◽️ Perubahan: {old_data['room_snapshot']['name']} → {booking.room_snapshot.name}\n"
        has_changes = True
    
    if old_data.get("start_time") and old_data.get("end_time"):
        new_time = format_time_range(booking.start_time, booking.end_time)
        message += f"◽️ Waktu baru: {new_time}\n"
        has_changes = True
    
    if has_changes:
        message += f"◽️ Oleh: @{username_display}\n\n"
        message += f"Mohon perhatikan perubahan jadwal. Terima kasih."
    else:
        message += f"◽️ Oleh: @{username_display}"
    
    await send_telegram_message(group_id, message)


async def notify_booking_cancelled(booking: Booking):
    """
    Send notification for booking cancellation to Telegram group.
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return
    
    # Format username with @ tag if available
    username_display = booking.user_snapshot.username if booking.user_snapshot.username else booking.user_snapshot.full_name
    
    message = (
        f"📍 CANCEL BOOKING: {booking.room_snapshot.name.upper()}\n"
        f"#{booking.booking_number}\n\n"
        f"Reservasi telah dibatalkan:\n\n"
        f"◽️ Acara: {booking.title}\n"
        f"◽️ Oleh: @{username_display}\n"
        f"◽️ Waktu: {format_time_range(booking.start_time, booking.end_time)}\n\n"
        f"Ruangan kini tersedia pada jam tersebut. Terima kasih."
    )
    
    await send_telegram_message(group_id, message)


async def test_notification():
    """
    Send a test notification to the Telegram group.
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return False
    
    message = (
        f"✅ *Test Notifikasi*\n\n"
        f"Notifikasi dari Booking Room Backend berhasil!\n"
        f"Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )
    
    return await send_telegram_message(group_id, message)
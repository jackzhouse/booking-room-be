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
    
    message = (
        f"📅 *Booking Baru*\n\n"
        f"👤 Nama      : {booking.user_snapshot.full_name}\n"
    )
    
    if booking.user_snapshot.division:
        message += f"🏢 Divisi    : {booking.user_snapshot.division}\n"
    
    message += (
        f"🚪 Ruangan   : {booking.room_snapshot.name}\n"
        f"📌 Keperluan : {booking.title}\n"
    )
    
    if booking.description:
        message += f"📝 Deskripsi : {booking.description}\n"
    
    message += (
        f"🕐 Waktu     : {format_date_indonesian(booking.start_time)} | "
        f"{format_time_range(booking.start_time, booking.end_time)}\n\n"
        f"🆔 #{booking.booking_number}"
    )
    
    await send_telegram_message(group_id, message)


async def notify_booking_updated(booking: Booking, old_data: dict):
    """
    Send notification for booking update to Telegram group.
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return
    
    message = (
        f"✏️ *Booking Diubah*\n\n"
        f"👤 Oleh : {booking.user_snapshot.full_name}\n"
        f"🆔 #{booking.booking_number}\n\n"
        f"Perubahan:\n"
    )
    
    # Check what changed
    if old_data.get("room_snapshot") and old_data["room_snapshot"].get("name") != booking.room_snapshot.name:
        message += f"🚪 Ruangan : {old_data['room_snapshot']['name']} → {booking.room_snapshot.name}\n"
    
    if old_data.get("start_time") and old_data.get("end_time"):
        old_time = f"{old_data['start_time'].strftime('%H:%M')}–{old_data['end_time'].strftime('%H:%M')} WIB"
        new_time = format_time_range(booking.start_time, booking.end_time)
        if old_time != new_time:
            message += f"🕐 Waktu   : {old_time} → {new_time}\n"
    
    await send_telegram_message(group_id, message)


async def notify_booking_cancelled(booking: Booking):
    """
    Send notification for booking cancellation to Telegram group.
    """
    group_id = await get_telegram_group_id()
    if not group_id:
        return
    
    message = (
        f"❌ *Booking Dibatalkan*\n\n"
        f"👤 Dibatalkan oleh : {booking.user_snapshot.full_name}\n"
        f"🆔 #{booking.booking_number}\n\n"
        f"Detail yang dibatalkan:\n"
        f"🚪 {booking.room_snapshot.name}\n"
        f"📌 {booking.title}\n"
        f"🕐 {format_date_indonesian(booking.start_time)} | "
        f"{format_time_range(booking.start_time, booking.end_time)}"
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
import logging
from datetime import datetime, timezone
from html import escape
from typing import Optional, List, Dict
from telegram import Bot, Chat
from telegram.error import TelegramError

from app.core.config import settings
from app.models.booking import Booking
from app.models.telegram_group import TelegramGroup


logger = logging.getLogger(__name__)
bot = Bot(token=settings.BOT_TOKEN)


def _display_value(value: object) -> str:
    """Return an HTML-safe notification value with a stable empty fallback."""
    if value is None or value == "":
        return "-"
    return escape(str(value), quote=False)


def _format_pic(booking: Booking) -> str:
    full_name = booking.user_snapshot.full_name or "-"
    username = _get_user_display_name(booking)
    if not username or username == booking.user_snapshot.full_name:
        return full_name
    return f"{full_name} (@{str(username).lstrip('@')})"


def _render_notification(
    title: str,
    fields: list[tuple[str, str, object]],
    action: str,
    booking_number: Optional[str] = None,
    blocks: Optional[list[tuple[str, str, object]]] = None,
) -> str:
    """Render every Telegram notification using one HTML-safe visual structure."""
    header = f"<b>{title}</b>"
    reference = f"\n<code>#{_display_value(booking_number)}</code>" if booking_number else ""
    details = "\n".join(
        f"<b>{label}:</b> {_display_value(value)}"
        for _icon, label, value in fields
    )
    detail_blocks = "\n\n".join(
        f"<b>{label}:</b>\n{_display_value(value)}"
        for _icon, label, value in blocks or []
    )
    body = f"{details}\n\n{detail_blocks}" if detail_blocks else details
    return f"{header}{reference}\n\n{body}\n\n<b>Tindakan:</b>\n{_display_value(action)}"


def _booking_fields(booking: Booking) -> list[tuple[str, str, object]]:
    return [
        ("📍", "Ruang", booking.room_snapshot.name),
        ("📅", "Tanggal", format_date_indonesian(booking.start_time)),
        ("⏰", "Waktu", format_time_range(booking.start_time, booking.end_time)),
        ("👤", "PIC", _format_pic(booking)),
        ("🏢", "Divisi", _get_division_display(booking)),
        ("📝", "Keperluan", booking.title),
    ]


def _booking_description_block(booking: Booking) -> list[tuple[str, str, object]]:
    return [("📄", "Deskripsi", booking.description)]


def _get_user_display_name(booking: Booking) -> str:
    if booking.user_snapshot.external_user_id:
        return booking.user_snapshot.telegram_username or booking.user_snapshot.full_name

    return booking.user_snapshot.username or booking.user_snapshot.full_name


def _get_division_display(booking: Booking) -> str:
    return booking.division or booking.user_snapshot.division or "-"


def _format_consumption_facilities(booking: Booking) -> str:
    facilities = getattr(booking, "consumption_facilities", None) or []
    if not facilities:
        return "-"
    return "\n".join(f"• {facility}" for facility in facilities)


def _format_consumption_note(booking: Booking) -> str:
    """Render each non-empty consumption line as one consistent list item."""
    note = getattr(booking, "consumption_note", None)
    if not note or not str(note).strip():
        return "-"

    items = [line.strip().lstrip("•- ").strip() for line in str(note).splitlines()]
    return "\n".join(f"• {item}" for item in items if item) or "-"


async def send_telegram_message(chat_id: int, message: str, parse_mode: str = "HTML") -> bool:
    """
    Send a message to a Telegram chat.
    
    Args:
        chat_id: Telegram chat ID (can be negative for groups)
        message: Message content
        parse_mode: Telegram parse mode; HTML by default for formatted notifications.
    
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
        logger.warning("Error sending Telegram message to %s: %s", chat_id, e)
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


async def update_telegram_group(
    group_id: int,
    group_name: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Optional[TelegramGroup]:
    """Update mutable Telegram group fields and return the saved group."""
    group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
    if not group:
        return None

    if group_name is not None:
        group.group_name = group_name
    if is_active is not None:
        group.is_active = is_active

    group.updated_at = datetime.now(timezone.utc)
    await group.save()
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
    chat name/title, type, and other metadata.
    
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
    Format datetime to Indonesian date format (UTC → Asia/Jakarta).
    Example: Senin, 24 Feb 2025
    """
    # Convert UTC to Asia/Jakarta if timezone-aware
    if dt.tzinfo is not None:
        dt = dt.astimezone(settings.timezone)
    elif dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(settings.timezone)
    
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", 
              "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    
    day_name = days[dt.weekday()]
    day = dt.day
    month = months[dt.month - 1]
    year = dt.year
    
    return f"{day_name}, {day} {month} {year}"


def format_time_range(start: datetime, end: datetime) -> str:
    """Format time range (UTC → Asia/Jakarta)."""
    # Convert both times to Asia/Jakarta
    for i, dt in enumerate([start, end]):
        if dt.tzinfo is not None:
            dt = dt.astimezone(settings.timezone)
        elif dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(settings.timezone)
        if i == 0:
            start = dt
        else:
            end = dt
    
    return f"{start.strftime('%H:%M')} – {end.strftime('%H:%M')} WIB"


def format_time_indonesian(dt: datetime) -> str:
    """Format one datetime in Asia/Jakarta for notification detail rows."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(settings.timezone)
    else:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(settings.timezone)
    return f"{dt.strftime('%H:%M')} WIB"


async def notify_new_booking(booking: Booking):
    """
    Send notification for new booking to Telegram group.
    Uses telegram_group_id from booking object.
    """
    # Use telegram_group_id from booking (snapshot)
    group_id = booking.telegram_group_id
    
    message = _render_notification(
        "TKI ROOM - BOOKING BARU",
        _booking_fields(booking),
        "Koordinasikan penggunaan ruang dengan PIC.",
        booking.booking_number,
        _booking_description_block(booking),
    )
    
    await send_telegram_message(group_id, message)


def _format_changed_fields(changed_fields: Optional[list[str]]) -> str:
    if not changed_fields:
        return "-"
    return ", ".join(changed_fields)


async def notify_booking_updated(
    booking: Booking,
    old_data: dict,
    chat_id: Optional[int] = None,
    changed_fields: Optional[list[str]] = None,
):
    """
    Send notification for booking update to Telegram group.
    Uses telegram_group_id from booking object.
    """
    group_id = chat_id if chat_id is not None else booking.telegram_group_id
    message = _render_notification(
        "TKI ROOM - PERUBAHAN BOOKING",
        [("🔄", "Perubahan", _format_changed_fields(changed_fields)), *_booking_fields(booking)],
        "Perhatikan perubahan jadwal ini.",
        booking.booking_number,
        _booking_description_block(booking),
    )
    
    await send_telegram_message(group_id, message)


async def notify_booking_target_removed(booking: Booking, chat_id: int, target_label: str):
    """
    Notify an old target group that the booking is no longer routed there.
    """
    message = _render_notification(
        "TKI ROOM - PERUBAHAN TUJUAN NOTIFIKASI",
        [("📨", "Tujuan sebelumnya", target_label), *_booking_fields(booking)],
        "Abaikan referensi lama untuk jadwal ini.",
        booking.booking_number,
        _booking_description_block(booking),
    )

    await send_telegram_message(chat_id, message)


async def notify_booking_cancelled(booking: Booking, chat_id: Optional[int] = None):
    """
    Send notification for booking cancellation to Telegram group.
    Uses telegram_group_id from booking object.
    """
    group_id = chat_id if chat_id is not None else booking.telegram_group_id
    message = _render_notification(
        "TKI ROOM - PEMBATALAN BOOKING",
        _booking_fields(booking),
        "Ruangan kini tersedia pada jam tersebut.",
        booking.booking_number,
        _booking_description_block(booking),
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
    
    message = _render_notification(
        "TKI ROOM - TEST NOTIFIKASI",
        [
            ("👥", "Grup", group.group_name),
            ("🕒", "Waktu", datetime.now(timezone.utc).astimezone(settings.timezone).strftime("%d/%m/%Y %H:%M:%S WIB")),
        ],
        "Notifikasi Booking Room berhasil dikirim.",
    )
    
    return await send_telegram_message(group_id, message)


async def notify_consumption_group(booking: Booking, is_update: bool = False):
    """
    Send notification to consumption group.
    
    Args:
        booking: Booking object with consumption details
        is_update: Whether notification represents a published booking update
    """
    if not booking.consumption_group_id:
        return
    
    title = (
        "TKI ROOM - PERUBAHAN KONSUMSI"
        if is_update
        else "TKI ROOM - PERMINTAAN KONSUMSI"
    )
    message = _render_notification(
        title,
        [
            *_booking_fields(booking),
        ],
        "Siapkan konsumsi sesuai permintaan.",
        booking.booking_number,
        [
            *_booking_description_block(booking),
            ("🏷️", "Fasilitas", _format_consumption_facilities(booking)),
            ("🍴", "Konsumsi", _format_consumption_note(booking)),
        ],
    )
    
    await send_telegram_message(booking.consumption_group_id, message)


async def notify_consumption_group_cancelled(booking: Booking, chat_id: Optional[int] = None):
    """
    Send cancellation notification to consumption group.
    """
    group_id = chat_id if chat_id is not None else booking.consumption_group_id
    if not group_id:
        return

    message = _render_notification(
        "TKI ROOM - PEMBATALAN KONSUMSI",
        _booking_fields(booking),
        "Hentikan persiapan konsumsi bila sudah dijadwalkan.",
        booking.booking_number,
        _booking_description_block(booking),
    )

    await send_telegram_message(group_id, message)


async def notify_verification_group_booking(booking: Booking):
    """
    Send booking notification to verification group (full format).
    
    Args:
        booking: Booking object
    """
    if not booking.verification_group_id:
        return
    
    message = _render_notification(
        "TKI ROOM - BOOKING BARU",
        _booking_fields(booking),
        "Koordinasikan penggunaan ruang dengan PIC.",
        booking.booking_number,
        _booking_description_block(booking),
    )
    
    await send_telegram_message(booking.verification_group_id, message)


async def notify_verification_group_cancelled(booking: Booking):
    """
    Send cancellation notification to verification group.
    """
    if not booking.verification_group_id:
        return

    await notify_booking_cancelled(booking, chat_id=booking.verification_group_id)


async def notify_verification_group_cleanup(booking: Booking):
    """
    Send cleanup notification to verification group after meeting ends.
    
    Args:
        booking: Booking object
    """
    if not booking.verification_group_id:
        return
    
    message = _render_notification(
        "TKI ROOM - MEETING SELESAI",
        [
            ("📍", "Ruang", booking.room_snapshot.name),
            ("📅", "Tanggal", format_date_indonesian(booking.end_time)),
            ("⏰", "Selesai", format_time_indonesian(booking.end_time)),
            ("👤", "PIC", _format_pic(booking)),
            ("🏢", "Divisi", _get_division_display(booking)),
            ("📝", "Keperluan", booking.title),
        ],
        "Rapikan dan bersihkan ruangan setelah penggunaan.",
        booking.booking_number,
    )
    
    await send_telegram_message(booking.verification_group_id, message)

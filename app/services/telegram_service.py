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
BOT_NOTIFICATION_FOOTER = "Pesan otomatis dari Bot Booking Room."


def _display_value(value: object) -> str:
    """Return an HTML-safe notification value with a stable empty fallback."""
    if value is None or value == "":
        return "-"
    return escape(str(value), quote=False)


def _format_pic(booking: Booking) -> str:
    full_name = booking.user_snapshot.full_name or "PIC tidak tersedia"
    username = _get_user_display_name(booking)
    if not username or username == booking.user_snapshot.full_name:
        return full_name
    return f"{full_name} (@{str(username).lstrip('@')})"


def _has_value(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def _render_detail_lines(details: list[tuple[str, object]]) -> str:
    return "\n".join(
        f"<b>{_display_value(label)}:</b> {_display_value(value)}"
        for label, value in details
        if _has_value(value)
    )


def _render_optional_blocks(blocks: list[tuple[str, object]]) -> str:
    return "\n\n".join(
        f"<b>{_display_value(label)}:</b>\n{_display_value(value)}"
        for label, value in blocks
        if _has_value(value)
    )


def _format_notification_date(dt: datetime) -> str:
    """Format a full Indonesian date for durable group notifications."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(settings.timezone)
    else:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(settings.timezone)

    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = [
        "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ]
    return f"{days[dt.weekday()]}, {dt.day} {months[dt.month - 1]} {dt.year}"


def _format_notification_time_range(start: datetime, end: datetime) -> str:
    """Format a group notification time range in Asia/Jakarta."""
    start_time = _to_notification_timezone(start)
    end_time = _to_notification_timezone(end)
    return f"{start_time.strftime('%H.%M')} sampai {end_time.strftime('%H.%M')} WIB"


def _to_notification_timezone(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(settings.timezone)
    return dt.replace(tzinfo=timezone.utc).astimezone(settings.timezone)


def _format_booking_intro(booking: Booking, action: str) -> str:
    division = _get_division_display(booking)
    if division:
        return f"{_format_pic(booking)} dari Divisi {division} {action}"
    return f"{_format_pic(booking)} {action}"


def _render_booking_notification(
    title: str,
    booking: Booking,
    intro: str,
    instruction: str,
    leading_blocks: Optional[list[tuple[str, object]]] = None,
    trailing_blocks: Optional[list[tuple[str, object]]] = None,
    date_value: Optional[str] = None,
    time_value: Optional[str] = None,
) -> str:
    """Render booking notifications as clear, human-readable bot messages."""
    date = date_value or _format_notification_date(booking.start_time)
    time_range = time_value or _format_notification_time_range(
        booking.start_time, booking.end_time
    )
    sections = [
        f"<b>{_display_value(title)}</b>",
        _display_value(intro),
    ]
    leading = _render_optional_blocks(leading_blocks or [])
    if leading:
        sections.append(leading)
    sections.append(
        _render_detail_lines([
            ("Ruang", booking.room_snapshot.name),
            ("Tanggal", date),
            ("Waktu", time_range),
            ("Keperluan", booking.title),
        ])
    )
    description = _render_optional_blocks([("Deskripsi", booking.description)])
    if description:
        sections.append(description)
    trailing = _render_optional_blocks(trailing_blocks or [])
    if trailing:
        sections.append(trailing)
    sections.extend([
        _render_detail_lines([
            ("PIC", _format_pic(booking)),
            ("Booking", f"#{booking.booking_number}"),
        ]),
        _display_value(instruction),
        BOT_NOTIFICATION_FOOTER,
    ])
    return "\n\n".join(sections)


def _render_new_booking_notification(booking: Booking) -> str:
    return _render_booking_notification(
        "Informasi Penggunaan Ruang Meeting",
        booking,
        _format_booking_intro(booking, "telah menjadwalkan penggunaan ruangan:"),
        "Mohon koordinasi dengan PIC bila diperlukan.",
    )


def _get_user_display_name(booking: Booking) -> str:
    if booking.user_snapshot.external_user_id:
        return booking.user_snapshot.telegram_username or booking.user_snapshot.full_name

    return booking.user_snapshot.username or booking.user_snapshot.full_name


def _get_division_display(booking: Booking) -> str:
    return booking.division or booking.user_snapshot.division or ""


def _format_consumption_facilities(booking: Booking) -> str:
    facilities = getattr(booking, "consumption_facilities", None) or []
    if not facilities:
        return ""
    return "\n".join(f"• {facility}" for facility in facilities)


def _format_consumption_note(booking: Booking) -> str:
    """Render each non-empty consumption line as one consistent list item."""
    note = getattr(booking, "consumption_note", None)
    if not note or not str(note).strip():
        return ""

    items = [line.strip().lstrip("•- ").strip() for line in str(note).splitlines()]
    return "\n".join(f"• {item}" for item in items if item)


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
    
    message = _render_new_booking_notification(booking)
    
    await send_telegram_message(group_id, message)


def _format_changed_fields(changed_fields: Optional[list[str]]) -> str:
    if not changed_fields:
        return ""
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
    message = _render_booking_notification(
        "Perubahan Penggunaan Ruang Meeting",
        booking,
        _format_booking_intro(booking, "telah memperbarui jadwal penggunaan ruangan:"),
        "Mohon gunakan jadwal terbaru ini sebagai acuan.",
        leading_blocks=[("Perubahan", _format_changed_fields(changed_fields))],
    )
    
    await send_telegram_message(group_id, message)


async def notify_booking_target_removed(booking: Booking, chat_id: int, target_label: str):
    """
    Notify an old target group that the booking is no longer routed there.
    """
    message = _render_booking_notification(
        "Perubahan Tujuan Notifikasi",
        booking,
        "Booking berikut tidak lagi dikirim ke grup ini:",
        "Silakan abaikan notifikasi sebelumnya dari booking ini.",
        leading_blocks=[("Tujuan sebelumnya", target_label)],
    )

    await send_telegram_message(chat_id, message)


async def notify_booking_cancelled(booking: Booking, chat_id: Optional[int] = None):
    """
    Send notification for booking cancellation to Telegram group.
    Uses telegram_group_id from booking object.
    """
    group_id = chat_id if chat_id is not None else booking.telegram_group_id
    message = _render_booking_notification(
        "Pembatalan Penggunaan Ruang Meeting",
        booking,
        _format_booking_intro(booking, "telah membatalkan penggunaan ruangan berikut:"),
        "Ruangan tersedia kembali pada jadwal tersebut.",
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
    
    sent_at = datetime.now(timezone.utc).astimezone(settings.timezone)
    message = (
        "<b>Test Notifikasi Bot Booking Room</b>\n\n"
        f"<b>Grup:</b> {_display_value(group.group_name)}\n"
        f"<b>Waktu kirim:</b> {_display_value(_format_notification_date(sent_at))}, "
        f"{_display_value(format_time_indonesian(sent_at).replace(':', '.'))}\n\n"
        "<b>Status:</b> Notifikasi berhasil dikirim ke grup ini.\n\n"
        f"{BOT_NOTIFICATION_FOOTER}"
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
        "Perubahan Permintaan Konsumsi"
        if is_update
        else "Permintaan Konsumsi Ruang Meeting"
    )
    intro = _format_booking_intro(
        booking,
        "telah memperbarui kebutuhan konsumsi:"
        if is_update
        else "telah mengajukan kebutuhan konsumsi untuk penggunaan ruangan:",
    )
    message = _render_booking_notification(
        title,
        booking,
        intro,
        "Mohon gunakan detail konsumsi terbaru ini sebagai acuan."
        if is_update
        else "Mohon siapkan konsumsi sesuai permintaan.",
        trailing_blocks=[
            ("Fasilitas", _format_consumption_facilities(booking)),
            ("Konsumsi", _format_consumption_note(booking)),
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

    message = _render_booking_notification(
        "Pembatalan Permintaan Konsumsi",
        booking,
        "Permintaan konsumsi untuk booking berikut telah dibatalkan:",
        "Mohon hentikan persiapan konsumsi untuk booking ini.",
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
    
    message = _render_new_booking_notification(booking)
    
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
    
    message = _render_booking_notification(
        "Penggunaan Ruang Meeting Selesai",
        booking,
        _format_booking_intro(booking, "telah selesai menggunakan ruangan:"),
        "Mohon rapikan dan bersihkan ruangan setelah penggunaan.",
        date_value=_format_notification_date(booking.end_time),
        time_value=f"{_to_notification_timezone(booking.end_time).strftime('%H.%M')} WIB",
    )
    
    await send_telegram_message(booking.verification_group_id, message)

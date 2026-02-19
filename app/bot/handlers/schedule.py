from datetime import datetime, date
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from app.models.user import User
from app.models.room import Room
from app.models.booking import Booking
from app.services.telegram_service import format_date_indonesian, format_time_range


async def schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /schedule command.
    Show schedule for all rooms on a specific date.
    Usage: /schedule [DD-MM-YYYY]
    """
    user = update.effective_user
    
    # Check if user is registered
    db_user = await User.find_one(User.telegram_id == user.id)
    
    if not db_user:
        message = (
            "❌ Kamu belum terdaftar.\n\n"
            "Silakan login dulu di aplikasi web menggunakan akun Telegram kamu."
        )
        await update.message.reply_text(message)
        return
    
    # Parse date argument
    target_date: Optional[date] = None
    
    if context.args:
        # Try to parse date from argument (DD-MM-YYYY)
        try:
            date_str = context.args[0]
            day, month, year = map(int, date_str.split('-'))
            target_date = date(year, month, day)
        except (ValueError, IndexError):
            message = (
                "❌ Format tanggal salah.\n\n"
                "Gunakan format: /schedule DD-MM-YYYY\n"
                "Contoh: /schedule 24-02-2025"
            )
            await update.message.reply_text(message)
            return
    else:
        # Default to today
        target_date = date.today()
    
    # Get date range for query
    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = datetime.combine(target_date, datetime.max.time())
    
    # Get all active rooms
    rooms = await Room.find(Room.is_active == True).sort(Room.name).to_list()
    
    if not rooms:
        message = "❌ Tidak ada ruangan yang aktif saat ini."
        await update.message.reply_text(message)
        return
    
    # Build schedule message
    date_display = format_date_indonesian(start_datetime)
    message = f"📋 *Jadwal Ruangan*\n\n"
    message += f"📅 {date_display}\n\n"
    
    total_bookings = 0
    
    for room in rooms:
        # Get bookings for this room
        bookings = await Booking.find({
            "room_id": room.id,
            "status": "active",
            "start_time": {"$gte": start_datetime, "$lte": end_datetime}
        }).sort(Booking.start_time).to_list()
        
        if bookings:
            message += f"🚪 *{room.name}*\n"
            
            for booking in bookings:
                message += f"  📌 {booking.title}\n"
                message += f"  👤 {booking.user_snapshot.full_name}"
                if booking.user_snapshot.division:
                    message += f" ({booking.user_snapshot.division})"
                message += f"\n"
                message += f"  ⏰ {format_time_range(booking.start_time, booking.end_time)}\n\n"
                
                total_bookings += 1
        else:
            message += f"🚪 *{room.name}*\n"
            message += f"  ✅ Tidak ada booking\n\n"
    
    if total_bookings == 0:
        message += "\n✨ Tidak ada booking pada tanggal ini."
    
    await update.message.reply_text(message, parse_mode="Markdown")
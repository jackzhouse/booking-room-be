from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from app.models.user import User
from app.models.booking import Booking
from app.services.telegram_service import format_date_indonesian, format_time_range


async def mybooking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /mybooking command.
    Show all active bookings for the user.
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
    
    # Get user's active bookings
    bookings = await Booking.find({
        "user_id": db_user.id,
        "status": "active"
    }).sort(Booking.start_time).to_list()
    
    if not bookings:
        message = (
            f"📅 *Booking Aktif*\n\n"
            f"Halo {db_user.full_name}!\n\n"
            "Kamu tidak memiliki booking aktif saat ini.\n\n"
            "Buat booking baru lewat aplikasi web."
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        return
    
    # Format bookings list
    message = f"📅 *Booking Aktif*\n\n"
    message += f"👤 {db_user.full_name}\n"
    if db_user.division:
        message += f"🏢 {db_user.division}\n"
    message += f"\n"
    
    for idx, booking in enumerate(bookings, 1):
        message += f"*{idx}. {booking.booking_number}*\n"
        message += f"🚪 {booking.room_snapshot.name}\n"
        message += f"📌 {booking.title}\n"
        message += f"🕐 {format_date_indonesian(booking.start_time)}\n"
        message += f"⏰ {format_time_range(booking.start_time, booking.end_time)}\n\n"
    
    message += f"Total: {len(bookings)} booking aktif"
    
    await update.message.reply_text(message, parse_mode="Markdown")
from telegram import Update
from telegram.ext import ContextTypes

from app.models.user import User
from app.models.booking import Booking
from app.services.booking_service import cancel_booking
from app.services.telegram_service import format_date_indonesian, format_time_range


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /cancel command.
    Cancel a booking by booking number.
    Usage: /cancel BK-XXXXX
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
    
    # Check if booking number is provided
    if not context.args:
        message = (
            "❌ Mohon berikan nomor booking.\n\n"
            "Gunakan format: /cancel BK-XXXXX\n"
            "Contoh: /cancel BK-00123"
        )
        await update.message.reply_text(message)
        return
    
    booking_number = context.args[0]
    
    # Validate booking number format
    if not booking_number.startswith("BK-"):
        message = (
            "❌ Format nomor booking salah.\n\n"
            "Nomor booking harus dimulai dengan 'BK-'\n"
            "Contoh: /cancel BK-00123"
        )
        await update.message.reply_text(message)
        return
    
    # Find the booking
    booking = await Booking.find_one(Booking.booking_number == booking_number)
    
    if not booking:
        message = (
            f"❌ Booking tidak ditemukan.\n\n"
            f"Nomor booking: {booking_number}\n\n"
            "Periksa kembali nomor booking kamu."
        )
        await update.message.reply_text(message)
        return
    
    # Check if booking is already cancelled
    if booking.status != "active":
        message = (
            f"❌ Booking ini sudah dibatalkan.\n\n"
            f"🆔 {booking.booking_number}"
        )
        await update.message.reply_text(message)
        return
    
    # Check ownership (user can only cancel their own bookings)
    if booking.user_id != db_user.id:
        # Check if user is admin
        if not db_user.is_admin:
            message = (
                f"❌ Kamu tidak memiliki akses untuk membatalkan booking ini.\n\n"
                f"🆔 {booking.booking_number}\n\n"
                "Kamu hanya bisa membatalkan booking milikmu sendiri."
            )
            await update.message.reply_text(message)
            return
    
    # Cancel the booking
    try:
        await cancel_booking(
            booking_id=str(booking.id),
            user_id=db_user.id,
            is_admin=db_user.is_admin
        )
        
        message = (
            f"✅ *Booking Berhasil Dibatalkan*\n\n"
            f"🆔 {booking.booking_number}\n"
            f"🚪 {booking.room_snapshot.name}\n"
            f"📌 {booking.title}\n"
            f"🕐 {format_date_indonesian(booking.start_time)}\n"
            f"⏰ {format_time_range(booking.start_time, booking.end_time)}\n\n"
            "Notifikasi telah dikirim ke grup Telegram."
        )
        await update.message.reply_text(message, parse_mode="Markdown")
        
    except Exception as e:
        message = (
            f"❌ Gagal membatalkan booking.\n\n"
            f"Error: {str(e)}"
        )
        await update.message.reply_text(message)
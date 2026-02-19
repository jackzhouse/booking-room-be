import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from app.models.user import User
from app.models.room import Room
from app.core.config import settings

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command.
    Send welcome message and basic usage instructions.
    """
    user = update.effective_user
    logger.info(f"📩 /start command received from user {user.id} (@{user.username or 'no username'}, {user.first_name})")
    
    # Check if user is registered
    db_user = await User.find_one(User.telegram_id == user.id)
    
    if not db_user:
        welcome_message = (
            f"👋 Halo, {user.first_name}!\n\n"
            "Kamu belum terdaftar di sistem.\n\n"
            "Silakan login dulu menggunakan aplikasi web:\n"
            f"📱 [Link Aplikasi]({settings.FRONTEND_URL})\n\n"
            "Setelah login, kamu bisa menggunakan bot ini untuk:\n"
            "• Melihat jadwal ruangan\n"
            "• Mengelola booking kamu\n"
            "• Membatalkan booking\n\n"
            "Ketik /help untuk melihat semua command yang tersedia."
        )
    else:
        welcome_message = (
            f"👋 Halo, {db_user.full_name}!\n\n"
            f"Selamat datang di Bot Booking Ruang Meeting!\n\n"
            "Berikut command yang tersedia:\n"
            "📅 /mybooking - Lihat booking aktif kamu\n"
            "📋 /schedule - Lihat jadwal hari ini\n"
            "📋 /schedule DD-MM-YYYY - Lihat jadwal tanggal tertentu\n"
            "❌ /cancel BK-XXXXX - Batalkan booking\n\n"
            "Ketik /help untuk informasi lebih lanjut."
        )
    
    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command.
    Show detailed help information.
    """
    help_message = (
        "📖 *Bantuan Bot Booking Ruang Meeting*\n\n"
        "*Daftar Command:*\n\n"
        "/start - Memulai bot dan melihat info\n"
        "/help - Menampilkan pesan bantuan ini\n\n"
        "*Booking:*\n"
        "/mybooking - Lihat semua booking aktif kamu\n"
        "/schedule - Lihat jadwal semua ruangan hari ini\n"
        "/schedule DD-MM-YYYY - Lihat jadwal tanggal tertentu\n"
        "/cancel BK-XXXXX - Batalkan booking\n\n"
        "*Contoh:*\n"
        "/schedule 24-02-2025\n"
        "/cancel BK-00123\n\n"
        "*Catatan:*\n"
        "• Kamu harus login di aplikasi web sebelum bisa menggunakan bot\n"
        "• Booking hanya bisa dibuat lewat aplikasi web\n"
        "• Bot digunakan untuk melihat dan mengelola booking\n\n"
        "Hubungi admin jika ada pertanyaan."
    )
    
    await update.message.reply_text(help_message, parse_mode="Markdown")
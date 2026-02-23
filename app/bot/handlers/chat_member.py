import logging
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app.models.telegram_group import TelegramGroup
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_message_with_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle message updates to detect when bot joins a group.
    This function checks if a new_chat_member field exists and if it's bot itself.
    This is same approach used in successful TypeScript code.
    """
    if not update.message:
        return
    
    message = update.message
    
    # Check if this is a new chat member event (someone joined group)
    if not message.new_chat_members:
        return
    
    # Get first new member from list
    new_member = message.new_chat_members[0]
    chat = message.chat
    
    # Check if new member is bot itself
    bot = context.bot
    bot_id = bot.id
    
    logger.info("📊 New chat member event detected:")
    logger.info(f"   - New member ID: {new_member.id}")
    logger.info(f"   - Bot ID: {bot_id}")
    logger.info(f"   - Is bot: {new_member.is_bot}")
    logger.info(f"   - Is bot itself: {new_member.id == bot_id}")
    logger.info(f"   - Chat ID: {chat.id}")
    logger.info(f"   - Chat type: {chat.type}")
    logger.info(f"   - Chat title: {chat.title}")
    
    # Only proceed if new member is bot itself
    if not new_member.is_bot or new_member.id != bot_id:
        logger.info("❌ New member is not bot, skipping...")
        return
    
    # Get group information
    group_id = chat.id
    group_name = chat.title or f"Group {group_id}"
    
    logger.info(f"🎉 Bot invited to group: {group_name} (ID: {group_id})")
    logger.info("🔄 Starting group registration process...")
    
    try:
        # Check if group already exists
        logger.info(f"🔍 Checking if group {group_id} already exists in database...")
        existing_group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
        
        if existing_group:
            logger.info(f"ℹ️ Group {group_name} already registered, skipping...")
            
            # Send confirmation message to group
            await chat.send_message(
                f"✅ Bot sudah terdaftar di grup ini!\n\n"
                f"Grup ID: {group_id}\n"
                f"Nama: {group_name}\n\n"
                f"Silakan lanjutkan menggunakan bot untuk booking ruangan."
            )
            return
        
        # Create new Telegram group record
        logger.info("💾 Creating new group record in database...")
        new_group = TelegramGroup(
            group_id=group_id,
            group_name=group_name,
            is_active=True
        )
        
        await new_group.insert()
        logger.info(f"✅ Successfully registered new group: {group_name} (ID: {group_id})")
        
        # Send welcome message to group
        logger.info("📤 Sending welcome message to group...")
        welcome_msg = (
            f"🎉 *Bot Berhasil Bergabung!*\n\n"
            f"Grup ini telah terdaftar di sistem:\n"
            f"📝 Nama: {group_name}\n"
            f"🆔 ID: {group_id}\n\n"
            f"Bot sekarang siap digunakan di grup ini!\n\n"
            f"Command yang tersedia:\n"
            f"📅 /schedule - Lihat jadwal ruangan\n"
            f"📋 /schedule DD-MM-YYYY - Lihat jadwal tanggal tertentu\n\n"
            f"Happy booking! 🚀"
        )
        
        await chat.send_message(welcome_msg, parse_mode="Markdown")
        logger.info(f"✅ Welcome message sent successfully to group {group_name}")
        
    except Exception as e:
        logger.error(f"❌ Error registering group {group_name}: {str(e)}")
        logger.error(f"❌ Full error details: {type(e).__name__}", exc_info=True)
        
        # Try to send error message to group (best effort)
        try:
            await chat.send_message(
                f"❌ Terjadi kesalahan saat mendaftarkan grup ini.\n"
                f"Silakan hubungi admin.\n\n"
                f"Error: {str(e)}"
            )
        except Exception as send_error:
            logger.error(f"❌ Failed to send error message: {str(send_error)}")


def get_chat_member_handler():
    """
    Create and return a MessageHandler for detecting new chat member events.
    This handler checks for new_chat_member field in message updates.
    Same approach as successful TypeScript implementation.
    """
    return MessageHandler(
        callback=handle_message_with_new_member,
        filters=filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP,
        block=False  # Don't block other handlers from running
    )
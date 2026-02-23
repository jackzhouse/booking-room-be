import logging
from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler, MyChatMemberHandler

from app.models.telegram_group import TelegramGroup
from app.core.config import settings

logger = logging.getLogger(__name__)


async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle chat member updates.
    This function is triggered when a user's chat membership status changes.
    We use this to automatically register Telegram groups when the bot is invited.
    """
    if not update.chat_member:
        return
    
    # Get the bot's user ID
    bot = context.bot
    bot_id = bot.id
    
    # Get the chat member update info
    chat_member_update = update.chat_member
    new_member = chat_member_update.new_chat_member
    old_member = chat_member_update.old_chat_member
    chat = chat_member_update.chat
    
    # Log all chat member updates for debugging
    logger.info(f"📊 Chat member update received:")
    logger.info(f"   - User ID: {new_member.user.id}")
    logger.info(f"   - Bot ID: {bot_id}")
    logger.info(f"   - Is bot: {new_member.user.id == bot_id}")
    logger.info(f"   - New status: {new_member.status}")
    logger.info(f"   - Old status: {old_member.status}")
    logger.info(f"   - Chat ID: {chat.id}")
    logger.info(f"   - Chat type: {chat.type}")
    logger.info(f"   - Chat title: {chat.title}")
    
    # Only proceed if the status change involves the bot itself
    if new_member.user.id != bot_id:
        logger.info("❌ Update is for another user, skipping...")
        return
    
    # Only proceed if the bot became a member/admin/creator (was not a member before)
    # Bot can be invited as: member, administrator, or creator
    valid_new_statuses = ["member", "administrator", "creator"]
    invalid_old_statuses = ["left", "kicked", "restricted", "banned"]
    
    if new_member.status in valid_new_statuses and old_member.status in invalid_old_statuses:
        # Get group information
        group_id = chat.id
        group_name = chat.title or f"Group {group_id}"
        
        logger.info(f"🎉 Bot invited to group: {group_name} (ID: {group_id})")
        logger.info(f"🔄 Starting group registration process...")
        
        try:
            # Check if group already exists
            logger.info(f"🔍 Checking if group {group_id} already exists in database...")
            existing_group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
            
            if existing_group:
                logger.info(f"ℹ️ Group {group_name} already registered, skipping...")
                
                # Send confirmation message to the group
                await chat.send_message(
                    f"✅ Bot sudah terdaftar di grup ini!\n\n"
                    f"Grup ID: {group_id}\n"
                    f"Nama: {group_name}\n\n"
                    f"Silakan lanjutkan menggunakan bot untuk booking ruangan."
                )
                return
            
            # Create new Telegram group record
            logger.info(f"💾 Creating new group record in database...")
            new_group = TelegramGroup(
                group_id=group_id,
                group_name=group_name,
                is_active=True
            )
            
            await new_group.insert()
            logger.info(f"✅ Successfully registered new group: {group_name} (ID: {group_id})")
            
            # Send welcome message to the group
            logger.info(f"📤 Sending welcome message to group...")
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
            
            # Try to send error message to the group (best effort)
            try:
                await chat.send_message(
                    f"❌ Terjadi kesalahan saat mendaftarkan grup ini.\n"
                    f"Silakan hubungi admin.\n\n"
                    f"Error: {str(e)}"
                )
            except Exception as send_error:
                logger.error(f"❌ Failed to send error message: {str(send_error)}")
    
    # Handle bot being removed from group
    elif new_member.status in ["left", "kicked"] and old_member.status == "member":
        group_id = chat.id
        group_name = chat.title or f"Group {group_id}"
        
        logger.info(f"👋 Bot removed from group: {group_name} (ID: {group_id})")
        
        try:
            # Deactivate the group in database instead of deleting
            existing_group = await TelegramGroup.find_one(TelegramGroup.group_id == group_id)
            
            if existing_group:
                existing_group.is_active = False
                await existing_group.save()
                logger.info(f"✅ Group {group_name} marked as inactive")
            
        except Exception as e:
            logger.error(f"❌ Error deactivating group {group_name}: {str(e)}")


def get_chat_member_handler():
    """
    Create and return a MyChatMemberHandler for bot invite detection.
    MyChatMemberHandler specifically handles the bot's own membership changes.
    """
    return MyChatMemberHandler(
        handle_chat_member_update,
        MyChatMemberHandler.MY_CHAT_MEMBER,
        block=False  # Don't block other handlers from running
    )

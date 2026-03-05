import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.core.config import settings
from app.bot.handlers.start import start, help_command
from app.bot.handlers.mybooking import mybooking
from app.bot.handlers.schedule import schedule
from app.bot.handlers.cancel import cancel
from app.bot.handlers.authorize import authorize_command
from app.bot.handlers.chat_member import get_chat_member_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize bot application
application = Application.builder().token(settings.BOT_TOKEN).build()

# Register chat member handler FIRST (before command handlers)
# This ensures chat_member updates are processed correctly
chat_member_handler = get_chat_member_handler()
application.add_handler(chat_member_handler)

# Register command handlers
start_handler = CommandHandler("start", start)
help_handler = CommandHandler("help", help_command)
mybooking_handler = CommandHandler("mybooking", mybooking)
schedule_handler = CommandHandler("schedule", schedule)
cancel_handler = CommandHandler("cancel", cancel)
authorize_handler = CommandHandler("authorize", authorize_command)

application.add_handler(start_handler)
application.add_handler(help_handler)
application.add_handler(mybooking_handler)
application.add_handler(schedule_handler)
application.add_handler(cancel_handler)
application.add_handler(authorize_handler)

# Initialize application once (not for every update)
application_started = False


async def get_application():
    """Get or start bot application"""
    global application_started
    if not application_started:
        await application.initialize()
        await application.start()
        application_started = True
    return application


async def stop_application():
    """Stop bot application"""
    global application_started
    if application_started:
        await application.stop()
        await application.shutdown()
        application_started = False


async def handle_webhook_update(data: dict, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming webhook updates from Telegram.
    This function is called by FastAPI when Telegram sends updates via webhook.
    """
    logger.info("=" * 50)
    logger.info("🔔 WEBHOOK UPDATE RECEIVED")
    logger.info("=" * 50)
    logger.info(f"📦 Raw data keys: {list(data.keys())}")
    
    app = await get_application()
    
    # Log the incoming update type for debugging
    if "message" in data:
        message = data.get("message", {})
        if "new_chat_members" in message:
            logger.info(f"📨 Received MESSAGE with NEW_CHAT_MEMBERS (BOT INVITE DETECTED!)")
        else:
            logger.info(f"📨 Received MESSAGE update")
            # Log message text if present
            if "text" in message:
                logger.info(f"💬 Message text: {message.get('text')}")
            # Log user info
            if "from" in message:
                user = message.get("from", {})
                logger.info(f"👤 From user: {user.get('id')} - {user.get('first_name')}")
    elif "callback_query" in data:
        logger.info(f"📨 Received CALLBACK_QUERY update")
    elif "my_chat_member" in data:
        logger.info(f"📨 Received MY_CHAT_MEMBER update")
    elif "chat_member" in data:
        logger.info(f"📨 Received CHAT_MEMBER update (other user)")
    elif "edited_message" in data:
        logger.info(f"📨 Received EDITED_MESSAGE update")
    else:
        logger.info(f"📨 Received UNKNOWN update type: {list(data.keys())}")
    
    # Create Update object from JSON data using the application's bot instance
    bot = app.bot
    update = Update.de_json(data, bot)
    
    # Log if update was successfully parsed
    if update:
        logger.info(f"✅ Update parsed successfully: {update.update_id}")
        if update.message and update.message.new_chat_members:
            logger.info(f"✅ MESSAGE with NEW_CHAT_MEMBERS detected in parsed Update object!")
        elif update.my_chat_member:
            logger.info(f"✅ MY_CHAT_MEMBER update detected in parsed Update object!")
        elif update.chat_member:
            logger.info(f"✅ CHAT_MEMBER update detected in parsed Update object!")
    else:
        logger.error(f"❌ Failed to parse update from data")
    
    # Process the update
    logger.info(f"🔄 Processing update through handlers...")
    await app.process_update(update)
    logger.info(f"✅ Update processing completed")


async def set_webhook():
    """
    Set webhook for Telegram bot.
    This should be called during application startup.
    Creates a temporary application instance to set the webhook without affecting the main application.
    """
    webhook_url = settings.webhook_url
    logger.info(f"🔗 Setting Telegram webhook to: {webhook_url}")
    
    try:
        # Create a temporary application instance just for setting webhook
        temp_app = Application.builder().token(settings.BOT_TOKEN).build()
        await temp_app.initialize()
        await temp_app.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]
        )
        logger.info("✅ Telegram webhook set successfully with allowed_updates: message, callback_query, chat_member, my_chat_member")
        await temp_app.shutdown()
    except Exception as e:
        logger.error(f"❌ Error setting webhook: {str(e)}")
        raise


async def delete_webhook():
    """
    Delete webhook for Telegram bot.
    This should be called during application shutdown or when switching to polling mode.
    Creates a temporary application instance to delete webhook without affecting the main application.
    """
    try:
        # Create a temporary application instance just for deleting webhook
        temp_app = Application.builder().token(settings.BOT_TOKEN).build()
        await temp_app.initialize()
        await temp_app.bot.delete_webhook()
        logger.info("✅ Telegram webhook deleted successfully")
        await temp_app.shutdown()
    except Exception as e:
        logger.error(f"❌ Error deleting webhook: {str(e)}")
        raise

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.core.config import settings
from app.bot.handlers.start import start, help_command
from app.bot.handlers.mybooking import mybooking
from app.bot.handlers.schedule import schedule
from app.bot.handlers.cancel import cancel
from app.bot.handlers.authorize import authorize_command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize bot application
application = Application.builder().token(settings.BOT_TOKEN).build()

# Register handlers
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

# Initialize the application once (not for every update)
application_initialized = False


async def get_application():
    """Get or initialize the bot application"""
    global application_initialized
    if not application_initialized:
        await application.initialize()
        application_initialized = True
    return application


async def handle_webhook_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming webhook updates from Telegram.
    This function is called by FastAPI when Telegram sends updates via webhook.
    """
    app = await get_application()
    await app.process_update(update)


async def set_webhook():
    """
    Set the webhook for the Telegram bot.
    This should be called during application startup.
    """
    webhook_url = settings.webhook_url
    logger.info(f"🔗 Setting Telegram webhook to: {webhook_url}")
    
    try:
        await application.initialize()
        await application.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info("✅ Telegram webhook set successfully")
        await application.shutdown()
    except Exception as e:
        logger.error(f"❌ Error setting webhook: {str(e)}")
        raise


async def delete_webhook():
    """
    Delete the webhook for the Telegram bot.
    This should be called during application shutdown or when switching to polling mode.
    """
    try:
        await application.initialize()
        await application.bot.delete_webhook()
        logger.info("✅ Telegram webhook deleted successfully")
        await application.shutdown()
    except Exception as e:
        logger.error(f"❌ Error deleting webhook: {str(e)}")
        raise

import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler

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


async def start_polling():
    """
    Start the bot in polling mode.
    This is used for local development without webhooks.
    """
    try:
        logger.info("🚀 Starting Telegram bot in polling mode...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        logger.info("✅ Telegram bot started successfully in polling mode")
        logger.info("📡 Bot is now listening for updates...")
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"❌ Error starting bot: {str(e)}")
        raise
    finally:
        logger.info("🔌 Shutting down bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


async def stop_polling():
    """
    Stop the bot polling.
    """
    if application.updater and application.updater.running:
        await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("🔌 Bot polling stopped")

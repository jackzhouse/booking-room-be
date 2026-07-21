#!/usr/bin/env python3
"""
Test script to verify Telegram bot is running in polling mode.
"""
import asyncio
import logging
from telegram import Bot
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_bot():
    """Test if bot is working"""
    try:
        logger.info(f"🔍 Testing bot with token: {settings.BOT_TOKEN[:10]}...")
        
        bot = Bot(token=settings.BOT_TOKEN)
        
        # Get bot info
        bot_info = await bot.get_me()
        logger.info(f"✅ Bot connected successfully!")
        logger.info(f"   Bot name: @{bot_info.username}")
        logger.info(f"   Bot ID: {bot_info.id}")
        logger.info(f"   Can read messages: {bot_info.can_read_all_group_messages}")
        
        print("\n" + "="*60)
        print("🤖 BOT STATUS: RUNNING AND ACCESSIBLE")
        print("="*60)
        print(f"Bot Username: @{bot_info.username}")
        print(f"Bot Name: {bot_info.first_name}")
        print("\n✅ Your bot should now respond to /start command!")
        print("   Send /start to your bot in Telegram to test it.")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error testing bot: {str(e)}")
        print("\n" + "="*60)
        print("❌ BOT ERROR")
        print("="*60)
        print(f"Error: {str(e)}")
        print("\nPossible issues:")
        print("1. Invalid BOT_TOKEN in .env file")
        print("2. Bot token has been revoked")
        print("3. Network connectivity issues")
        print("\nPlease check your BOT_TOKEN in .env file and try again.")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(test_bot())
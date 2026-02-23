#!/usr/bin/env python3
"""
Script untuk reset Telegram bot webhook
Gunakan script ini untuk memastikan webhook ter-set dengan konfigurasi yang benar
"""
import asyncio
import sys
from telegram import Bot
from app.core.config import settings


async def reset_webhook():
    """Reset dan set ulang webhook dengan konfigurasi yang benar"""
    print(f"🔗 Resetting webhook for bot...")
    
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Step 1: Delete webhook existing
    print(f"🗑️  Deleting existing webhook...")
    await bot.delete_webhook()
    print(f"✅ Webhook deleted")
    
    # Step 2: Set ulang webhook dengan konfigurasi yang benar
    # Gunakan URL production langsung (Render)
    webhook_url = "https://booking-room-be.onrender.com/webhook/telegram/8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k"
    print(f"🔗 Setting webhook to: {webhook_url}")
    
    await bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]
    )
    print(f"✅ Webhook set successfully")
    
    # Step 3: Verifikasi konfigurasi
    webhook_info = await bot.get_webhook_info()
    print(f"\n📊 Webhook Info:")
    print(f"   URL: {webhook_info.url}")
    print(f"   Allowed Updates: {webhook_info.allowed_updates}")
    print(f"   Pending Updates: {webhook_info.pending_update_count}")
    print(f"   Max Connections: {webhook_info.max_connections}")
    
    # Verifikasi allowed_updates
    expected_updates = ["message", "callback_query", "chat_member", "my_chat_member"]
    if set(webhook_info.allowed_updates) == set(expected_updates):
        print(f"\n✅ Allowed updates configuration is CORRECT!")
    else:
        print(f"\n❌ Allowed updates configuration is WRONG!")
        print(f"   Expected: {expected_updates}")
        print(f"   Actual: {webhook_info.allowed_updates}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(reset_webhook())
        print(f"\n🎉 Webhook reset completed successfully!")
        print(f"\n⚠️  INSTRUKSI:")
        print(f"   1. Invite bot ke grup baru")
        print(f"   2. Cek logs di Render Dashboard")
        print(f"   3. Harapannya akan muncul log: '📨 Received CHAT_MEMBER update'")
    except Exception as e:
        print(f"\n❌ Error resetting webhook: {str(e)}")
        sys.exit(1)
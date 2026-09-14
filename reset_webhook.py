#!/usr/bin/env python3
"""
Script untuk reset Telegram bot webhook
Gunakan script ini untuk memastikan webhook ter-set dengan konfigurasi yang benar
"""
import asyncio
import sys
from telegram import Bot
from app.core.config import settings
from app.bot.constants import TELEGRAM_ALLOWED_UPDATES


async def reset_webhook():
    """Reset dan set ulang webhook dengan konfigurasi yang benar"""
    print(f"🔗 Resetting webhook for bot...")
    
    bot = Bot(token=settings.BOT_TOKEN)
    
    # Step 1: Delete webhook existing
    print(f"🗑️  Deleting existing webhook...")
    await bot.delete_webhook()
    print(f"✅ Webhook deleted")
    
    # Step 2: Use the same configured public URL as application startup.
    webhook_url = settings.webhook_url
    print(f"🔗 Setting webhook to: {webhook_url}")

    webhook_kwargs = {
        "url": webhook_url,
        "drop_pending_updates": True,
        "allowed_updates": TELEGRAM_ALLOWED_UPDATES
    }
    if settings.WEBHOOK_SECRET_TOKEN:
        webhook_kwargs["secret_token"] = settings.WEBHOOK_SECRET_TOKEN

    await bot.set_webhook(**webhook_kwargs)
    print(f"✅ Webhook set successfully")
    
    # Step 3: Verifikasi konfigurasi
    webhook_info = await bot.get_webhook_info()
    print(f"\n📊 Webhook Info:")
    print(f"   URL: {webhook_info.url}")
    print(f"   Allowed Updates: {webhook_info.allowed_updates}")
    print(f"   Pending Updates: {webhook_info.pending_update_count}")
    print(f"   Max Connections: {webhook_info.max_connections}")
    
    # Verifikasi allowed_updates
    expected_updates = TELEGRAM_ALLOWED_UPDATES
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
        print("   2. Cek logs aplikasi yang sedang berjalan")
        print(f"   3. Harapannya akan muncul log: '📨 Received MY_CHAT_MEMBER update'")
    except Exception as e:
        print(f"\n❌ Error resetting webhook: {str(e)}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Manual script to set Telegram webhook.
Use this to verify or manually configure the webhook.
"""
import requests
import sys
from urllib.parse import urljoin

# Your bot token
BOT_TOKEN = "8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k"

# Your backend URL (should match WEBHOOK_BASE_URL in Consul)
WEBHOOK_BASE_URL = "https://api-booking-room.tkilocal.biz.id"

# Full webhook URL
WEBHOOK_URL = urljoin(WEBHOOK_BASE_URL, f"/webhook/telegram/{BOT_TOKEN}")

def get_webhook_info():
    """Get current webhook info from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    response = requests.get(url)
    return response.json()

def set_webhook():
    """Set webhook for the bot"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    payload = {
        "url": WEBHOOK_URL,
        "drop_pending_updates": True,
        "allowed_updates": ["message", "callback_query", "chat_member", "my_chat_member"]
    }
    
    print(f"🔗 Setting webhook to: {WEBHOOK_URL}")
    print(f"📦 Payload: {payload}")
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    return result

def delete_webhook():
    """Delete webhook (switch to polling mode)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.get(url)
    return response.json()

if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM WEBHOOK MANAGER")
    print("=" * 60)
    print(f"Bot Token: {BOT_TOKEN}")
    print(f"Webhook Base URL: {WEBHOOK_BASE_URL}")
    print(f"Full Webhook URL: {WEBHOOK_URL}")
    print("=" * 60)
    
    # Check current status
    print("\n📋 Current Webhook Info:")
    print("-" * 60)
    info = get_webhook_info()
    print(f"URL: {info['result']['url']}")
    print(f"Pending Updates: {info['result']['pending_update_count']}")
    print(f"Last Error Date: {info['result'].get('last_error_date', 'None')}")
    print(f"Last Error Message: {info['result'].get('last_error_message', 'None')}")
    print("-" * 60)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "set":
            print("\n🔧 Setting webhook...")
            result = set_webhook()
            if result.get("ok"):
                print("✅ Webhook set successfully!")
                print(f"URL: {result['result']}")
            else:
                print(f"❌ Failed to set webhook: {result.get('description')}")
                
        elif command == "delete":
            print("\n🗑️  Deleting webhook...")
            result = delete_webhook()
            if result.get("ok"):
                print("✅ Webhook deleted successfully!")
            else:
                print(f"❌ Failed to delete webhook: {result.get('description')}")
                
        elif command == "info":
            print("\n📋 Current webhook info shown above.")
            
        else:
            print(f"\n❌ Unknown command: {command}")
            print("Usage: python set_webhook_manual.py [set|delete|info]")
    else:
        print("\n💡 Usage:")
        print("  python set_webhook_manual.py set     - Set webhook")
        print("  python set_webhook_manual.py delete  - Delete webhook")
        print("  python set_webhook_manual.py info    - Show webhook info")
        print("\n⚠️  No command specified. Use 'set' to configure webhook.")
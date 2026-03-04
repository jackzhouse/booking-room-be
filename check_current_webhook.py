"""
Check current webhook status using the deployed configuration.
This will help identify why the bot is not responding.
"""
import requests
import json

def check_webhook_status():
    """Check the current webhook status by testing the Telegram API"""
    
    print("=" * 80)
    print("🔧 WEBHOOK STATUS CHECKER")
    print("=" * 80)
    print("\nTesting webhook endpoint accessibility...")
    
    # Test if the webhook endpoint pattern is accessible
    webhook_base = "https://api-booking-room.tkilocal.biz.id"
    
    # Test health endpoint
    try:
        print(f"\n1. Testing health endpoint...")
        response = requests.get(f"{webhook_base}/health", timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Health endpoint is accessible")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Health endpoint returned HTTP {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error accessing health endpoint: {str(e)}")
    
    # Test webhook endpoint structure
    print(f"\n2. Checking webhook endpoint structure...")
    print(f"   The webhook endpoint should be: {webhook_base}/webhook/telegram/<BOT_TOKEN>")
    
    # Without the bot token, we can't check the actual webhook status
    print(f"\n3. To check the actual Telegram webhook status, we need the bot token.")
    print(f"   Please run: python check_webhook_status.py")
    print(f"   And provide your bot token when prompted.")
    
    print(f"\n💡 Alternative: You can check the webhook status using curl:")
    print(f"   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo")
    
    print(f"\n💡 The bot token should be in your Consul configuration at:")
    print(f"   new-config/psp-booking-room-be/setting -> BOT_TOKEN")


if __name__ == "__main__":
    check_webhook_status()
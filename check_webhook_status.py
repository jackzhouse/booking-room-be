"""
Simple webhook checker - checks Telegram webhook status without needing Consul.
This will help identify if the webhook is configured correctly.
"""
import requests
import sys

def get_bot_token():
    """Get bot token from user input"""
    print("=" * 80)
    print("🔧 TELEGRAM WEBHOOK CHECKER")
    print("=" * 80)
    print("\nThis tool checks if your bot's webhook is configured correctly.")
    print("You need to provide your bot token to proceed.\n")
    
    # Try to read from environment variable first
    import os
    token = os.environ.get('BOT_TOKEN')
    
    if token:
        print(f"✅ Found BOT_TOKEN in environment variable")
        return token
    
    # Otherwise prompt user
    token = input("Please enter your bot token (from @BotFather): ").strip()
    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)
    
    return token


def check_bot_info(bot_token: str) -> dict:
    """Check if bot token is valid and get bot info"""
    try:
        print("\n🔍 Checking bot token validity...")
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                bot_info = data.get('result', {})
                print("✅ Bot token is valid!")
                return bot_info
            else:
                print(f"❌ Invalid bot token: {data.get('description')}")
                sys.exit(1)
        else:
            print(f"❌ HTTP error: {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error checking bot: {str(e)}")
        sys.exit(1)


def check_webhook_info(bot_token: str) -> dict:
    """Get current webhook information"""
    try:
        print("\n🔍 Getting current webhook configuration...")
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                webhook_info = data.get('result', {})
                return webhook_info
            else:
                print(f"❌ Error: {data.get('description')}")
                return None
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_webhook_endpoint(url: str, bot_token: str) -> bool:
    """Test if webhook endpoint is accessible"""
    try:
        print(f"\n🔍 Testing webhook endpoint accessibility...")
        print(f"   URL: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Webhook endpoint is accessible (HTTP {response.status_code})")
            return True
        else:
            print(f"❌ Webhook endpoint returned HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.Timeout:
        print("❌ Webhook endpoint timeout (not accessible)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Webhook endpoint connection refused (not accessible)")
        return False
    except Exception as e:
        print(f"❌ Error testing webhook endpoint: {str(e)}")
        return False


def main():
    """Main function"""
    token = get_bot_token()
    
    # Check bot info
    bot_info = check_bot_info(token)
    print(f"\n🤖 Bot Information:")
    print(f"  - Username: @{bot_info.get('username')}")
    print(f"  - Name: {bot_info.get('first_name')}")
    print(f"  - ID: {bot_info.get('id')}")
    
    # Check webhook info
    webhook_info = check_webhook_info(token)
    
    if webhook_info:
        current_webhook = webhook_info.get('url', '')
        print(f"\n🔗 Current Webhook Configuration:")
        print(f"  - URL: {current_webhook if current_webhook else '❌ NO WEBHOOK SET'}")
        print(f"  - Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
        print(f"  - Pending updates: {webhook_info.get('pending_update_count', 0)}")
        print(f"  - Last error date: {webhook_info.get('last_error_date', 'None')}")
        print(f"  - Last error message: {webhook_info.get('last_error_message', 'None')}")
        
        # Expected webhook URL
        expected_url = f"https://api-booking-room.tkilocal.biz.id/webhook/telegram/{token}"
        
        print(f"\n📋 Expected Webhook URL:")
        print(f"  - URL: {expected_url}")
        
        # Check if webhook matches
        print(f"\n🔍 Webhook Status:")
        if not current_webhook:
            print("  ❌ CRITICAL: No webhook is set!")
            print("  💡 The bot will NOT receive any messages until webhook is set.")
            print("  💡 You need to set the webhook to: {expected_url}")
        elif current_webhook != expected_url:
            print("  ❌ CRITICAL: Webhook is pointing to WRONG URL!")
            print(f"  💡 Current:  {current_webhook}")
            print(f"  💡 Expected: {expected_url}")
            print("  💡 Telegram is sending messages to the wrong endpoint.")
        else:
            print("  ✅ Webhook URL is correctly configured!")
            
            # Test if the endpoint is accessible
            health_url = "https://api-booking-room.tkilocal.biz.id/health"
            test_webhook_endpoint(health_url, token)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        if not current_webhook:
            print("❌ PROBLEM: Bot has NO webhook configured.")
            print("🔧 SOLUTION: Set webhook using:")
            print(f"   curl -F 'url={expected_url}' https://api.telegram.org/bot{token}/setWebhook")
        elif current_webhook != expected_url:
            print("❌ PROBLEM: Webhook is pointing to wrong URL.")
            print("🔧 SOLUTION: Reset webhook using:")
            print(f"   curl -F 'url={expected_url}' https://api.telegram.org/bot{token}/setWebhook")
        else:
            print("✅ Webhook configuration looks correct!")
            print("💡 If bot still doesn't respond, check:")
            print("   1. Server logs for incoming webhook requests")
            print("   2. Bot token is correct in Consul configuration")
            print("   3. Application is running and webhook endpoint is accessible")


if __name__ == "__main__":
    main()
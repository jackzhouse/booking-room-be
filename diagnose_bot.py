"""
Diagnostic script to check bot configuration and webhook status.
This will help identify why the bot is not responding to commands.
"""
import asyncio
import requests
from typing import Dict, Any
import yaml
import consul

# Load configuration from Consul
def load_settings_from_consul():
    """Load settings from Consul key-value store"""
    try:
        print("🔍 Connecting to Consul...")
        c = consul.Consul(host='consul', port=8500)
        index, data = c.kv.get('new-config/psp-booking-room-be/setting')
        
        if not data or not data.get('Value'):
            print("❌ No configuration found in Consul!")
            return None
        
        config = yaml.load(data['Value'], Loader=yaml.SafeLoader)
        print("✅ Successfully loaded configuration from Consul")
        return config
    except Exception as e:
        print(f"❌ Error loading from Consul: {str(e)}")
        return None


def check_telegram_webhook_info(bot_token: str) -> Dict[str, Any]:
    """Get current webhook information from Telegram API"""
    try:
        print("\n🔍 Checking Telegram webhook status...")
        url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                webhook_info = data.get('result', {})
                print("✅ Got webhook info from Telegram")
                return webhook_info
            else:
                print(f"❌ Telegram API error: {data.get('description')}")
                return None
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error checking webhook: {str(e)}")
        return None


def check_bot_info(bot_token: str) -> Dict[str, Any]:
    """Get bot information from Telegram API"""
    try:
        print("\n🔍 Checking bot information...")
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
                return None
        else:
            print(f"❌ HTTP error: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error checking bot info: {str(e)}")
        return None


def check_webhook_endpoint(webhook_url: str) -> bool:
    """Test if webhook endpoint is accessible"""
    try:
        print(f"\n🔍 Testing webhook endpoint accessibility: {webhook_url}")
        response = requests.get(webhook_url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Webhook endpoint is accessible (HTTP {response.status_code})")
            return True
        else:
            print(f"❌ Webhook endpoint returned HTTP {response.status_code}")
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
    """Main diagnostic function"""
    print("=" * 80)
    print("🔧 BOT CONFIGURATION DIAGNOSTIC TOOL")
    print("=" * 80)
    
    # Load configuration
    config = load_settings_from_consul()
    if not config:
        print("\n❌ CRITICAL: Cannot load configuration. Exiting.")
        return
    
    print("\n📋 Current Configuration:")
    print("-" * 80)
    
    bot_token = config.get('BOT_TOKEN')
    frontend_url = config.get('FRONTEND_URL')
    webhook_base_url = config.get('WEBHOOK_BASE_URL')
    
    print(f"BOT_TOKEN: {'{' + bot_token[:10] + '...}' if bot_token else '❌ NOT SET'}")
    print(f"FRONTEND_URL: {frontend_url or '❌ NOT SET'}")
    print(f"WEBHOOK_BASE_URL: {webhook_base_url or '❌ NOT SET'}")
    
    # Check expected values
    print("\n📋 Expected Configuration:")
    print("-" * 80)
    print(f"FRONTEND_URL should be: https://booking-room.tkilocal.biz.id")
    print(f"WEBHOOK_BASE_URL should be: https://api-booking-room.tkilocal.biz.id")
    
    # Validate configuration
    print("\n✅ Configuration Validation:")
    print("-" * 80)
    
    issues = []
    
    if frontend_url != "https://booking-room.tkilocal.biz.id":
        issues.append(f"FRONTEND_URL mismatch: current={frontend_url}, expected=https://booking-room.tkilocal.biz.id")
    
    if webhook_base_url != "https://api-booking-room.tkilocal.biz.id":
        issues.append(f"WEBHOOK_BASE_URL mismatch: current={webhook_base_url}, expected=https://api-booking-room.tkilocal.biz.id")
    
    if not bot_token:
        issues.append("BOT_TOKEN is not set")
    
    if issues:
        print("❌ Configuration Issues Found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ All configuration values are correct!")
    
    # Check bot token
    if bot_token:
        bot_info = check_bot_info(bot_token)
        if bot_info:
            print(f"\n🤖 Bot Information:")
            print(f"  - Username: @{bot_info.get('username')}")
            print(f"  - Name: {bot_info.get('first_name')}")
            print(f"  - ID: {bot_info.get('id')}")
            
            # Check webhook status
            webhook_info = check_telegram_webhook_info(bot_token)
            if webhook_info:
                current_webhook = webhook_info.get('url', 'NOT SET')
                print(f"\n🔗 Current Telegram Webhook:")
                print(f"  - URL: {current_webhook}")
                print(f"  - Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
                print(f"  - Pending updates: {webhook_info.get('pending_update_count', 0)}")
                
                expected_webhook = f"{webhook_base_url}/webhook/telegram/{bot_token}" if webhook_base_url else "NOT SET"
                print(f"\n  Expected webhook URL: {expected_webhook}")
                
                if current_webhook != expected_webhook:
                    print(f"  ❌ WEBHOOK MISMATCH!")
                    print(f"  Current:  {current_webhook}")
                    print(f"  Expected: {expected_webhook}")
                elif not current_webhook or current_webhook == "":
                    print(f"  ❌ NO WEBHOOK SET!")
                else:
                    print(f"  ✅ Webhook is correctly configured!")
                
                # Test webhook endpoint
                if webhook_base_url:
                    test_url = f"{webhook_base_url}/health"
                    check_webhook_endpoint(test_url)
        
        # Final summary
        print("\n" + "=" * 80)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 80)
        
        if not bot_token:
            print("❌ CRITICAL: BOT_TOKEN is missing. Bot will not receive any messages.")
        elif webhook_base_url != "https://api-booking-room.tkilocal.biz.id":
            print("❌ CRITICAL: WEBHOOK_BASE_URL is incorrect. Webhook pointing to wrong URL.")
        elif frontend_url != "https://booking-room.tkilocal.biz.id":
            print("⚠️  WARNING: FRONTEND_URL is incorrect. Links in bot messages will be wrong.")
        else:
            print("✅ Configuration looks good. Check webhook status above for details.")
        
        print("\n💡 Next Steps:")
        if issues:
            print("  1. Update Consul configuration with correct values")
            print("  2. Restart the application to load new configuration")
            print("  3. Reset webhook if needed: python reset_webhook.py")
        else:
            print("  1. Verify webhook is set correctly")
            print("  2. Test bot commands in Telegram")


if __name__ == "__main__":
    main()
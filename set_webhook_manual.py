#!/usr/bin/env python3
"""
Manual script to set Telegram webhook.
Use this to verify or manually configure the webhook.
"""
import sys
import time
from urllib.parse import urljoin

import requests

# Your bot token
BOT_TOKEN = "8421546523:AAG1UGi9k1dKwyaCdZKUk6zMktWxKF2VXsQ"

# Your backend URL (should match WEBHOOK_BASE_URL in Consul)
WEBHOOK_BASE_URL = "https://api-booking-room.tkilocal.biz.id"

# Full webhook URL
WEBHOOK_URL = urljoin(WEBHOOK_BASE_URL, f"/webhook/telegram/{BOT_TOKEN}")

# Network + retry configuration
REQUEST_TIMEOUT_SECONDS = 20
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2


def mask_token(token: str) -> str:
    """Mask bot token for safer logs."""
    if not token or len(token) < 10:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def safe_webhook_url(url: str, token: str) -> str:
    """Return webhook URL with masked token for display only."""
    return url.replace(token, mask_token(token))


def should_retry(description: str) -> bool:
    """Detect temporary errors worth retrying."""
    if not description:
        return False

    lower = description.lower()
    transient_signals = [
        "failed to resolve host",
        "temporary failure in name resolution",
        "timed out",
        "timeout",
        "bad gateway",
        "gateway timeout",
        "network",
    ]
    return any(signal in lower for signal in transient_signals)


def call_telegram_api(method_name: str, http_method: str = "GET", payload: dict = None) -> dict:
    """Call Telegram Bot API and return JSON response."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method_name}"

    try:
        if http_method.upper() == "POST":
            response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        else:
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        return response.json()
    except requests.RequestException as exc:
        return {"ok": False, "description": f"Request error: {exc}"}
    except ValueError:
        return {"ok": False, "description": "Telegram API returned non-JSON response"}


def get_webhook_info() -> dict:
    """Get current webhook info from Telegram."""
    return call_telegram_api("getWebhookInfo", "GET")


def set_webhook(max_retries: int = MAX_RETRIES, initial_backoff: int = INITIAL_BACKOFF_SECONDS) -> dict:
    """Set webhook for the bot with retry for transient failures."""
    payload = {
        "url": WEBHOOK_URL,
        "drop_pending_updates": True,
        "allowed_updates": ["message", "callback_query", "chat_member", "my_chat_member"],
    }

    print(f"Setting webhook to: {safe_webhook_url(WEBHOOK_URL, BOT_TOKEN)}")
    print(f"Payload: {payload}")

    for attempt in range(1, max_retries + 1):
        result = call_telegram_api("setWebhook", "POST", payload=payload)
        if result.get("ok"):
            return result

        description = result.get("description", "Unknown error")
        if attempt < max_retries and should_retry(description):
            wait_seconds = initial_backoff * (2 ** (attempt - 1))
            print(
                f"Attempt {attempt}/{max_retries} failed: {description}. "
                f"Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)
            continue

        return result

    return {"ok": False, "description": "Unknown error after retries"}


def delete_webhook() -> dict:
    """Delete webhook (switch to polling mode)."""
    return call_telegram_api("deleteWebhook", "GET")


if __name__ == "__main__":
    print("=" * 60)
    print("TELEGRAM WEBHOOK MANAGER")
    print("=" * 60)
    print(f"Bot Token: {mask_token(BOT_TOKEN)}")
    print(f"Webhook Base URL: {WEBHOOK_BASE_URL}")
    print(f"Full Webhook URL: {safe_webhook_url(WEBHOOK_URL, BOT_TOKEN)}")
    print("=" * 60)

    # Check current status
    print("\nCurrent Webhook Info:")
    print("-" * 60)
    info = get_webhook_info()
    if info.get("ok") and info.get("result"):
        current = info["result"]
        current_url = safe_webhook_url(current.get("url", ""), BOT_TOKEN)
        print(f"URL: {current_url}")
        print(f"Pending Updates: {current.get('pending_update_count', 0)}")
        print(f"Last Error Date: {current.get('last_error_date', 'None')}")
        print(f"Last Error Message: {current.get('last_error_message', 'None')}")
    else:
        print(f"Failed to fetch webhook info: {info.get('description', info)}")
    print("-" * 60)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "set":
            print("\nSetting webhook...")
            result = set_webhook()
            if result.get("ok"):
                print("Webhook set successfully")
                print(f"URL: {result.get('result')}")
            else:
                print(f"Failed to set webhook: {result.get('description')}")

        elif command == "delete":
            print("\nDeleting webhook...")
            result = delete_webhook()
            if result.get("ok"):
                print("Webhook deleted successfully")
            else:
                print(f"Failed to delete webhook: {result.get('description')}")

        elif command == "info":
            print("\nCurrent webhook info shown above.")

        else:
            print(f"\nUnknown command: {command}")
            print("Usage: python set_webhook_manual.py [set|delete|info]")
    else:
        print("\nUsage:")
        print("  python set_webhook_manual.py set     - Set webhook")
        print("  python set_webhook_manual.py delete  - Delete webhook")
        print("  python set_webhook_manual.py info    - Show webhook info")
        print("\nNo command specified. Use 'set' to configure webhook.")

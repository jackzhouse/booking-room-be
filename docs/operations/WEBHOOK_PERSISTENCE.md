# Webhook Persistence & Restart Behavior

## Do You Need to Set Webhook After Restart?

**Short Answer: No, not manually.**

The webhook in Telegram is **persistent** - once set, it stays configured even if your backend restarts. The webhook URL is stored on Telegram's servers, not locally.

## How It Should Work

### Automatic Webhook Setup (Ideal Scenario)
Your application (`app/main.py`) automatically sets the webhook during startup:

```python
# In lifespan function
try:
    await set_webhook()
    print("✅ Telegram webhook configured successfully")
except Exception as e:
    print(f"⚠️  Warning: Could not set Telegram webhook: {str(e)}")
```

This means:
1. When the backend starts → It reads `WEBHOOK_BASE_URL` from Consul
2. It calls `set_webhook()` → Configures Telegram with the correct URL
3. Telegram remembers this URL → Even after backend restarts

## Why It Failed This Time

The webhook wasn't set because of **configuration issues**:

1. **Wrong `WEBHOOK_BASE_URL`** in Consul
   - The app tried to set webhook to a wrong URL
   - Or the configuration was missing entirely

2. **Silent Failure**
   - The webhook setup failed but only logged a warning
   - The app continued running, but bot couldn't receive messages

3. **No Manual Intervention**
   - Since webhook was never set correctly initially, it stayed empty

## Current Status

✅ **Webhook is now correctly set and will persist**

The webhook is now configured to:
```
https://api-booking-room.tkilocal.biz.id/webhook/telegram/8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k
```

This configuration is stored on Telegram's servers and will remain active even after backend restarts.

## How to Prevent This Issue

### 1. Fix Consul Configuration

Update `new-config/psp-booking-room-be/setting` in Consul:

```yaml
FRONTEND_URL: "https://booking-room.tkilocal.biz.id"
WEBHOOK_BASE_URL: "https://api-booking-room.tkilocal.biz.id"
BOT_TOKEN: "8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k"
```

This ensures the application sets the webhook to the correct URL automatically.

### 2. Update set_webhook() to be More Robust

The current implementation in `app/bot/webhook.py` could be improved to:
- Check if webhook is already set to correct URL
- Only update if URL changed
- Better error handling and logging

### 3. Add Health Check for Webhook

Consider adding an endpoint to verify webhook status:

```python
@app.get("/bot/webhook/status")
async def webhook_status():
    """Check if bot webhook is correctly configured"""
    webhook_info = await get_webhook_info()
    expected_url = settings.webhook_url
    
    return {
        "webhook_url": webhook_info.get("url"),
        "expected_url": expected_url,
        "is_configured": webhook_info.get("url") == expected_url,
        "pending_updates": webhook_info.get("pending_update_count", 0)
    }
```

## Manual Webhook Management Tools

### Check Current Webhook Status
```bash
curl https://api.telegram.org/bot8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k/getWebhookInfo
```

### Set Webhook (If Needed)
```bash
curl -F "url=https://api-booking-room.tkilocal.biz.id/webhook/telegram/8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k" \
  https://api.telegram.org/bot8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k/setWebhook
```

### Delete Webhook (Switch to Polling Mode)
```bash
curl https://api.telegram.org/bot8421546523:AAERgz8eG3R0cqyzvtq3-U1K-hiP43jr67k/deleteWebhook
```

## When Would You Need to Manually Set Webhook?

You might need to manually set the webhook in these scenarios:

1. **Changed Backend URL**
   - Moved from `https://vercel-app.com` to `https://api-booking-room.tkilocal.biz.id`
   - Need to update webhook to point to new URL

2. **Changed Bot Token**
   - Reset bot token from @BotFather
   - New token means new webhook endpoint

3. **Webhook Was Deleted**
   - Someone accidentally deleted the webhook
   - Manual intervention via deleteWebhook API

4. **Initial Setup**
   - First time deploying the bot
   - Bot never had webhook configured

5. **Configuration Issues**
   - Consul had wrong configuration
   - Automatic setup failed

## Best Practices

### 1. Keep Consul Configuration Accurate
Always ensure `WEBHOOK_BASE_URL` matches your actual backend URL.

### 2. Monitor Webhook Health
Regularly check webhook status:
- Use `/bot/webhook/status` endpoint (if implemented)
- Check Telegram API for errors
- Monitor server logs for webhook failures

### 3. Update Webhook When URL Changes
If you change your backend URL, immediately update:
1. Consul configuration
2. Webhook in Telegram
3. Any hardcoded URLs

### 4. Use the Same Bot Token
Don't change the bot token unless absolutely necessary (security breach, etc.).

## Summary

✅ **Webhook is now correctly configured and will persist across restarts**

🔧 **To prevent future issues:**
1. Update Consul with correct `WEBHOOK_BASE_URL`
2. The app will automatically maintain the webhook on startup
3. Only manual intervention needed if URL changes

🎯 **You don't need to manually set webhook after normal restarts** - it will persist in Telegram.
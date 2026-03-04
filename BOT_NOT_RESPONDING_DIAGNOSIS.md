# Bot Not Responding - Diagnosis & Solution

## Problem Summary
The Telegram bot is not responding to ANY commands (`/start`, `/help`, `/authorize`, etc.).

## Root Causes Identified

### 1. Configuration Issues
- **FRONTEND_URL**: Currently set to `https://booking-meeting-flax.vercel.app` in default config
  - ✅ Should be: `https://booking-room.tkilocal.biz.id`
  
- **WEBHOOK_BASE_URL**: Unknown (loaded from Consul)
  - ✅ Should be: `https://api-booking-room.tkilocal.biz.id`

- **BOT_TOKEN**: Unknown (loaded from Consul)
  - ❓ Must be valid for bot to work

### 2. Likely Webhook Issue
The most probable cause is that the **Telegram webhook is either not set or pointing to the wrong URL**. When the webhook is misconfigured, Telegram cannot send updates to your bot.

## Diagnostic Tools Created

### 1. check_webhook_status.py
Checks the Telegram webhook configuration by querying the Telegram API directly.

**Usage:**
```bash
python check_webhook_status.py
```

This will:
- Verify your bot token is valid
- Show current webhook URL configured in Telegram
- Compare it with the expected URL
- Test if the webhook endpoint is accessible

### 2. check_current_webhook.py
Basic endpoint accessibility check without needing the bot token.

**Usage:**
```bash
python check_current_webhook.py
```

### 3. diagnose_bot.py
Comprehensive diagnostic (requires Consul access - not useful locally).

## Solution Steps

### Step 1: Check Current Webhook Status

**Option A: Using the diagnostic script**
```bash
python check_webhook_status.py
```
When prompted, enter your bot token (from Consul or @BotFather).

**Option B: Using curl directly**
```bash
# Replace <YOUR_BOT_TOKEN> with your actual bot token
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

### Step 2: Interpret the Results

#### Scenario 1: No Webhook Set
If the response shows `url: ""`, then:
- **Problem**: No webhook is configured
- **Solution**: Set the webhook

#### Scenario 2: Wrong Webhook URL
If the response shows a URL different from `https://api-booking-room.tkilocal.biz.id/webhook/telegram/<TOKEN>`:
- **Problem**: Webhook is pointing to wrong endpoint
- **Solution**: Reset the webhook

#### Scenario 3: Webhook Has Errors
If `last_error_message` shows an error:
- **Problem**: Webhook is failing
- **Solution**: Check the error and fix accordingly

### Step 3: Fix the Webhook

**Option A: Using the existing script**
```bash
python set_webhook_manual.py
```

**Option B: Using curl directly**
```bash
# Replace <YOUR_BOT_TOKEN> with your actual bot token
curl -F "url=https://api-booking-room.tkilocal.biz.id/webhook/telegram/<YOUR_BOT_TOKEN>" \
  https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook
```

### Step 4: Update Consul Configuration (If Needed)

The following values should be set in Consul at `new-config/psp-booking-room-be/setting`:

```yaml
FRONTEND_URL: "https://booking-room.tkilocal.biz.id"
WEBHOOK_BASE_URL: "https://api-booking-room.tkilocal.biz.id"
BOT_TOKEN: "<your-bot-token>"
```

**To update in Consul:**
1. Access your Consul instance
2. Navigate to: `new-config/psp-booking-room-be/setting`
3. Update the values above
4. Restart the application to load new configuration

### Step 5: Verify the Fix

After setting the webhook:

1. Check webhook status again:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

2. The `url` should now be: `https://api-booking-room.tkilocal.biz.id/webhook/telegram/<YOUR_BOT_TOKEN>`

3. Test the bot in Telegram:
   - Send `/start`
   - Send `/help`
   - Generate a code from frontend and test `/authorize <code>`

## Expected Webhook URL

The webhook should be set to:
```
https://api-booking-room.tkilocal.biz.id/webhook/telegram/<YOUR_BOT_TOKEN>
```

Where `<YOUR_BOT_TOKEN>` is your actual bot token from @BotFather.

## Common Issues & Solutions

### Issue: "Webhook endpoint is not accessible"
**Cause**: The server at `api-booking-room.tkilocal.biz.id` is not reachable from Telegram's servers.

**Solutions**:
1. Verify the server is running: `curl https://api-booking-room.tkilocal.biz.id/health`
2. Check firewall rules allow incoming HTTPS traffic
3. Verify DNS resolution works
4. Check if SSL certificate is valid

### Issue: "Bot token is invalid"
**Cause**: Wrong or expired bot token.

**Solution**:
1. Get a new token from @BotFather
2. Update Consul configuration
3. Restart the application
4. Reset webhook with new token

### Issue: Webhook has errors in Telegram
**Cause**: Server is returning errors when processing webhook updates.

**Solution**:
1. Check application logs for errors
2. Ensure all dependencies are installed
3. Verify MongoDB connection
4. Check Consul configuration is loaded correctly

## Monitoring

After fixing, you should monitor:

1. **Incoming webhook logs**: The application should log all incoming Telegram updates
2. **Error rates**: Check for any errors in webhook processing
3. **Response times**: Ensure webhook endpoint responds quickly

## Testing Commands

Once fixed, test these commands in Telegram:

1. `/start` - Should show welcome message
2. `/help` - Should show help information
3. `/authorize <code>` - Should work with a valid 6-digit code from frontend

## Additional Resources

- Telegram Bot API Documentation: https://core.telegram.org/bots/api
- Webhook Documentation: https://core.telegram.org/bots/api#setwebhook
- BotFather: @BotFather in Telegram (to get/reset bot token)

## Next Steps

1. Run `python check_webhook_status.py` with your bot token
2. Review the output to identify the specific issue
3. Apply the appropriate fix from the scenarios above
4. Test the bot commands in Telegram
5. If issues persist, check application logs for detailed error information
# Vercel Deployment Guide

This guide will walk you through deploying your Booking Room Backend API to Vercel.

## Prerequisites

Before deploying, make sure you have:
- [x] MongoDB Atlas account and cluster set up
- [x] Telegram Bot Token (from @BotFather)
- [x] Vercel account
- [x] Git repository connected to Vercel

## Environment Variables

You need to configure the following environment variables in Vercel:

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key (minimum 32 characters) | `your-secure-random-secret-key-here` |
| `MONGODB_URL` | MongoDB Atlas connection string | `mongodb+srv://user:pass@cluster.mongodb.net/booking_app?retryWrites=true&w=majority` |
| `MONGODB_DB_NAME` | Database name | `booking_app` |
| `BOT_TOKEN` | Telegram bot token from @BotFather | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `WEBHOOK_BASE_URL` | Your Vercel app URL | `https://your-app-name.vercel.app` |
| `ADMIN_TELEGRAM_ID` | Your Telegram user ID | `123456789` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment mode | `production` |
| `FRONTEND_URL` | Frontend URL for CORS | `https://booking-meeting-flax.vercel.app` |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT expiration time | `10080` (7 days) |

## MongoDB Atlas Setup

If you haven't set up MongoDB Atlas yet:

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account (if you don't have one)
3. Create a new cluster (Free tier is sufficient)
4. Create a database user:
   - Go to Database Access → Add New Database User
   - Choose Password authentication
   - Save username and password
5. Configure Network Access:
   - Go to Network Access → Add IP Address
   - Allow access from anywhere: `0.0.0.0/0` (required for Vercel)
6. Get connection string:
   - Click "Connect" → "Drivers"
   - Copy the connection string
   - Replace `<password>` with your database password
   - Replace `<dbname>` with `booking_app`

Example connection string:
```
mongodb+srv://myuser:mypassword@cluster0.abc12.mongodb.net/booking_app?retryWrites=true&w=majority
```

## Deployment Steps

### Option 1: Deploy via Vercel Dashboard (Recommended)

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for Vercel deployment"
   git push origin main
   ```

2. **Create Vercel Project**
   - Go to [Vercel Dashboard](https://vercel.com/dashboard)
   - Click "Add New Project"
   - Import your GitHub repository

3. **Configure Project**
   - **Framework Preset**: Python
   - **Root Directory**: `./` (leave as is)
   - **Build Command**: (leave empty - Vercel will auto-detect)
   - **Output Directory**: (leave empty)

4. **Add Environment Variables**
   - Click "Environment Variables"
   - Add all the required variables from the table above
   - Click "Save"

5. **Deploy**
   - Click "Deploy"
   - Wait for the deployment to complete (2-3 minutes)

6. **Get Your URL**
   - After deployment, Vercel will provide a URL like: `https://your-project-name.vercel.app`
   - Update your `WEBHOOK_BASE_URL` environment variable if needed

### Option 2: Deploy via Vercel CLI

1. **Install Vercel CLI**
   ```bash
   npm install -g vercel
   ```

2. **Login to Vercel**
   ```bash
   vercel login
   ```

3. **Deploy**
   ```bash
   vercel
   ```

4. **Follow the prompts** and add environment variables when asked

5. **Set up production environment variables**
   ```bash
   vercel env add SECRET_KEY production
   vercel env add MONGODB_URL production
   # ... add all other variables
   ```

6. **Deploy to production**
   ```bash
   vercel --prod
   ```

## Post-Deployment Configuration

### 1. Verify the Deployment

Check if your API is running:
```bash
curl https://your-app-name.vercel.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "booking-room-backend"
}
```

### 2. Test API Endpoints

Test your API endpoints:
```bash
# Root endpoint
curl https://your-app-name.vercel.app/

# Health check
curl https://your-app-name.vercel.app/health

# API docs
# Visit: https://your-app-name.vercel.app/docs
```

### 3. Configure Telegram Bot Webhook

The bot will automatically set the webhook on deployment. However, you can verify it:

```bash
# Get current webhook info
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
```

Expected response should show your Vercel webhook URL:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-app-name.vercel.app/webhook/telegram/<YOUR_BOT_TOKEN>",
    "has_custom_certificate": false,
    "use_independent_mode": false,
    "pending_update_count": 0
  }
}
```

### 4. Test Telegram Bot

1. Open your Telegram bot
2. Send `/start` command
3. You should receive a welcome message

## Troubleshooting

### Bot Not Responding

If the Telegram bot is not responding:

1. **Check webhook status**:
   ```bash
   curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo
   ```

2. **Check Vercel function logs**:
   - Go to Vercel Dashboard → Your Project → Logs
   - Look for errors in the function execution

3. **Verify webhook URL**:
   - Make sure `WEBHOOK_BASE_URL` matches your Vercel URL
   - Re-deploy if needed

### Database Connection Errors

If you see database connection errors:

1. **Check MongoDB Atlas Network Access**:
   - Ensure IP `0.0.0.0/0` is allowed
   - Verify database user has correct permissions

2. **Check connection string**:
   - Verify username and password are correct
   - Ensure the database name is correct

3. **Check environment variables**:
   - Verify `MONGODB_URL` is set correctly in Vercel
   - Re-deploy if needed

### CORS Errors

If you see CORS errors:

1. **Check `FRONTEND_URL`**:
   - Ensure it matches your frontend URL exactly
   - Include `https://` protocol

2. **Re-deploy** after updating environment variables

## Custom Domain (Optional)

If you want to use a custom domain:

1. **Go to Vercel Dashboard** → Your Project → Settings → Domains
2. **Add your domain**
3. **Update DNS records** as instructed by Vercel
4. **Update `WEBHOOK_BASE_URL`** to your custom domain
5. **Update `FRONTEND_URL`** if needed

## Monitoring and Logs

### View Logs

- **Vercel Dashboard**: Your Project → Logs
- **Real-time logs**: Click "Live" in the logs tab

### Performance Monitoring

- Vercel provides built-in analytics
- Monitor function execution time
- Check for errors and warnings

## Updates and Redeployment

To update your application:

1. Make changes to your code
2. Commit and push to GitHub
3. Vercel will automatically detect and redeploy
4. Or use Vercel CLI: `vercel --prod`

## Local Development with Vercel Config

To test locally with the same configuration:

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your environment variables
cp .env.example .env

# Run locally
uvicorn app.main:app --reload
```

Note: For local development, the Telegram bot will use webhook mode. If you prefer polling for local development, you can modify the `lifespan` function in `app/main.py`.

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use strong secrets** for `SECRET_KEY`
3. **Limit MongoDB Atlas access** to necessary IPs when possible
4. **Keep dependencies updated**: Run `pip install --upgrade -r requirements.txt` regularly
5. **Monitor logs** for suspicious activity
6. **Use HTTPS** (Vercel provides this by default)

## Support

If you encounter issues:

1. Check Vercel logs for error messages
2. Review MongoDB Atlas logs
3. Verify all environment variables are set correctly
4. Check Telegram Bot API status: https://core.telegram.org/bots/api

## Summary

Your FastAPI backend is now ready for Vercel deployment with:
- ✅ Serverless function support
- ✅ Webhook-based Telegram bot (no polling)
- ✅ MongoDB Atlas integration
- ✅ Production-ready configuration
- ✅ Automatic CORS handling

Good luck with your deployment! 🚀
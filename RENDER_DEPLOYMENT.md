# Render.com Deployment Guide

This guide will help you deploy the Booking Room Backend API to Render.com.

## Why Render.com?

After multiple attempts with Vercel, we've switched to Render.com because:
- ✅ Native FastAPI support (no complex configuration needed)
- ✅ Simple deployment process
- ✅ Free tier available
- ✅ Automatic HTTPS and SSL certificates
- ✅ Better Python/ASGI app support
- ✅ No `issubclass` errors or complex handler issues

## Prerequisites

1. **Render.com Account** - Sign up at [render.com](https://render.com)
2. **GitHub Repository** - Your code should be on GitHub
3. **MongoDB Atlas** - For database hosting (free tier available)

## Step-by-Step Deployment

### Step 1: Create Render Account

1. Go to [render.com](https://render.com)
2. Click "Sign Up"
3. Sign up with GitHub (recommended) or email

### Step 2: Create New Web Service

1. After logging in, click **"New +"** button
2. Select **"Web Service"**
3. Click **"Connect"** next to your GitHub repository
4. If prompted, authorize Render to access your GitHub
5. Select your `booking-room-be` repository
6. Click **"Connect"**

### Step 3: Configure Build and Deploy

Render will auto-detect most settings. Verify these:

**Build & Deploy:**
- **Name**: `booking-room-be` (or your preferred name)
- **Region**: Choose region closest to your users
- **Branch**: `main`
- **Runtime**: `Python 3.12.0` (should auto-detect from `render.yaml`)

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 4: Set Environment Variables

Scroll down to **"Environment"** section and add these variables:

| Variable | Value | Required |
|----------|-------|----------|
| `SECRET_KEY` | Generate a random string | ✅ Yes |
| `MONGODB_URL` | Your MongoDB connection string | ✅ Yes |
| `MONGODB_DB_NAME` | Your database name | ✅ Yes |
| `BOT_TOKEN` | Your Telegram bot token | ✅ Yes |
| `WEBHOOK_BASE_URL` | Your Render app URL | ✅ Yes |
| `ADMIN_TELEGRAM_ID` | Your Telegram user ID | ✅ Yes |
| `FRONTEND_URL` | Your frontend URL | ✅ Yes |
| `PYTHON_VERSION` | `3.12.0` | ✅ Yes |

**Generating SECRET_KEY:**
```bash
openssl rand -hex 32
```

**MongoDB URL Format:**
```
mongodb+srv://username:password@cluster.mongodb.net/database_name?retryWrites=true&w=majority
```

**WEBHOOK_BASE_URL:**
After deployment, this will be: `https://booking-room-be.onrender.com`
(Use your actual Render app URL)

### Step 5: Choose Plan

Select **"Free"** plan:
- 512 MB RAM
- 0.1 CPU
- Sufficient for development and testing
- Automatic sleep after 15 minutes of inactivity (free tier only)

### Step 6: Deploy

Click **"Create Web Service"** button

Render will:
1. Build your application
2. Install dependencies
3. Start the server
4. Deploy to production

This typically takes 2-5 minutes.

### Step 7: Monitor Deployment

1. Click on your web service
2. Go to **"Events"** tab
3. Watch the deployment progress
4. Look for **"Live"** status

### Step 8: Test Your Deployment

Once deployed, test your endpoints:

```bash
# Health check
curl https://booking-room-be.onrender.com/health

# Root endpoint
curl https://booking-room-be.onrender.com/

# API docs (should work in browser)
https://booking-room-be.onrender.com/docs
```

Replace `booking-room-be.onrender.com` with your actual Render URL.

### Step 9: Update Webhook URL

After deployment, update your Telegram webhook:

1. Get your Render URL from Render dashboard
2. Update `WEBHOOK_BASE_URL` environment variable in Render
3. Your webhook URL will be: `https://booking-room-be.onrender.com/webhook/telegram/YOUR_BOT_TOKEN`
4. Set webhook via Telegram Bot API or the app will set it automatically

## Accessing Logs

To view logs:

1. Go to your web service in Render
2. Click **"Logs"** tab
3. View real-time logs
4. Filter by log level (Error, Warning, Info)

## Common Issues and Solutions

### Issue: Deployment Fails - Module Not Found

**Solution:**
- Check `requirements.txt` includes all necessary packages
- Verify package names are correct
- Check logs for specific missing module

### Issue: Database Connection Failed

**Solution:**
- Verify `MONGODB_URL` is correct
- Check MongoDB Atlas allows access from everywhere (`0.0.0.0/0`)
- Verify database user has correct permissions
- Check connection string format

### Issue: Bot Not Responding

**Solution:**
- Verify `BOT_TOKEN` is correct
- Check `WEBHOOK_BASE_URL` matches your Render URL
- Check logs for webhook errors
- Manually set webhook using Telegram API

### Issue: Free Tier Sleeps

**Solution:**
- Free tier sleeps after 15 minutes of inactivity
- First request after sleep takes longer (~30 seconds)
- Upgrade to Starter plan ($5/month) to prevent sleep

## Updating Your Application

To update your application:

1. Make changes locally
2. Commit to Git:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```
3. Render automatically detects the push
4. New deployment starts automatically
5. Monitor in Events tab

## Environment Variables in Development

For local development, create `.env` file:

```bash
cp .env.example .env
```

Edit `.env` with your local settings.

## Performance Tips

1. **Use Connection Pooling** - Already implemented with Motor
2. **Enable Caching** - Consider adding Redis for frequent queries
3. **Optimize Database Queries** - Use indexes in MongoDB
4. **Monitor Logs** - Regularly check for slow operations

## Monitoring and Metrics

Render provides:
- CPU usage
- Memory usage
- Response times
- Request counts
- Error rates

Access these in your web service dashboard.

## Scaling

To scale your application:

1. Go to your web service
2. Click **"Settings"**
3. Scroll to **"Instances"**
4. Change CPU and RAM limits
5. Save changes (triggers redeploy)

## Backup and Recovery

- **Database Backups** - MongoDB Atlas provides automated backups
- **Code** - Stored in GitHub
- **Environment Variables** - Saved in Render

## Cost Estimate

- **Free Tier**: $0/month
  - 512 MB RAM
  - 0.1 CPU
  - Sleeps after 15 minutes inactivity
  
- **Starter**: $7/month
  - 512 MB RAM
  - 0.5 CPU
  - No sleep
  - Better performance

## Support

- **Render Documentation**: [docs.render.com](https://docs.render.com)
- **FastAPI Docs**: [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **MongoDB Atlas Docs**: [docs.atlas.mongodb.com](https://docs.atlas.mongodb.com)

## Next Steps

1. ✅ Complete deployment to Render
2. ✅ Test all API endpoints
3. ✅ Verify Telegram bot functionality
4. ✅ Set up monitoring and alerts
5. ✅ Configure backup strategies
6. ✅ Document API for frontend team

---

**Congratulations!** Your FastAPI application is now deployed on Render.com 🚀
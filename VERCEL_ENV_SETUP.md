# How to Setup Environment Variables in Vercel

This guide shows you exactly where and how to configure environment variables in Vercel for your Booking Room Backend deployment.

## Step-by-Step Guide

### Step 1: Access Your Project Settings

1. **Go to Vercel Dashboard**
   - Visit: https://vercel.com/dashboard
   - Login if needed

2. **Select Your Project**
   - Find your booking-room-be project
   - Click on it to open the project overview

### Step 2: Navigate to Environment Variables

**Option A: During Project Setup (First Time Deployment)**
1. After importing your GitHub repository
2. Scroll down to **"Environment Variables"** section
3. Click **"+ Add New"** button for each variable

**Option B: After Project is Created**
1. Click on the **"Settings"** tab at the top of the project page
2. Click on **"Environment Variables"** in the left sidebar menu

### Step 3: Add Each Environment Variable

For each variable, you need to provide:
- **Name**: The variable name (exact match required)
- **Value**: The actual value
- **Environment**: Choose which environment(s) to apply to

#### Variable 1: SECRET_KEY
```
Name: SECRET_KEY
Value: your-secure-random-secret-key-minimum-32-characters-long
Environment: Production, Preview, Development (all)
```

**How to generate a secure SECRET_KEY:**
```bash
# Run this command to generate a random key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Variable 2: MONGODB_URL
```
Name: MONGODB_URL
Value: mongodb+srv://username:password@cluster.mongodb.net/booking_app?retryWrites=true&w=majority
Environment: Production, Preview, Development (all)
```

**How to get your MongoDB URL:**
1. Go to MongoDB Atlas Dashboard
2. Click "Connect" on your cluster
3. Choose "Connect your application"
4. Copy the connection string
5. Replace `<password>` with your database password

#### Variable 3: MONGODB_DB_NAME
```
Name: MONGODB_DB_NAME
Value: booking_app
Environment: Production, Preview, Development (all)
```

#### Variable 4: BOT_TOKEN
```
Name: BOT_TOKEN
Value: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
Environment: Production, Preview, Development (all)
```

**How to get your BOT_TOKEN:**
1. Open Telegram and search for @BotFather
2. Send `/newbot` command
3. Follow the instructions
4. Copy the token provided (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Variable 5: WEBHOOK_BASE_URL
```
Name: WEBHOOK_BASE_URL
Value: https://your-project-name.vercel.app
Environment: Production, Preview, Development (all)
```

**Important:**
- Deploy your project first to get the Vercel URL
- Then come back and update this variable
- The URL will look like: `https://booking-room-be.vercel.app`
- **Do NOT** include `/webhook/telegram/...` in this variable
- Just use the base URL

#### Variable 6: ADMIN_TELEGRAM_ID
```
Name: ADMIN_TELEGRAM_ID
Value: 123456789
Environment: Production, Preview, Development (all)
```

**How to get your Telegram ID:**
1. Open Telegram and search for @userinfobot
2. Send any message to the bot
3. It will reply with your user ID
4. Copy the number (e.g., `123456789`)

### Step 4: Save the Variables

1. After adding all variables, click **"Save"** button
2. Wait for the confirmation message

### Step 5: Redeploy (If Project Already Exists)

If you already deployed the project before adding variables:

1. Go to **"Deployments"** tab
2. Find the latest deployment
3. Click the three dots (⋮) menu
4. Select **"Redeploy"**
5. Check the box **"This is a production deployment"** if needed
6. Click **"Redeploy"**

Or use the Vercel CLI:
```bash
vercel --prod
```

## Environment Types Explained

Vercel has three environments:

1. **Production**: Live production environment
   - URL: `https://your-project.vercel.app`
   - Used for actual users

2. **Preview**: Created for each git branch/PR
   - URL: `https://your-branch-name.vercel.app`
   - Used for testing changes

3. **Development**: Local development with Vercel CLI
   - Used when running `vercel dev`

**Recommendation:** For a simple deployment, add variables to **all three environments**.

## Using Vercel CLI (Alternative Method)

If you prefer using the command line:

### 1. Install Vercel CLI
```bash
npm install -g vercel
```

### 2. Login
```bash
vercel login
```

### 3. Add Environment Variables
```bash
# Add SECRET_KEY
vercel env add SECRET_KEY
# Select: Production, Preview, and Development
# Paste the value when prompted

# Add MONGODB_URL
vercel env add MONGODB_URL
# Select: Production, Preview, and Development
# Paste the value when prompted

# Add MONGODB_DB_NAME
vercel env add MONGODB_DB_NAME
# Select: Production, Preview, and Development
# Paste: booking_app

# Add BOT_TOKEN
vercel env add BOT_TOKEN
# Select: Production, Preview, and Development
# Paste your bot token

# Add WEBHOOK_BASE_URL
vercel env add WEBHOOK_BASE_URL
# Select: Production, Preview, and Development
# Paste your Vercel URL

# Add ADMIN_TELEGRAM_ID
vercel env add ADMIN_TELEGRAM_ID
# Select: Production, Preview, and Development
# Paste your Telegram ID
```

### 4. Deploy
```bash
vercel --prod
```

## Verifying Environment Variables

### Method 1: Check in Vercel Dashboard

1. Go to **Settings** → **Environment Variables**
2. You should see all your variables listed
3. Click the eye icon to view values (hidden by default)

### Method 2: Check via Health Endpoint

After deployment, test if variables are loaded:

```bash
curl https://your-project.vercel.app/health
```

If the API responds correctly, environment variables are loaded properly.

### Method 3: Check Vercel Logs

1. Go to **Deployments** tab
2. Click on a deployment
3. Click the **"Logs"** tab
4. Look for any environment variable errors

## Common Issues & Solutions

### Issue: Variables Not Working After Deployment

**Solution:**
1. Check variable names match exactly (case-sensitive)
2. Verify you added variables to the correct environment
3. Make sure you redeployed after adding variables
4. Check Vercel logs for errors

### Issue: MongoDB Connection Failed

**Solution:**
1. Verify `MONGODB_URL` format is correct
2. Check username and password are correct
3. Ensure MongoDB Atlas allows `0.0.0.0/0` IP access
4. Check if cluster is in MongoDB Atlas

### Issue: Telegram Bot Not Responding

**Solution:**
1. Verify `BOT_TOKEN` is correct
2. Check `WEBHOOK_BASE_URL` matches your Vercel URL exactly
3. Ensure webhook was set successfully (check logs)
4. Test with: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo`

### Issue: CORS Errors

**Solution:**
1. Verify `FRONTEND_URL` is set correctly
2. Ensure it includes `https://` protocol
3. Check it matches your frontend URL exactly

## Best Practices

1. **Use different values for different environments** when needed
2. **Never commit `.env` file** to git
3. **Use strong secrets** for `SECRET_KEY`
4. **Rotate secrets** periodically
5. **Limit access** to environment variables in team settings
6. **Document your variables** (like this guide!)

## Quick Reference: All Required Variables

| Variable | Example Value | Notes |
|----------|---------------|-------|
| `SECRET_KEY` | `abc123xyz...` (min 32 chars) | Generate with Python secrets module |
| `MONGODB_URL` | `mongodb+srv://user:pass@...` | From MongoDB Atlas |
| `MONGODB_DB_NAME` | `booking_app` | Your database name |
| `BOT_TOKEN` | `123456789:ABC...` | From @BotFather |
| `WEBHOOK_BASE_URL` | `https://your-app.vercel.app` | Base URL only |
| `ADMIN_TELEGRAM_ID` | `123456789` | From @userinfobot |

## Summary

To setup environment variables in Vercel:
1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Click "+ Add New"
3. Add each of the 6 required variables
4. Click "Save"
5. Redeploy if needed

That's it! Your environment variables are now configured and ready for deployment. 🚀
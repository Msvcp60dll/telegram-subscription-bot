# 🚀 DEPLOYMENT INSTRUCTIONS

## Why Manual Steps Are Required

Some deployment steps require manual intervention because:

1. **Railway Authentication**: Railway requires browser-based OAuth login for security
2. **Airwallex Dashboard**: Webhook configuration must be done in their web interface
3. **Security**: API tokens should never be hardcoded for production systems

---

## Option 1: Railway CLI Deployment (Recommended)

### Step 1: Install Railway CLI
```bash
brew install railway
```

### Step 2: Login to Railway
```bash
railway login
# This opens a browser for authentication
```

### Step 3: Run Automated Deployment
```bash
cd ~/TGbot
./deploy_now.sh
```

This script will:
- Link to your Railway project
- Set all environment variables
- Deploy from GitHub
- Provide deployment URL

---

## Option 2: Railway Dashboard (Web UI)

### Step 1: Open Railway Dashboard
Go to: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c

### Step 2: Connect GitHub
1. Click **"New Service"** or **"Deploy"**
2. Select **"Deploy from GitHub repo"**
3. Choose: `Msvcp60dll/telegram-subscription-bot`
4. Branch: `main`
5. Enable **"Auto Deploy"**

### Step 3: Set Environment Variables
1. Go to **Variables** tab
2. Click **"Raw Editor"**
3. Paste this block:

```env
BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o
GROUP_ID=-1002384609773
ADMIN_USER_ID=306145881
SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1
AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47
ADMIN_PASSWORD=TGBot2024Secure!
WEBHOOK_PORT=8080
PYTHONUNBUFFERED=1
```

### Step 4: Generate Public Domain
1. Go to **Settings** → **Networking**
2. Click **"Generate Domain"**
3. Copy your URL (e.g., `https://telegram-subscription-bot.up.railway.app`)

### Step 5: Add Webhook URL
Add this variable with your Railway URL:
```
WEBHOOK_BASE_URL=https://your-app.up.railway.app
```

---

## Option 3: Railway API Deployment

### Step 1: Get Railway API Token
1. Go to: https://railway.app/account/tokens
2. Create a new token
3. Set as environment variable:

```bash
export RAILWAY_API_TOKEN=your_token_here
```

### Step 2: Run API Deployment
```bash
cd ~/TGbot
python scripts/auto_deploy_railway.py
```

---

## Post-Deployment Steps

### 1. Verify Deployment
```bash
# Check logs
railway logs --follow

# Test bot
# Open Telegram and message @Msvcp60dllgoldbot
# Send: /start
```

### 2. Configure Airwallex Webhook
1. Go to Airwallex Dashboard
2. Navigate to Webhooks section
3. Create new endpoint:
   - URL: `https://your-railway-url.up.railway.app/webhook/airwallex`
   - Events: 
     - payment_intent.succeeded
     - payment_intent.failed
     - payment_link.paid
4. Copy webhook secret
5. Add to Railway:
```bash
railway variables set AIRWALLEX_WEBHOOK_SECRET=your_secret --yes
```

### 3. Run Production Tests
```bash
cd ~/TGbot
python scripts/verify_deployment.py
python scripts/production_tests.py --all
```

### 4. Migrate Existing Members
```bash
# Test migration
python scripts/production_migration.py --file sample_users_test.json --dry-run

# Run actual migration (when ready)
python scripts/production_migration.py --file your_members.json
```

---

## Quick Reference

### View Logs
```bash
railway logs --follow
```

### Check Status
```bash
railway status
```

### Restart Service
```bash
railway restart
```

### Update Code
```bash
git add .
git commit -m "Update"
git push origin main
# Railway auto-deploys
```

---

## Troubleshooting

### "Unauthorized" Error
```bash
railway login
```

### Deployment Failed
1. Check logs: `railway logs`
2. Verify environment variables
3. Check build logs in Railway dashboard

### Bot Not Responding
1. Verify bot token is correct
2. Check if bot is running: `railway status`
3. Look for errors: `railway logs --tail 100`

---

## Support Links

- Railway Dashboard: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
- GitHub Repo: https://github.com/Msvcp60dll/telegram-subscription-bot
- Railway Docs: https://docs.railway.app
- Telegram Bot: @Msvcp60dllgoldbot

---

## Why Some Steps Can't Be Automated

1. **OAuth Authentication**: Railway and GitHub require secure browser-based login
2. **API Token Security**: Production tokens shouldn't be stored in code
3. **Webhook Configuration**: Airwallex requires manual dashboard configuration
4. **Domain Generation**: Railway generates unique URLs that must be retrieved after deployment
5. **Payment Provider Security**: Webhook secrets must be manually configured for security

The provided scripts automate everything technically possible while maintaining security best practices.
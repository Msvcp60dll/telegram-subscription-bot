# Telegram Subscription Bot - Railway Deployment Instructions

## Deployment Status
✅ **GitHub Repository Created**: https://github.com/Msvcp60dll/telegram-subscription-bot  
⏳ **Railway Deployment**: Ready for manual configuration

## Quick Start Deployment

### Step 1: Connect to Railway Project

1. **Open Railway Dashboard**:
   ```
   https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
   ```

2. **Connect GitHub Repository**:
   - Click "New Service" or select your existing service
   - Choose "Deploy from GitHub repo"
   - Authorize Railway if prompted
   - Select repository: `Msvcp60dll/telegram-subscription-bot`
   - Select branch: `main`
   - Enable "Auto Deploy" ✅

### Step 2: Set Environment Variables

#### Option A: Via Railway Dashboard (Recommended)
1. Go to your service in Railway
2. Click on "Variables" tab
3. Click "Raw Editor" button
4. Paste the following configuration:

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
PYTHONDONTWRITEBYTECODE=1
```

5. Click "Update Variables"
6. Railway will automatically redeploy

#### Option B: Via Railway CLI
```bash
# First, link your project
railway link e57ef125-1237-45b2-82a0-83df6d0b375c

# Then run the setup script
./setup_railway_env.sh
```

### Step 3: Get Your Production URL

After deployment starts:
1. Go to your service → "Settings" tab
2. Under "Networking" section, click "Generate Domain"
3. Your URL will be something like: `https://telegram-subscription-bot-production.up.railway.app`
4. Copy this URL

### Step 4: Update Webhook URL

1. Go back to "Variables" tab
2. Add new variable:
   ```
   WEBHOOK_BASE_URL=https://your-production-url.up.railway.app
   ```
3. Railway will redeploy automatically

### Step 5: Verify Deployment

1. **Check Logs**:
   ```bash
   railway logs --tail 50
   ```
   
   Or view in dashboard: Deployments → Click on active deployment → View logs

2. **Expected Log Output**:
   ```
   Starting Telegram Subscription Bot...
   Database connection established
   Bot started successfully
   Webhook set to: https://your-url.up.railway.app/webhook
   Admin dashboard available at: /admin
   ```

3. **Test the Bot**:
   - Open Telegram
   - Search for your bot
   - Send `/start` command
   - Bot should respond

4. **Test Admin Dashboard**:
   - Navigate to: `https://your-url.up.railway.app/admin`
   - Login with password: `TGBot2024Secure!`

## Production URLs and Access Points

| Service | URL | Status |
|---------|-----|--------|
| GitHub Repository | https://github.com/Msvcp60dll/telegram-subscription-bot | ✅ Active |
| Railway Project | https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c | ⏳ Configure |
| Production URL | Will be generated after deployment | ⏳ Pending |
| Admin Dashboard | `[Production-URL]/admin` | ⏳ Pending |
| Health Check | `[Production-URL]/health` | ⏳ Pending |
| Webhook Endpoint | `[Production-URL]/webhook/airwallex` | ⏳ Pending |

## Deployment Commands Reference

### Railway CLI Commands
```bash
# Link to project
railway link e57ef125-1237-45b2-82a0-83df6d0b375c

# Deploy from local
railway up

# View logs
railway logs
railway logs --tail 100
railway logs --follow

# Check status
railway status

# List variables
railway variables

# Open dashboard
railway open
```

### Git Commands for Updates
```bash
# Make changes and deploy
git add .
git commit -m "Your update message"
git push origin main
# Railway auto-deploys
```

## Monitoring Instructions

### Real-time Monitoring
1. **Via Dashboard**:
   - Go to your Railway project
   - Click on your service
   - View "Metrics" tab for CPU/Memory usage
   - View "Logs" tab for application logs

2. **Via CLI**:
   ```bash
   # Follow logs in real-time
   railway logs --follow
   
   # Check last 100 lines
   railway logs --tail 100
   ```

### Health Checks
- Health endpoint: `https://[your-url].up.railway.app/health`
- Should return: `{"status": "healthy", "timestamp": "..."}`

### Key Metrics to Monitor
- **CPU Usage**: Should stay below 80%
- **Memory Usage**: Should stay below 450MB
- **Response Time**: Webhook responses < 2s
- **Error Rate**: Should be < 1%

## Rollback Procedures

### Method 1: Quick Rollback (Railway Dashboard)
1. Go to "Deployments" tab
2. Find the last working deployment
3. Click "..." menu → "Rollback to this deployment"
4. Confirm rollback

### Method 2: Git Revert
```bash
# Revert last commit
git revert HEAD
git push origin main

# Or reset to specific commit
git log --oneline  # Find commit hash
git revert [commit-hash]
git push origin main
```

### Method 3: Railway CLI
```bash
# List deployments
railway deployments

# Rollback to specific deployment
railway deployments rollback [deployment-id]
```

## Troubleshooting Guide

### Issue: Bot Not Responding
**Symptoms**: Bot doesn't reply to commands
**Solutions**:
1. Check BOT_TOKEN is correct
2. Verify webhook URL is set: Check logs for "Webhook set to:"
3. Ensure bot is not already running elsewhere
4. Check Railway logs for errors

### Issue: Database Connection Failed
**Symptoms**: "Database connection failed" in logs
**Solutions**:
1. Verify SUPABASE_URL format
2. Check SUPABASE_SERVICE_KEY is correct
3. Test connection from Supabase dashboard
4. Check if Supabase project is active

### Issue: Webhook Not Working
**Symptoms**: Payments not updating
**Solutions**:
1. Verify WEBHOOK_BASE_URL is set correctly
2. Check webhook endpoint: `curl https://[your-url]/webhook/airwallex`
3. Verify Airwallex webhook configuration
4. Check logs for webhook errors

### Issue: Build Failed
**Symptoms**: Deployment fails during build
**Solutions**:
1. Check requirements.txt syntax
2. Verify Python version in runtime.txt
3. Check build logs for specific errors
4. Try deploying from local: `railway up`

## Security Reminders

⚠️ **Important Security Notes**:
1. Never commit `.env` files to Git
2. Rotate API keys regularly
3. Use Railway's environment variables for all secrets
4. Enable 2FA on GitHub and Railway accounts
5. Monitor access logs regularly

## Support Resources

### Documentation
- [Railway Docs](https://docs.railway.com)
- [Project Repository](https://github.com/Msvcp60dll/telegram-subscription-bot)
- [Local Setup Docs](/docs/railway-setup.md)

### Get Help
- Railway Discord: https://discord.gg/railway
- Railway Support: support@railway.app
- GitHub Issues: https://github.com/Msvcp60dll/telegram-subscription-bot/issues

## Next Steps After Deployment

1. ✅ **Configure Airwallex Webhook**:
   - Log into Airwallex dashboard
   - Set webhook URL to: `https://[your-production-url]/webhook/airwallex`
   - Save webhook secret if provided

2. ✅ **Test Payment Flow**:
   - Create a test subscription
   - Process a test payment
   - Verify webhook receives notification

3. ✅ **Set Up Monitoring**:
   - Enable Railway notifications
   - Set up uptime monitoring (e.g., UptimeRobot)
   - Configure error alerting

4. ✅ **Documentation**:
   - Document your production URL
   - Update team with access instructions
   - Create runbook for common issues

## Files and Scripts

| File | Purpose | Location |
|------|---------|----------|
| `railway.toml` | Railway configuration | `/Users/antongladkov/TGbot/railway.toml` |
| `railway_deploy.sh` | Deployment guide script | `/Users/antongladkov/TGbot/railway_deploy.sh` |
| `setup_railway_env.sh` | Environment setup script | `/Users/antongladkov/TGbot/setup_railway_env.sh` |
| `docs/railway-setup.md` | Detailed documentation | `/Users/antongladkov/TGbot/docs/railway-setup.md` |
| `requirements.txt` | Python dependencies | `/Users/antongladkov/TGbot/requirements.txt` |

---

## Summary

✅ **Completed**:
- GitHub repository created and code pushed
- Railway configuration files prepared
- Environment variable setup scripts created
- Comprehensive documentation prepared

⏳ **Action Required**:
1. Open Railway dashboard: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
2. Connect GitHub repository
3. Set environment variables (use the provided configuration above)
4. Get production URL after deployment
5. Update WEBHOOK_BASE_URL with production URL

📝 **Important URLs**:
- **GitHub Repository**: https://github.com/Msvcp60dll/telegram-subscription-bot
- **Railway Project**: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
- **Production URL**: Will be available after deployment

---
*Deployment prepared on: 2025-09-03*
*Documentation version: 1.0.0*
# Railway Deployment Setup Documentation

## Project Information
- **Railway Project ID**: `e57ef125-1237-45b2-82a0-83df6d0b375c`
- **GitHub Repository**: https://github.com/Msvcp60dll/telegram-subscription-bot
- **Service Type**: Telegram Bot (Python)
- **Deployment Date**: 2025-09-03

## Prerequisites

### Required Tools
- Railway CLI (installed)
- GitHub CLI (installed)
- Git (configured)

### Account Requirements
- Railway account with project created
- GitHub account with repository access
- Telegram Bot Token from BotFather

## Configuration Files

### railway.toml
Located at project root, defines build and deployment configuration:
- **Builder**: Nixpacks (automatic Python detection)
- **Start Command**: `python main.py`
- **Health Check**: `/health` endpoint
- **Restart Policy**: Always restart on failure
- **Region**: us-west1

### Environment Variables

#### Required Variables
```bash
# Bot Configuration
BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o
GROUP_ID=-1002384609773
ADMIN_USER_ID=306145881

# Database Configuration
SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1

# Payment Integration
AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47

# Admin Configuration
ADMIN_PASSWORD=TGBot2024Secure!

# Webhook Configuration
WEBHOOK_BASE_URL=[AUTO-SET-AFTER-DEPLOYMENT]
WEBHOOK_PORT=8080

# Python Optimization
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
```

## Deployment Steps

### Step 1: Connect to Railway Project

#### Via Railway Dashboard
1. Navigate to: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
2. Click on "New Service" or select existing service
3. Choose "GitHub Repo" as source
4. Authorize Railway to access GitHub if not already done
5. Select repository: `Msvcp60dll/telegram-subscription-bot`
6. Select branch: `main`
7. Enable "Auto Deploy" for automatic deployments

#### Via Railway CLI
```bash
# Link local project to Railway
railway link e57ef125-1237-45b2-82a0-83df6d0b375c

# Deploy from local directory (optional)
railway up
```

### Step 2: Configure Environment Variables

#### Via Dashboard
1. Go to service settings: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c/service
2. Click on "Variables" tab
3. Add each variable from the list above
4. Click "Add Variable" for each entry
5. Railway will automatically redeploy after variables are saved

#### Via CLI
```bash
# Set variables one by one
railway variables set BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o
railway variables set GROUP_ID=-1002384609773
railway variables set ADMIN_USER_ID=306145881
# ... continue for all variables
```

### Step 3: Monitor Deployment

#### Check Build Logs
```bash
# View real-time logs
railway logs

# View deployment status
railway status
```

#### Dashboard Monitoring
1. Go to Deployments tab in Railway dashboard
2. Click on active deployment to view logs
3. Check for any build or runtime errors

### Step 4: Get Production URL

After successful deployment:
1. Go to service settings → Networking
2. Railway will provide a URL like: `https://[service-name].up.railway.app`
3. Update `WEBHOOK_BASE_URL` environment variable with this URL
4. The service will automatically redeploy with the updated URL

## Post-Deployment Verification

### 1. Check Bot Status
```bash
# View application logs
railway logs --tail 100

# Expected output should show:
# - Database connection successful
# - Bot started successfully
# - Webhook set successfully
```

### 2. Test Bot Functions
- Send `/start` command to bot
- Test subscription commands
- Verify admin dashboard at: `https://[your-url].up.railway.app/admin`

### 3. Verify Webhook
- Check webhook status in logs
- Test payment webhook endpoint: `https://[your-url].up.railway.app/webhook/airwallex`

## Monitoring and Maintenance

### Regular Checks
- **Daily**: Check Railway dashboard for service health
- **Weekly**: Review logs for any errors or warnings
- **Monthly**: Check Railway usage and billing

### Log Management
```bash
# View last 100 lines
railway logs --tail 100

# Follow logs in real-time
railway logs --follow

# Export logs (via dashboard)
# Go to Logs tab → Export
```

### Performance Monitoring
- CPU Usage: Monitor via Railway metrics
- Memory Usage: Check for memory leaks
- Response Time: Monitor webhook response times
- Error Rate: Track failed requests

## Rollback Procedures

### Method 1: Via Railway Dashboard
1. Go to Deployments tab
2. Find previous working deployment
3. Click "..." menu → "Redeploy"
4. Confirm redeployment

### Method 2: Via Git
```bash
# Revert last commit
git revert HEAD
git push origin main

# Or reset to specific commit
git reset --hard [commit-hash]
git push origin main --force
```

### Method 3: Via Railway CLI
```bash
# List recent deployments
railway deployments

# Rollback to specific deployment
railway rollback [deployment-id]
```

## Troubleshooting

### Common Issues

#### 1. Build Failures
- **Issue**: Dependencies not installing
- **Solution**: Check requirements.txt format and versions
- **Command**: `railway logs --build`

#### 2. Bot Not Responding
- **Issue**: Bot doesn't respond to commands
- **Solution**: 
  - Check BOT_TOKEN is correct
  - Verify webhook URL is set
  - Check logs for connection errors

#### 3. Database Connection Failed
- **Issue**: Cannot connect to Supabase
- **Solution**:
  - Verify SUPABASE_URL and SUPABASE_SERVICE_KEY
  - Check network policies in Railway
  - Test connection from local environment

#### 4. Webhook Not Working
- **Issue**: Payment webhooks not received
- **Solution**:
  - Ensure WEBHOOK_BASE_URL is set correctly
  - Check firewall/network settings
  - Verify webhook secret in Airwallex dashboard

### Debug Commands
```bash
# Check environment variables
railway variables

# Test deployment locally
railway run python main.py

# Check service status
railway status

# Open Railway dashboard
railway open
```

## Security Best Practices

### Environment Variables
- Never commit sensitive variables to Git
- Use Railway's variable management
- Rotate API keys regularly
- Use strong passwords for admin access

### Access Control
- Limit GitHub repository access
- Use Railway's team management features
- Enable 2FA on all accounts
- Regularly audit access logs

### Data Protection
- Ensure HTTPS is always used
- Validate all webhook signatures
- Encrypt sensitive data in database
- Regular backup of critical data

## Updates and Maintenance

### Updating Dependencies
```bash
# Update requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push origin main
```

### Updating Bot Code
```bash
# Make changes locally
# Test thoroughly
git add .
git commit -m "Description of changes"
git push origin main
# Railway auto-deploys
```

### Railway Configuration Updates
- Edit railway.toml for configuration changes
- Commit and push to trigger redeployment
- Monitor deployment for any issues

## Support Resources

### Railway Documentation
- Official Docs: https://docs.railway.com
- Config as Code: https://docs.railway.com/deploy/config-as-code
- CLI Reference: https://docs.railway.com/reference/cli-api

### Community Support
- Railway Discord: https://discord.gg/railway
- GitHub Issues: https://github.com/railwayapp/railway
- Stack Overflow: Tag with `railway-app`

### Project-Specific
- GitHub Repository: https://github.com/Msvcp60dll/telegram-subscription-bot
- Local Documentation: /docs directory
- Admin Dashboard: https://[your-url].up.railway.app/admin

## Appendix

### Railway.toml Reference
```toml
[build]
builder = "nixpacks"
buildCommand = "pip install --upgrade pip && pip install -r requirements.txt"
watchPatterns = ["**/*.py", "requirements.txt", "railway.toml"]

[deploy]
numReplicas = 1
startCommand = "python main.py"
healthcheckPath = "/health"
healthcheckTimeout = 300
restartPolicyType = "always"
restartPolicyMaxRetries = 10
region = "us-west1"

[env]
PYTHONUNBUFFERED = "1"
PYTHONDONTWRITEBYTECODE = "1"
```

### Quick Reference Card
```
Project ID: e57ef125-1237-45b2-82a0-83df6d0b375c
GitHub: https://github.com/Msvcp60dll/telegram-subscription-bot
Dashboard: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c
```

---
*Last Updated: 2025-09-03*
*Version: 1.0.0*
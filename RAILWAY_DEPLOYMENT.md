# Railway Deployment Guide for Telegram Subscription Bot

## Overview
This guide provides complete instructions for deploying your Telegram subscription bot to Railway.app, a modern platform-as-a-service that offers simple deployment with automatic scaling and built-in CI/CD.

## Project Configuration
- **Railway Project ID**: `e57ef125-1237-45b2-82a0-83df6d0b375c`
- **Runtime**: Python 3.11
- **Framework**: aiogram 3.4.1
- **Database**: Supabase
- **Payment Provider**: Airwallex

## Prerequisites

### Required Software
1. **Git**: Version control system
   ```bash
   # macOS
   brew install git
   
   # Ubuntu/Debian
   sudo apt-get install git
   
   # Windows
   # Download from https://git-scm.com
   ```

2. **Railway CLI**: Command-line interface for Railway
   ```bash
   # Install via npm
   npm install -g @railway/cli
   
   # Or via install script
   curl -fsSL https://railway.app/install.sh | sh
   ```

3. **Python 3.11+**: Required for local testing
   ```bash
   # Check version
   python3 --version
   ```

### Railway Account
1. Sign up at [railway.app](https://railway.app)
2. Verify your email
3. Optionally upgrade to a paid plan for production use

## Quick Start Deployment

### Option 1: Automated Setup (Recommended)
Run the provided setup script for first-time deployment:

```bash
# Make script executable
chmod +x setup_railway.sh

# Run setup
./setup_railway.sh
```

This script will:
- Install Railway CLI if needed
- Authenticate with Railway
- Initialize git repository
- Link to your Railway project
- Set environment variables
- Perform initial deployment
- Generate admin password

### Option 2: Manual Setup

#### Step 1: Install Railway CLI and Login
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login
```

#### Step 2: Initialize Git Repository
```bash
# Initialize git
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit for Railway deployment"
```

#### Step 3: Link to Railway Project
```bash
# Link to existing project
railway link e57ef125-1237-45b2-82a0-83df6d0b375c
```

#### Step 4: Set Environment Variables
```bash
# Core bot configuration
railway variables set BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o --yes
railway variables set GROUP_ID=-1002384609773 --yes
railway variables set ADMIN_USER_ID=306145881 --yes

# Supabase configuration
railway variables set SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co --yes
railway variables set SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1 --yes

# Airwallex configuration
railway variables set AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg --yes
railway variables set AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47 --yes

# Generate and set admin password
ADMIN_PASSWORD=$(openssl rand -base64 32)
railway variables set ADMIN_PASSWORD=$ADMIN_PASSWORD --yes
echo "Admin Password: $ADMIN_PASSWORD"

# Python configuration
railway variables set PYTHONUNBUFFERED=1 --yes
railway variables set PYTHONDONTWRITEBYTECODE=1 --yes
railway variables set WEBHOOK_PORT=8080 --yes
```

#### Step 5: Deploy
```bash
# Deploy to Railway
railway up --detach
```

## Post-Deployment Configuration

### 1. Get Deployment URL
After deployment, get your application URL:

```bash
# Check deployment status
railway status

# Get logs
railway logs
```

Your deployment URL will be in the format: `https://your-app.up.railway.app`

### 2. Configure Webhook URL
Set the webhook base URL environment variable:

```bash
railway variables set WEBHOOK_BASE_URL=https://your-app.up.railway.app --yes
```

### 3. Register Webhook with Airwallex
1. Log into your Airwallex dashboard
2. Navigate to Webhooks settings
3. Add new webhook endpoint:
   - URL: `https://your-app.up.railway.app/webhook/airwallex`
   - Events: Select payment-related events
4. Copy the webhook secret provided by Airwallex

### 4. Set Webhook Secret
```bash
railway variables set AIRWALLEX_WEBHOOK_SECRET=your-webhook-secret --yes
```

### 5. Redeploy with Updated Configuration
```bash
railway up --detach
```

## Continuous Deployment

### Using the Deploy Script
For subsequent deployments, use the provided deploy script:

```bash
./deploy.sh
```

This script will:
- Check Railway CLI installation
- Verify git repository
- Set/update environment variables
- Commit changes
- Deploy to Railway
- Display deployment URL

### Manual Deployment
```bash
# Add changes
git add .

# Commit
git commit -m "Update description"

# Deploy
railway up --detach
```

### GitHub Integration (Optional)
1. Push your code to GitHub:
   ```bash
   git remote add origin https://github.com/yourusername/your-repo.git
   git push -u origin main
   ```

2. In Railway dashboard:
   - Go to your service settings
   - Connect to GitHub
   - Select your repository
   - Enable automatic deployments

## Configuration Files

### railway.toml
Defines build and deployment configuration:
- Build commands
- Start command
- Health check settings
- Restart policies
- Resource limits

### requirements.txt
Lists all Python dependencies:
- aiogram==3.4.1 (Telegram bot framework)
- supabase>=2.0.0 (Database client)
- aiohttp>=3.10.0 (Async HTTP)
- python-dotenv>=1.0.0 (Environment variables)
- And more...

### runtime.txt
Specifies Python version:
```
python-3.11.10
```

### Procfile
Defines process types:
```
web: python main.py
worker: python main.py
```

## Environment Variables Reference

### Required Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token | `8263837787:AAG...` |
| `GROUP_ID` | Telegram group ID | `-1002384609773` |
| `ADMIN_USER_ID` | Admin Telegram user ID | `306145881` |
| `SUPABASE_URL` | Supabase project URL | `https://xyz.supabase.co` |
| `SUPABASE_SERVICE_KEY` | Supabase service key | `sb_secret_...` |
| `AIRWALLEX_CLIENT_ID` | Airwallex client ID | `BxnIFV1TQ...` |
| `AIRWALLEX_API_KEY` | Airwallex API key | `df76d4f3a...` |
| `ADMIN_PASSWORD` | Admin panel password | Auto-generated |

### Optional Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `WEBHOOK_BASE_URL` | Your Railway app URL | Set after deployment |
| `AIRWALLEX_WEBHOOK_SECRET` | Webhook validation secret | Set after webhook registration |
| `WEBHOOK_PORT` | Internal webhook port | `8080` |
| `DEBUG` | Debug mode | `False` |
| `REDIS_URL` | Redis URL for FSM storage | Optional |

## Monitoring and Maintenance

### View Logs
```bash
# Real-time logs
railway logs

# Follow logs
railway logs -f
```

### Check Service Status
```bash
# Service status
railway status

# List all variables
railway variables
```

### Open Dashboard
```bash
railway open
```

### Restart Service
In Railway dashboard:
1. Go to your service
2. Click "Settings"
3. Click "Restart"

### Scale Resources
In Railway dashboard:
1. Go to your service
2. Click "Settings"
3. Adjust CPU and Memory limits
4. Changes apply immediately

## Health Monitoring

The bot includes a health check endpoint at `/health` that Railway uses to monitor the application status.

### Manual Health Check
```bash
curl https://your-app.up.railway.app/health
```

Expected response: `OK` with status 200

## Troubleshooting

### Common Issues and Solutions

#### 1. Bot Not Responding
- **Check logs**: `railway logs`
- **Verify bot token**: Ensure BOT_TOKEN is correct
- **Check group permissions**: Bot must be admin in the group

#### 2. Webhook Not Working
- **Verify URL**: Check WEBHOOK_BASE_URL is set correctly
- **Check secret**: Ensure AIRWALLEX_WEBHOOK_SECRET matches Airwallex
- **Test endpoint**: `curl https://your-app.up.railway.app/health`

#### 3. Database Connection Failed
- **Check Supabase URL**: Verify SUPABASE_URL is correct
- **Verify service key**: Ensure SUPABASE_SERVICE_KEY is valid
- **Check Supabase status**: Visit Supabase dashboard

#### 4. Deployment Failed
- **Check requirements.txt**: Ensure all dependencies are listed
- **Verify Python version**: Must be 3.11+
- **Review build logs**: `railway logs --build`

#### 5. Environment Variables Not Working
- **List variables**: `railway variables`
- **Re-set variable**: `railway variables set KEY=value --yes`
- **Redeploy**: `railway up --detach`

### Debug Commands
```bash
# Check Python version
railway run python --version

# Test imports
railway run python -c "import aiogram; print(aiogram.__version__)"

# Check environment
railway run env | grep BOT

# Test database connection
railway run python -c "from database.supabase_client import SupabaseClient; client = SupabaseClient()"
```

## Security Best Practices

1. **Never commit secrets to git**
   - Use .gitignore for .env files
   - Set variables via Railway CLI or dashboard

2. **Rotate credentials regularly**
   - Update bot token if compromised
   - Regenerate API keys periodically

3. **Use strong admin password**
   - Generated automatically by setup script
   - Store securely in password manager

4. **Monitor access logs**
   - Check `railway logs` regularly
   - Set up alerts for suspicious activity

5. **Keep dependencies updated**
   - Review security advisories
   - Update requirements.txt regularly

## Cost Optimization

### Railway Pricing
- **Hobby Plan**: $5/month includes $5 of usage
- **Pro Plan**: $20/month includes $20 of usage
- **Usage-based**: Pay for what you use

### Optimization Tips
1. **Set resource limits** in railway.toml
2. **Use efficient code** to reduce CPU usage
3. **Implement caching** to reduce database calls
4. **Monitor usage** in Railway dashboard

## Support and Resources

### Official Documentation
- [Railway Docs](https://docs.railway.com)
- [aiogram Documentation](https://docs.aiogram.dev)
- [Supabase Docs](https://supabase.io/docs)
- [Airwallex API](https://www.airwallex.com/docs)

### Getting Help
1. **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
2. **GitHub Issues**: Report bugs in your repository
3. **Railway Support**: support@railway.app

### Useful Commands Reference
```bash
# Deployment
railway up --detach          # Deploy latest code
railway logs                 # View logs
railway status              # Check status

# Variables
railway variables           # List all variables
railway variables set K=V   # Set variable
railway variables get K     # Get variable value

# Management
railway open               # Open dashboard
railway restart           # Restart service
railway down             # Stop service

# Local Development
railway run python main.py  # Run locally with Railway env
railway shell              # Open shell with Railway env
```

## Backup and Recovery

### Backup Strategy
1. **Code**: Use Git for version control
2. **Database**: Supabase handles automatic backups
3. **Environment**: Export variables regularly:
   ```bash
   railway variables > variables_backup.txt
   ```

### Recovery Process
1. **Restore code**: `git checkout <commit>`
2. **Restore variables**: Re-set from backup
3. **Redeploy**: `railway up --detach`

## Updates and Maintenance

### Updating Dependencies
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Commit and deploy
git add requirements.txt
git commit -m "Update dependencies"
railway up --detach
```

### Python Version Update
1. Edit `runtime.txt`
2. Update to new version (e.g., `python-3.12.0`)
3. Test locally
4. Deploy: `railway up --detach`

## Conclusion

Your Telegram subscription bot is now deployed on Railway with:
- Automatic restarts on failure
- Health monitoring
- Webhook support
- Secure environment variables
- Continuous deployment capability

For daily operations, use:
- `./deploy.sh` for deployments
- `railway logs` for monitoring
- `railway open` for dashboard access

Remember to monitor your bot regularly and keep dependencies updated for security and performance.
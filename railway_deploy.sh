#!/bin/bash

# Railway Deployment Script for Telegram Subscription Bot
# Project ID: e57ef125-1237-45b2-82a0-83df6d0b375c
# GitHub Repository: https://github.com/Msvcp60dll/telegram-subscription-bot

set -e

echo "====================================="
echo "Railway Deployment Script"
echo "====================================="
echo ""
echo "Project ID: e57ef125-1237-45b2-82a0-83df6d0b375c"
echo "GitHub Repo: https://github.com/Msvcp60dll/telegram-subscription-bot"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Prerequisites:${NC}"
echo "1. Railway CLI must be installed and authenticated"
echo "2. GitHub repository is already created and pushed"
echo ""

echo -e "${GREEN}Step 1: Link to Railway Project${NC}"
echo "Run the following command to link your project:"
echo ""
echo "railway link e57ef125-1237-45b2-82a0-83df6d0b375c"
echo ""

echo -e "${GREEN}Step 2: Connect GitHub Repository${NC}"
echo "1. Go to: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c/settings/general"
echo "2. Under 'Service Settings', click on your service"
echo "3. Go to 'Settings' tab"
echo "4. Under 'Source', click 'Connect GitHub'"
echo "5. Authorize Railway if needed"
echo "6. Select repository: Msvcp60dll/telegram-subscription-bot"
echo "7. Select branch: main"
echo "8. Enable 'Auto Deploy' for automatic deployments on push"
echo ""

echo -e "${GREEN}Step 3: Configure Environment Variables${NC}"
echo "Go to: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c/service"
echo "Click on 'Variables' tab and add the following:"
echo ""

cat << 'EOF'
BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o
GROUP_ID=-1002384609773
ADMIN_USER_ID=306145881
SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1
AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47
ADMIN_PASSWORD=TGBot2024Secure!
WEBHOOK_BASE_URL=(Will be set automatically after deployment)
WEBHOOK_PORT=8080
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
EOF

echo ""
echo -e "${YELLOW}Note:${NC} WEBHOOK_BASE_URL will be automatically set to your Railway URL after deployment"
echo ""

echo -e "${GREEN}Step 4: Deploy${NC}"
echo "After connecting GitHub and setting variables:"
echo "1. Railway will automatically deploy from the main branch"
echo "2. Monitor the deployment at: https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c"
echo "3. Check build logs for any errors"
echo ""

echo -e "${GREEN}Step 5: Get Production URL${NC}"
echo "After successful deployment:"
echo "1. Go to your service settings"
echo "2. Under 'Networking', you'll see your Railway domain"
echo "3. It will be something like: https://your-service.up.railway.app"
echo "4. Update WEBHOOK_BASE_URL variable with this URL"
echo ""

echo -e "${GREEN}Step 6: Verify Deployment${NC}"
echo "1. Check service logs in Railway dashboard"
echo "2. Test the bot in Telegram"
echo "3. Access admin dashboard at: https://your-service.up.railway.app/admin"
echo ""

echo -e "${YELLOW}Useful Railway CLI Commands:${NC}"
echo "railway logs           - View deployment logs"
echo "railway status         - Check deployment status"
echo "railway variables      - List environment variables"
echo "railway up            - Deploy from local directory"
echo "railway open          - Open project in browser"
echo ""

echo -e "${GREEN}Rollback Procedures:${NC}"
echo "1. Via Railway Dashboard:"
echo "   - Go to Deployments tab"
echo "   - Find the previous working deployment"
echo "   - Click '...' menu and select 'Redeploy'"
echo ""
echo "2. Via Git:"
echo "   - git revert HEAD"
echo "   - git push origin main"
echo "   - Railway will auto-deploy the reverted version"
echo ""

echo "====================================="
echo "Script complete! Follow the steps above to deploy."
echo "====================================="
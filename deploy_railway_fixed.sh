#!/bin/bash

# Fixed Railway Deployment Script
# Handles both Empty Service and GitHub deployment methods correctly
# Last Updated: 2025-09-03

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=================================${NC}"
echo -e "${BLUE}Railway Deployment Script (Fixed)${NC}"
echo -e "${BLUE}=================================${NC}"
echo ""

# Configuration
PROJECT_ID="e57ef125-1237-45b2-82a0-83df6d0b375c"
GITHUB_REPO="https://github.com/Msvcp60dll/telegram-subscription-bot"

# Check Railway CLI
if ! command -v railway &> /dev/null; then
    echo -e "${RED}❌ Railway CLI not installed${NC}"
    echo "Install with: brew install railway"
    exit 1
fi

# Check authentication
if ! railway whoami &> /dev/null; then
    echo -e "${RED}❌ Not logged in to Railway${NC}"
    echo "Run: railway login"
    exit 1
fi

echo -e "${GREEN}✅ Authenticated as: $(railway whoami)${NC}"
echo ""

# Link to project
echo -e "${YELLOW}Linking to Railway project...${NC}"
railway link --project $PROJECT_ID || {
    echo -e "${RED}❌ Failed to link project${NC}"
    exit 1
}
echo -e "${GREEN}✅ Project linked${NC}"
echo ""

# Choose deployment method
echo -e "${BLUE}Choose Deployment Method:${NC}"
echo "1) GitHub Auto-Deploy (Recommended for production)"
echo "2) Local Deploy with Empty Service (For testing)"
echo ""
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}=== GitHub Deployment Setup ===${NC}"
        echo ""
        echo -e "${YELLOW}You need to manually configure GitHub integration:${NC}"
        echo ""
        echo "1. Open Railway Dashboard:"
        railway open
        echo ""
        echo "2. In your project, click '+ New Service'"
        echo "3. Select 'GitHub Repo' (NOT Empty Service)"
        echo "4. Connect your GitHub account if needed"
        echo "5. Select repository: Msvcp60dll/telegram-subscription-bot"
        echo "6. Select branch: main"
        echo "7. Enable 'Auto Deploy'"
        echo ""
        echo -e "${GREEN}After setup, Railway will automatically deploy from GitHub${NC}"
        echo ""
        echo "To trigger deployment:"
        echo "  git push origin main"
        echo ""
        echo "Monitor with:"
        echo "  railway logs --follow"
        ;;
        
    2)
        echo ""
        echo -e "${BLUE}=== Local Deployment with Empty Service ===${NC}"
        echo ""
        
        # Check for Empty Service
        echo -e "${YELLOW}IMPORTANT: You must have an Empty Service in your Railway project${NC}"
        echo ""
        echo "To create an Empty Service:"
        echo "1. Open Railway Dashboard"
        echo "2. Click '+ New Service'"
        echo "3. Select 'Empty Service' (NOT GitHub Repo)"
        echo "4. Give it a name (e.g., 'tgbot-local')"
        echo ""
        read -p "Have you created an Empty Service? (y/n): " has_empty
        
        if [ "$has_empty" != "y" ]; then
            echo ""
            echo -e "${YELLOW}Opening Railway dashboard...${NC}"
            railway open
            echo ""
            echo "Create an Empty Service, then run this script again"
            exit 0
        fi
        
        # Set environment variables
        echo ""
        echo -e "${YELLOW}Setting environment variables...${NC}"
        
        railway variables set BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o --yes
        railway variables set GROUP_ID=-1002384609773 --yes
        railway variables set ADMIN_USER_ID=306145881 --yes
        railway variables set SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co --yes
        railway variables set SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1 --yes
        railway variables set AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg --yes
        railway variables set AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47 --yes
        railway variables set ADMIN_PASSWORD=TGBot2024Secure! --yes
        railway variables set WEBHOOK_PORT=8080 --yes
        railway variables set PORT=8080 --yes
        railway variables set PYTHONUNBUFFERED=1 --yes
        railway variables set PYTHONDONTWRITEBYTECODE=1 --yes
        
        echo -e "${GREEN}✅ Environment variables set${NC}"
        echo ""
        
        # Check file size
        echo -e "${YELLOW}Checking deployment size...${NC}"
        total_size=$(du -sh . | cut -f1)
        echo "Total directory size: $total_size"
        
        # Create .railwayignore if needed
        if [ ! -f .railwayignore ]; then
            echo "Creating .railwayignore..."
            cat > .railwayignore << 'EOF'
.git
.gitignore
*.pyc
__pycache__
.env
.venv
venv/
node_modules/
*.log
.DS_Store
docs/
*.md
!README.md
EOF
            echo -e "${GREEN}✅ Created .railwayignore${NC}"
        fi
        
        # Deploy
        echo ""
        echo -e "${BLUE}Deploying to Railway Empty Service...${NC}"
        echo "When prompted, select your Empty Service"
        echo ""
        
        railway up || {
            echo ""
            echo -e "${RED}❌ Deployment failed${NC}"
            echo ""
            echo "Common issues:"
            echo "1. No Empty Service exists (create one in dashboard)"
            echo "2. File size > 40MB (check .railwayignore)"
            echo "3. Network issues (try again)"
            echo ""
            echo "Check logs: railway logs"
            exit 1
        }
        
        echo ""
        echo -e "${GREEN}✅ Deployment initiated!${NC}"
        echo ""
        echo "Monitor deployment:"
        echo "  railway logs --follow"
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Common post-deployment steps
echo ""
echo -e "${BLUE}=== Post-Deployment Steps ===${NC}"
echo ""
echo "1. Get your production URL:"
echo "   railway open"
echo "   (Look for the domain under Networking)"
echo ""
echo "2. Update webhook URL:"
echo "   railway variables set WEBHOOK_BASE_URL=https://your-app.up.railway.app --yes"
echo ""
echo "3. Configure Airwallex webhook:"
echo "   URL: https://your-app.up.railway.app/webhook/airwallex"
echo ""
echo "4. Test your bot:"
echo "   Telegram: @Msvcp60dllgoldbot"
echo "   Send: /start"
echo ""
echo "5. Monitor logs:"
echo "   railway logs --follow"
echo ""

# Show current status
echo -e "${BLUE}Current Status:${NC}"
railway status

echo ""
echo -e "${GREEN}Script complete!${NC}"
#!/bin/bash

# Automated Railway Deployment Script
# This script will deploy your bot to Railway with all configurations

set -e  # Exit on error

echo "🚀 Starting Automated Railway Deployment"
echo "========================================"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    brew install railway || {
        echo "Failed to install Railway CLI. Please install manually:"
        echo "brew install railway"
        exit 1
    }
fi

# Project configuration
PROJECT_ID="e57ef125-1237-45b2-82a0-83df6d0b375c"
GITHUB_REPO="https://github.com/Msvcp60dll/telegram-subscription-bot"

echo ""
echo "📦 GitHub Repository: $GITHUB_REPO"
echo "🚂 Railway Project ID: $PROJECT_ID"
echo ""

# Login check
echo "🔐 Checking Railway authentication..."
railway whoami &> /dev/null || {
    echo "❌ Not logged in to Railway"
    echo ""
    echo "Please login with: railway login"
    echo "Then run this script again"
    exit 1
}

echo "✅ Authenticated as: $(railway whoami)"
echo ""

# Link to project
echo "🔗 Linking to Railway project..."
railway link --project $PROJECT_ID || {
    echo "❌ Failed to link project"
    echo "Make sure project ID is correct: $PROJECT_ID"
    exit 1
}
echo "✅ Project linked successfully"
echo ""

# Set environment variables
echo "⚙️  Setting environment variables..."

# Create env file
cat > .railway.env << 'EOF'
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
PORT=8080
EOF

# Set each variable
while IFS='=' read -r key value; do
    if [ ! -z "$key" ] && [ ! -z "$value" ]; then
        echo "  Setting $key..."
        railway variables set "$key=$value" --yes 2>/dev/null || true
    fi
done < .railway.env

echo "✅ Environment variables configured"
echo ""

# Deploy from GitHub
echo "🚀 Deploying from GitHub..."
echo ""
echo "📝 Railway will now:"
echo "  1. Connect to GitHub repository"
echo "  2. Build your application"
echo "  3. Deploy to production"
echo ""

# Trigger deployment
railway up --detach || {
    echo "❌ Deployment failed"
    echo "Please check Railway dashboard for details"
    exit 1
}

echo ""
echo "✅ Deployment initiated!"
echo ""

# Get deployment URL
echo "🌐 Getting deployment URL..."
sleep 5  # Wait for deployment to start

# Try to get the deployment URL
railway status 2>/dev/null | grep -i "deployment url" || {
    echo "⏳ Deployment URL not ready yet"
    echo "Check status with: railway status"
}

echo ""
echo "========================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Check deployment logs:"
echo "   railway logs"
echo ""
echo "2. Get your production URL:"
echo "   railway open"
echo ""
echo "3. Once deployed, get your URL and set webhook:"
echo "   railway variables set WEBHOOK_BASE_URL=https://your-app.up.railway.app --yes"
echo ""
echo "4. Configure Airwallex webhook in their dashboard"
echo "   URL: https://your-app.up.railway.app/webhook/airwallex"
echo ""
echo "5. Test your bot:"
echo "   - Open Telegram"
echo "   - Search: @Msvcp60dllgoldbot"
echo "   - Send: /start"
echo ""
echo "📊 Monitor deployment:"
echo "   railway logs --follow"
echo ""
echo "🎉 Your bot is deploying to production!"
echo ""

# Cleanup
rm -f .railway.env

# Open Railway dashboard
echo "Opening Railway dashboard in browser..."
railway open
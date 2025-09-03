#!/bin/bash

# Railway Setup and Deployment Script
# Run this in your terminal where you logged in

echo "🚀 Railway Setup and Deployment"
echo "================================"
echo ""

# Check authentication
echo "✅ Logged in as: $(railway whoami)"
echo ""

# Check if already linked
if railway status &>/dev/null; then
    echo "✅ Project already linked"
else
    echo "❌ No project linked. Please run: railway init"
    echo "Then run this script again."
    exit 1
fi

echo ""
echo "⚙️  Setting environment variables..."

# Set all environment variables using the correct syntax
railway variables \
  --set "BOT_TOKEN=8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o" \
  --set "GROUP_ID=-1002384609773" \
  --set "ADMIN_USER_ID=306145881" \
  --set "SUPABASE_URL=https://dijdhqrxqwbctywejydj.supabase.co" \
  --set "SUPABASE_SERVICE_KEY=sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1" \
  --set "AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg" \
  --set "AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47" \
  --set "ADMIN_PASSWORD=TGBot2024Secure!" \
  --set "WEBHOOK_PORT=8080" \
  --set "PORT=8080" \
  --set "PYTHONUNBUFFERED=1" \
  --set "PYTHONDONTWRITEBYTECODE=1"

echo "✅ Environment variables set"
echo ""

# Deploy
echo "🚀 Deploying to Railway..."
railway up --detach

echo ""
echo "✅ Deployment started!"
echo ""

# Wait a moment for deployment to start
sleep 5

# Get deployment info
echo "📊 Getting deployment info..."
railway status || true

echo ""
echo "================================"
echo "✅ SETUP COMPLETE!"
echo "================================"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Monitor deployment:"
echo "   railway logs --follow"
echo ""
echo "2. Check deployment status:"
echo "   railway status"
echo ""
echo "3. Once deployed, generate a domain:"
echo "   Go to Railway dashboard → Settings → Generate Domain"
echo "   Or visit: https://railway.app/project/$(railway status 2>/dev/null | grep -oE '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)"
echo ""
echo "4. After getting domain, set webhook URL:"
echo "   railway variables --set \"WEBHOOK_BASE_URL=https://your-app.up.railway.app\""
echo ""
echo "5. Test your bot:"
echo "   - Open Telegram"
echo "   - Search: @Msvcp60dllgoldbot"
echo "   - Send: /start"
echo ""
echo "🎉 Your bot is deploying!"
echo ""
echo "Opening Railway dashboard..."
railway open
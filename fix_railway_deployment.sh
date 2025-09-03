#!/bin/bash

echo "🔧 Fixing Railway Deployment"
echo "============================"
echo ""

# Check if we're linked to a project
if ! railway status &>/dev/null; then
    echo "❌ No project linked. Please run: railway init"
    exit 1
fi

echo "📦 Current Status:"
railway status
echo ""

# The issue is that Railway needs the code to be connected via GitHub
echo "🔗 Railway requires GitHub connection for deployment"
echo ""
echo "Please follow these steps:"
echo ""
echo "1. Open Railway Dashboard:"
railway open
echo ""
echo "2. In the Railway Dashboard:"
echo "   a) Click '+ New Service'"
echo "   b) Select 'GitHub Repo'"
echo "   c) Connect your GitHub account if not already connected"
echo "   d) Select repository: Msvcp60dll/telegram-subscription-bot"
echo "   e) Select branch: main"
echo "   f) Railway will start deploying automatically"
echo ""
echo "3. Alternative - Deploy from local code (if GitHub connection fails):"
echo "   Run: railway up"
echo ""
echo "📝 Your environment variables are already set!"
echo ""
echo "After deployment starts, monitor with:"
echo "   railway logs"
echo ""
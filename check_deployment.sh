#!/bin/bash

echo "🔍 Checking Railway Deployment Status"
echo "======================================"
echo ""

echo "Project Status:"
railway status
echo ""

echo "Environment Variables (first few):"
railway variables | head -5
echo ""

echo "Recent Activity:"
echo "The deployment was initiated. Please check the Railway dashboard:"
echo ""
echo "Build Logs URLs from recent deployments:"
echo "1. https://railway.com/project/fdbba060-8a48-4c9a-98ec-82bac1c37ffe/service/9c599758-bf84-4c8f-a6c7-427e0c40bc75?id=9fb02b07-c8a2-4b2c-a2bd-6fa94088339d"
echo "2. https://railway.com/project/fdbba060-8a48-4c9a-98ec-82bac1c37ffe/service/9c599758-bf84-4c8f-a6c7-427e0c40bc75?id=b8a36533-abff-40b0-8aac-528c7ffab567"
echo ""
echo "Please visit the Railway dashboard to:"
echo "1. Check if the build completed"
echo "2. View any build errors"
echo "3. Get the production URL once deployed"
echo ""
echo "To generate a domain after successful deployment:"
echo "  Go to Settings → Networking → Generate Domain"
echo ""
echo "Once you have the domain, set the webhook URL:"
echo "  railway variables --set WEBHOOK_BASE_URL=https://your-domain.up.railway.app"
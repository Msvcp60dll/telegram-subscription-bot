# Railway Deployment Guide
**Last Updated:** 2025-09-03
**Railway CLI Version:** Latest
**Documentation Source:** Official Railway Docs

## Table of Contents
1. [Deployment Methods](#deployment-methods)
2. [Network Process Error - Root Cause](#network-process-error---root-cause)
3. [Solution for Local Deployment](#solution-for-local-deployment)
4. [GitHub Integration Method](#github-integration-method)
5. [Common Errors and Solutions](#common-errors-and-solutions)

## Deployment Methods

Railway supports three primary deployment methods:

### 1. GitHub Repository Deployment (Recommended)
- **How it works:** Railway connects directly to your GitHub repository
- **Auto-deploy:** Automatically deploys on push to selected branch
- **Requirements:** GitHub account linked to Railway

### 2. Local Directory Deployment via CLI
- **How it works:** Deploy code from your local machine using `railway up`
- **Requirements:** Empty Service must be created first
- **Use case:** Testing, development, or when GitHub integration isn't available

### 3. Docker Image Deployment
- **How it works:** Deploy pre-built Docker images
- **Requirements:** Docker image in a registry

## Network Process Error - Root Cause

The "Deployment failed during network process" error typically occurs due to:

### 1. Service Type Mismatch
**CRITICAL ISSUE:** Your current scripts are attempting to use `railway up` without first creating an Empty Service. The `railway up` command ONLY works with Empty Services, not GitHub-connected services.

### 2. Common Causes:
- Attempting local deployment (`railway up`) on a GitHub-connected service
- Missing Empty Service creation step
- Healthcheck failures during deployment
- Database connection issues (PostgreSQL, Redis)
- Exceeded file size limits (40MB for `railway up`)
- Free plan limitations

## Solution for Local Deployment

### Step 1: Create an Empty Service
```bash
# This MUST be done in Railway Dashboard
# 1. Go to your project
# 2. Click "+ New Service"
# 3. Select "Empty Service" (NOT GitHub Repo)
# 4. Name it (e.g., "tgbot-service")
```

### Step 2: Deploy with Railway CLI
```bash
# Link to your project
railway link e57ef125-1237-45b2-82a0-83df6d0b375c

# Deploy to the Empty Service
railway up

# When prompted, select the empty service you created
```

### Fixed Deployment Script
Create a new deployment script that handles Empty Service correctly:

```bash
#!/bin/bash

# Fixed Railway Deployment Script for Empty Service
set -e

echo "Railway Empty Service Deployment"
echo "================================"

# Check Railway CLI authentication
if ! railway whoami &> /dev/null; then
    echo "Error: Not logged in to Railway"
    echo "Run: railway login"
    exit 1
fi

# Link to project
PROJECT_ID="e57ef125-1237-45b2-82a0-83df6d0b375c"
railway link --project $PROJECT_ID

# Check if Empty Service exists
echo ""
echo "IMPORTANT: You must have an Empty Service created in Railway"
echo "If not, go to Railway dashboard and create one now"
echo ""
read -p "Press Enter when Empty Service is ready..."

# Deploy to Empty Service
echo "Deploying to Empty Service..."
railway up

echo "Deployment initiated!"
echo "Check logs: railway logs"
```

## GitHub Integration Method

If you prefer automatic deployments on git push:

### Step 1: Remove Empty Service
Delete any Empty Services from your Railway project

### Step 2: Create GitHub-Connected Service
```
1. Railway Dashboard → Your Project
2. Click "+ New Service"
3. Select "GitHub Repo"
4. Connect GitHub account (if needed)
5. Select: Msvcp60dll/telegram-subscription-bot
6. Select branch: main
7. Enable "Auto Deploy"
```

### Step 3: Push to GitHub
```bash
git add .
git commit -m "Deploy to Railway"
git push origin main
# Railway automatically deploys
```

## Common Errors and Solutions

### Error: "Deployment failed during network process"

**Cause 1:** Using `railway up` without Empty Service
**Solution:** Create Empty Service first or switch to GitHub deployment

**Cause 2:** Healthcheck failure
**Solution:** Remove healthcheck in Railway settings (set Healthcheck Path to blank)

**Cause 3:** File size > 40MB
**Solution:** Add `.railwayignore` file to exclude large files

### Error: "Project Token not found"

**Cause:** Missing authentication in CI/CD
**Solution:** Set RAILWAY_TOKEN environment variable

### Error: "service unavailable" (502/500)

**Cause:** Application startup failure
**Solution:** Check logs with `railway logs` and fix startup issues

### Error: Database connection failed

**Cause:** PostgreSQL/Redis not deployed
**Solution:** Ensure database services are running before app deployment

## Environment Variables Setup

Set all required environment variables BEFORE deployment:

```bash
# Set variables via CLI
railway variables set BOT_TOKEN=your_token --yes
railway variables set GROUP_ID=-1002384609773 --yes
railway variables set ADMIN_USER_ID=306145881 --yes
# ... set all other variables

# Or set in Railway Dashboard
# Project → Service → Variables tab
```

## Deployment Verification

After deployment:

```bash
# Check deployment status
railway status

# View logs
railway logs --follow

# Get deployment URL
railway open

# Update webhook URL after deployment
railway variables set WEBHOOK_BASE_URL=https://your-app.up.railway.app --yes
```

## Key Differences: Empty Service vs GitHub Service

| Feature | Empty Service | GitHub Service |
|---------|--------------|----------------|
| Deployment Method | `railway up` from local | Auto-deploy on git push |
| Use Case | Development, testing | Production |
| Requirements | Railway CLI | GitHub account linked |
| Auto-deploy | No | Yes |
| Rollback | Manual redeploy | Git revert + push |
| Build Location | Railway servers | Railway servers |

## Troubleshooting Commands

```bash
# Check current service type
railway status

# List all services
railway list

# View environment variables
railway variables

# Check deployment logs
railway logs --tail 100

# Open Railway dashboard
railway open
```

## IMPORTANT NOTES

1. **You cannot use `railway up` with GitHub-connected services** - this is the root cause of your error
2. **Empty Services are required for local CLI deployment**
3. **File limit for `railway up` is 40MB**
4. **Free tier has deployment queue during high traffic**
5. **Pro tier gets deployment priority**

## Recommended Fix for Your Situation

Since you have GitHub repo ready (https://github.com/Msvcp60dll/telegram-subscription-bot):

1. **Option A: Use GitHub Deployment (Recommended)**
   - Delete any existing services in Railway
   - Create new GitHub-connected service
   - Let Railway auto-deploy from GitHub

2. **Option B: Use Empty Service for Local Deployment**
   - Create Empty Service in Railway dashboard
   - Use `railway up` to deploy local code

The error "Deployment failed during network process" is occurring because your scripts try to use `railway up` on a non-Empty Service. Choose one method and stick with it.
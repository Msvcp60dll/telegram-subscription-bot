#!/bin/bash

# Railway Deployment Script for Telegram Subscription Bot
# This script automates the deployment process to Railway

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="e57ef125-1237-45b2-82a0-83df6d0b375c"
SERVICE_NAME="telegram-subscription-bot"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Railway Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for Railway CLI
if ! command_exists railway; then
    echo -e "${RED}Error: Railway CLI is not installed${NC}"
    echo "Please install Railway CLI first:"
    echo "  npm install -g @railway/cli"
    echo "or"
    echo "  curl -fsSL https://railway.app/install.sh | sh"
    exit 1
fi

# Check for Git
if ! command_exists git; then
    echo -e "${RED}Error: Git is not installed${NC}"
    echo "Please install Git first"
    exit 1
fi

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}Initializing Git repository...${NC}"
    git init
    git add .
    git commit -m "Initial commit for Railway deployment"
    echo -e "${GREEN}Git repository initialized${NC}"
else
    echo -e "${GREEN}Git repository found${NC}"
fi

# Check if logged into Railway
echo -e "${YELLOW}Checking Railway authentication...${NC}"
if ! railway whoami &>/dev/null; then
    echo -e "${YELLOW}Not logged into Railway. Please login:${NC}"
    railway login
fi

# Link to Railway project
echo -e "${YELLOW}Linking to Railway project...${NC}"
if [ -f ".railway/project.json" ]; then
    echo -e "${GREEN}Already linked to Railway project${NC}"
else
    railway link $PROJECT_ID
    echo -e "${GREEN}Linked to Railway project${NC}"
fi

# Create/Update environment variables from .env.railway
if [ -f ".env.railway" ]; then
    echo -e "${YELLOW}Setting environment variables...${NC}"
    
    # Read .env.railway and set variables (excluding comments and empty lines)
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
            # Remove any leading/trailing whitespace
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            
            # Skip empty values for certain keys that should be set later
            if [[ "$key" == "AIRWALLEX_WEBHOOK_SECRET" || "$key" == "WEBHOOK_BASE_URL" || "$key" == "ADMIN_PASSWORD" ]] && [[ -z "$value" ]]; then
                echo -e "${YELLOW}Skipping $key (needs to be set manually)${NC}"
            elif [[ -n "$value" ]]; then
                railway variables set "$key=$value" --yes 2>/dev/null || true
                echo -e "${GREEN}Set $key${NC}"
            fi
        fi
    done < .env.railway
    
    echo -e "${GREEN}Environment variables configured${NC}"
else
    echo -e "${YELLOW}Warning: .env.railway file not found${NC}"
    echo "Please create .env.railway with your environment variables"
fi

# Generate admin password if not set
echo -e "${YELLOW}Checking admin password...${NC}"
ADMIN_PASSWORD=$(railway variables get ADMIN_PASSWORD 2>/dev/null || echo "")
if [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${YELLOW}Generating secure admin password...${NC}"
    NEW_PASSWORD=$(openssl rand -base64 32)
    railway variables set ADMIN_PASSWORD="$NEW_PASSWORD" --yes
    echo -e "${GREEN}Admin password generated and saved${NC}"
    echo -e "${YELLOW}Admin Password: $NEW_PASSWORD${NC}"
    echo -e "${RED}Please save this password securely!${NC}"
fi

# Commit any changes
echo -e "${YELLOW}Checking for uncommitted changes...${NC}"
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${YELLOW}Committing changes...${NC}"
    git add .
    git commit -m "Update deployment configuration" || true
fi

# Deploy to Railway
echo -e "${YELLOW}Deploying to Railway...${NC}"
railway up --detach

# Get deployment URL
echo -e "${YELLOW}Waiting for deployment...${NC}"
sleep 5

# Get the deployment URL
DEPLOYMENT_URL=$(railway status --json 2>/dev/null | grep -o '"url":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -n "$DEPLOYMENT_URL" ]; then
    # Set the webhook URL if not already set
    WEBHOOK_URL="https://$DEPLOYMENT_URL"
    echo -e "${GREEN}Deployment URL: $WEBHOOK_URL${NC}"
    
    # Update WEBHOOK_BASE_URL if not set
    CURRENT_WEBHOOK_URL=$(railway variables get WEBHOOK_BASE_URL 2>/dev/null || echo "")
    if [ -z "$CURRENT_WEBHOOK_URL" ]; then
        railway variables set WEBHOOK_BASE_URL="$WEBHOOK_URL" --yes
        echo -e "${GREEN}Updated WEBHOOK_BASE_URL${NC}"
        
        # Trigger redeploy to apply the new webhook URL
        echo -e "${YELLOW}Redeploying with updated webhook URL...${NC}"
        railway up --detach
    fi
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${GREEN}Bot URL: $WEBHOOK_URL${NC}"
    echo -e "${GREEN}Webhook endpoint: $WEBHOOK_URL/webhook/airwallex${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "1. Register the webhook URL with Airwallex"
    echo "2. Get the webhook secret from Airwallex"
    echo "3. Set AIRWALLEX_WEBHOOK_SECRET using:"
    echo "   railway variables set AIRWALLEX_WEBHOOK_SECRET=your-secret --yes"
    echo "4. Redeploy using: railway up --detach"
    echo ""
    echo -e "${GREEN}To view logs:${NC} railway logs"
    echo -e "${GREEN}To open dashboard:${NC} railway open"
else
    echo -e "${YELLOW}Deployment initiated. Check status with: railway logs${NC}"
fi

echo ""
echo -e "${GREEN}Deployment script completed!${NC}"
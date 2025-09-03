#!/bin/bash

# Railway Environment Variables Setup Script
# This script sets up all required environment variables for the Railway deployment

set -e

echo "================================================"
echo "Railway Environment Variables Setup"
echo "Project ID: e57ef125-1237-45b2-82a0-83df6d0b375c"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo -e "${RED}Error: Railway CLI is not installed${NC}"
    echo "Please install it from: https://docs.railway.app/develop/cli"
    exit 1
fi

echo -e "${YELLOW}Prerequisites:${NC}"
echo "1. You must be logged into Railway CLI (railway login)"
echo "2. Your project must be linked (railway link e57ef125-1237-45b2-82a0-83df6d0b375c)"
echo ""

read -p "Have you completed the prerequisites? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Please complete the prerequisites first${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Setting up environment variables...${NC}"
echo ""

# Function to set variable with confirmation
set_railway_var() {
    local var_name=$1
    local var_value=$2
    local is_secret=$3
    
    if [ "$is_secret" = true ]; then
        echo -e "${BLUE}Setting ${var_name} (hidden for security)${NC}"
    else
        echo -e "${BLUE}Setting ${var_name}=${var_value}${NC}"
    fi
    
    railway variables set "$var_name=$var_value" 2>/dev/null || {
        echo -e "${RED}Failed to set ${var_name}${NC}"
        return 1
    }
    
    echo -e "${GREEN}✓ ${var_name} set successfully${NC}"
    echo ""
}

# Core Bot Configuration
echo -e "${YELLOW}Setting Bot Configuration...${NC}"
set_railway_var "BOT_TOKEN" "8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o" true
set_railway_var "GROUP_ID" "-1002384609773" false
set_railway_var "ADMIN_USER_ID" "306145881" false

# Database Configuration
echo -e "${YELLOW}Setting Database Configuration...${NC}"
set_railway_var "SUPABASE_URL" "https://dijdhqrxqwbctywejydj.supabase.co" false
set_railway_var "SUPABASE_SERVICE_KEY" "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1" true

# Payment Integration
echo -e "${YELLOW}Setting Payment Integration...${NC}"
set_railway_var "AIRWALLEX_CLIENT_ID" "BxnIFV1TQkWbrpkEKaADwg" false
set_railway_var "AIRWALLEX_API_KEY" "df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47" true

# Admin Configuration
echo -e "${YELLOW}Setting Admin Configuration...${NC}"
set_railway_var "ADMIN_PASSWORD" "TGBot2024Secure!" true

# Webhook Configuration
echo -e "${YELLOW}Setting Webhook Configuration...${NC}"
set_railway_var "WEBHOOK_PORT" "8080" false

# Python Optimization
echo -e "${YELLOW}Setting Python Optimization...${NC}"
set_railway_var "PYTHONUNBUFFERED" "1" false
set_railway_var "PYTHONDONTWRITEBYTECODE" "1" false

echo ""
echo "================================================"
echo -e "${GREEN}Environment variables setup complete!${NC}"
echo "================================================"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Go to your Railway dashboard to verify variables are set"
echo "   https://railway.app/project/e57ef125-1237-45b2-82a0-83df6d0b375c/service"
echo ""
echo "2. After deployment, get your production URL from Railway"
echo "   and set WEBHOOK_BASE_URL:"
echo "   railway variables set WEBHOOK_BASE_URL=https://your-app.up.railway.app"
echo ""
echo "3. Trigger a deployment:"
echo "   - Push to GitHub main branch (if connected)"
echo "   - Or run: railway up"
echo ""

echo -e "${GREEN}Useful commands:${NC}"
echo "railway variables        # List all variables"
echo "railway logs            # View deployment logs"
echo "railway status          # Check deployment status"
echo "railway open            # Open project in browser"
echo ""

# Verify variables were set
echo -e "${BLUE}Verifying variables...${NC}"
railway variables | head -20 || echo -e "${YELLOW}Note: Run 'railway variables' manually to verify${NC}"

echo ""
echo -e "${GREEN}Script completed successfully!${NC}"
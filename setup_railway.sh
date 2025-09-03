#!/bin/bash

# Initial Railway Setup Script for Telegram Subscription Bot
# Run this script once to set up your Railway project

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="e57ef125-1237-45b2-82a0-83df6d0b375c"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Railway Initial Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Railway CLI
install_railway_cli() {
    echo -e "${YELLOW}Installing Railway CLI...${NC}"
    
    # Check for npm
    if command_exists npm; then
        echo "Installing via npm..."
        npm install -g @railway/cli
    # Check for curl
    elif command_exists curl; then
        echo "Installing via install script..."
        curl -fsSL https://railway.app/install.sh | sh
    else
        echo -e "${RED}Error: Neither npm nor curl is available${NC}"
        echo "Please install npm or curl first, then run this script again"
        exit 1
    fi
    
    echo -e "${GREEN}Railway CLI installed successfully${NC}"
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

# Check for Git
if ! command_exists git; then
    echo -e "${RED}Error: Git is not installed${NC}"
    echo "Please install Git first:"
    echo "  macOS: brew install git"
    echo "  Ubuntu/Debian: sudo apt-get install git"
    echo "  RHEL/Fedora: sudo yum install git"
    exit 1
fi
echo -e "${GREEN}✓ Git is installed${NC}"

# Check for Python
if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo "Please install Python 3.11 or later"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
echo -e "${GREEN}✓ Python $PYTHON_VERSION is installed${NC}"

# Check for Railway CLI
if ! command_exists railway; then
    echo -e "${YELLOW}Railway CLI is not installed${NC}"
    read -p "Do you want to install Railway CLI now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        install_railway_cli
    else
        echo -e "${RED}Railway CLI is required. Please install it manually:${NC}"
        echo "  npm install -g @railway/cli"
        echo "or"
        echo "  curl -fsSL https://railway.app/install.sh | sh"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Railway CLI is installed${NC}"
fi

# Step 2: Railway Authentication
echo ""
echo -e "${YELLOW}Step 2: Railway Authentication${NC}"
echo "You'll be redirected to Railway login page in your browser"
echo "Please log in with your Railway account"
read -p "Press Enter to continue..." -r

railway login

echo -e "${GREEN}✓ Logged into Railway${NC}"

# Step 3: Initialize Git Repository
echo ""
echo -e "${YELLOW}Step 3: Setting up Git repository...${NC}"

if [ ! -d ".git" ]; then
    git init
    
    # Create .gitignore if it doesn't exist
    if [ ! -f ".gitignore" ]; then
        cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Environment variables
.env
.env.local
.env.*.local

# Logs
*.log
bot.log

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/

# Railway
.railway/

# Temporary files
*.tmp
*.bak
EOF
        echo -e "${GREEN}Created .gitignore${NC}"
    fi
    
    git add .
    git commit -m "Initial commit for Railway deployment"
    echo -e "${GREEN}✓ Git repository initialized${NC}"
else
    echo -e "${GREEN}✓ Git repository already exists${NC}"
fi

# Step 4: Link to Railway Project
echo ""
echo -e "${YELLOW}Step 4: Linking to Railway project...${NC}"

if [ -f ".railway/project.json" ]; then
    echo -e "${GREEN}✓ Already linked to Railway project${NC}"
else
    railway link $PROJECT_ID
    echo -e "${GREEN}✓ Linked to Railway project${NC}"
fi

# Step 5: Generate secure passwords
echo ""
echo -e "${YELLOW}Step 5: Generating secure credentials...${NC}"

# Generate admin password
ADMIN_PASSWORD=$(openssl rand -base64 32)
echo -e "${GREEN}Generated Admin Password: ${YELLOW}$ADMIN_PASSWORD${NC}"
echo -e "${RED}⚠️  Please save this password securely!${NC}"

# Update .env.railway with generated password
if [ -f ".env.railway" ]; then
    # Update ADMIN_PASSWORD in .env.railway
    if grep -q "^ADMIN_PASSWORD=" .env.railway; then
        sed -i.bak "s|^ADMIN_PASSWORD=.*|ADMIN_PASSWORD=$ADMIN_PASSWORD|" .env.railway
    else
        echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> .env.railway
    fi
    rm -f .env.railway.bak
fi

# Step 6: Set up environment variables
echo ""
echo -e "${YELLOW}Step 6: Configuring environment variables...${NC}"

if [ -f ".env.railway" ]; then
    echo "Setting environment variables in Railway..."
    
    # Parse .env.railway and set variables
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        if [[ ! "$key" =~ ^# ]] && [[ -n "$key" ]]; then
            key=$(echo "$key" | xargs)
            value=$(echo "$value" | xargs)
            
            if [[ -n "$value" ]]; then
                railway variables set "$key=$value" --yes 2>/dev/null || true
                echo -e "${GREEN}✓ Set $key${NC}"
            fi
        fi
    done < .env.railway
    
    echo -e "${GREEN}✓ Environment variables configured${NC}"
else
    echo -e "${RED}Warning: .env.railway file not found${NC}"
    echo "Please create .env.railway first"
fi

# Step 7: Initial deployment
echo ""
echo -e "${YELLOW}Step 7: Performing initial deployment...${NC}"
echo "This may take a few minutes..."

# Commit any changes
if [ -n "$(git status --porcelain)" ]; then
    git add .
    git commit -m "Initial Railway configuration"
fi

# Deploy
railway up --detach

echo -e "${GREEN}✓ Initial deployment started${NC}"

# Step 8: Get deployment URL and final instructions
echo ""
echo -e "${YELLOW}Step 8: Retrieving deployment information...${NC}"
sleep 10

# Try to get the deployment URL
DEPLOYMENT_URL=$(railway status --json 2>/dev/null | grep -o '"url":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -n "$DEPLOYMENT_URL" ]; then
    WEBHOOK_URL="https://$DEPLOYMENT_URL"
    
    # Set the WEBHOOK_BASE_URL
    railway variables set WEBHOOK_BASE_URL="$WEBHOOK_URL" --yes
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Your bot is deployed at:${NC}"
    echo -e "${GREEN}$WEBHOOK_URL${NC}"
    echo ""
    echo -e "${BLUE}Webhook endpoint for Airwallex:${NC}"
    echo -e "${GREEN}$WEBHOOK_URL/webhook/airwallex${NC}"
    echo ""
    echo -e "${BLUE}Admin Password:${NC}"
    echo -e "${YELLOW}$ADMIN_PASSWORD${NC}"
    echo ""
else
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Setup Complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}Deployment is in progress...${NC}"
fi

echo -e "${BLUE}Next Steps:${NC}"
echo "1. Check deployment status: ${YELLOW}railway logs${NC}"
echo "2. Open Railway dashboard: ${YELLOW}railway open${NC}"
echo "3. Register webhook with Airwallex using the URL above"
echo "4. Get webhook secret from Airwallex and set it:"
echo "   ${YELLOW}railway variables set AIRWALLEX_WEBHOOK_SECRET=your-secret --yes${NC}"
echo "5. Redeploy after setting webhook secret: ${YELLOW}railway up --detach${NC}"
echo ""
echo -e "${BLUE}Useful Commands:${NC}"
echo "• View logs: ${YELLOW}railway logs${NC}"
echo "• Deploy updates: ${YELLOW}./deploy.sh${NC}"
echo "• Open dashboard: ${YELLOW}railway open${NC}"
echo "• Check status: ${YELLOW}railway status${NC}"
echo "• List variables: ${YELLOW}railway variables${NC}"
echo ""
echo -e "${GREEN}Setup script completed successfully!${NC}"
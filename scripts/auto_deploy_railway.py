#!/usr/bin/env python3
"""
Automated Railway Deployment via API
This script deploys the bot to Railway using their GraphQL API
"""

import os
import sys
import json
import time
import requests
from typing import Dict, Any, Optional

# Railway API Configuration
RAILWAY_API_URL = "https://backboard.railway.app/graphql/v2"
PROJECT_ID = "e57ef125-1237-45b2-82a0-83df6d0b375c"

# Environment Variables to Set
ENV_VARS = {
    "BOT_TOKEN": "8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o",
    "GROUP_ID": "-1002384609773",
    "ADMIN_USER_ID": "306145881",
    "SUPABASE_URL": "https://dijdhqrxqwbctywejydj.supabase.co",
    "SUPABASE_SERVICE_KEY": "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1",
    "AIRWALLEX_CLIENT_ID": "BxnIFV1TQkWbrpkEKaADwg",
    "AIRWALLEX_API_KEY": "df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47",
    "ADMIN_PASSWORD": "TGBot2024Secure!",
    "WEBHOOK_PORT": "8080",
    "PORT": "8080",
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1"
}

def check_railway_token() -> Optional[str]:
    """Check for Railway API token"""
    token = os.getenv("RAILWAY_API_TOKEN")
    if not token:
        print("❌ RAILWAY_API_TOKEN not found")
        print("\nTo get your Railway API token:")
        print("1. Go to: https://railway.app/account/tokens")
        print("2. Create a new token")
        print("3. Set it as environment variable:")
        print("   export RAILWAY_API_TOKEN=your_token_here")
        print("\nOr use the Railway CLI:")
        print("   railway login")
        print("   railway up --detach")
        return None
    return token

def make_graphql_request(token: str, query: str, variables: Dict = None) -> Dict:
    """Make a GraphQL request to Railway API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    response = requests.post(RAILWAY_API_URL, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"API request failed: {response.status_code} - {response.text}")
    
    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data.get("data", {})

def get_project_info(token: str) -> Dict:
    """Get project information"""
    query = """
    query GetProject($projectId: String!) {
        project(id: $projectId) {
            id
            name
            environments {
                edges {
                    node {
                        id
                        name
                    }
                }
            }
        }
    }
    """
    
    result = make_graphql_request(token, query, {"projectId": PROJECT_ID})
    return result.get("project", {})

def set_environment_variables(token: str, environment_id: str) -> bool:
    """Set environment variables for the project"""
    query = """
    mutation UpsertVariables($projectId: String!, $environmentId: String!, $variables: VariableCollectionInput!) {
        variableCollectionUpsert(
            projectId: $projectId, 
            environmentId: $environmentId, 
            variables: $variables
        )
    }
    """
    
    variables_input = {
        "projectId": PROJECT_ID,
        "environmentId": environment_id,
        "variables": {"variables": ENV_VARS}
    }
    
    try:
        make_graphql_request(token, query, variables_input)
        return True
    except Exception as e:
        print(f"❌ Failed to set variables: {e}")
        return False

def trigger_deployment(token: str, environment_id: str) -> Optional[str]:
    """Trigger a new deployment"""
    query = """
    mutation CreateDeployment($projectId: String!, $environmentId: String!) {
        deploymentCreate(projectId: $projectId, environmentId: $environmentId) {
            id
            status
        }
    }
    """
    
    variables = {
        "projectId": PROJECT_ID,
        "environmentId": environment_id
    }
    
    try:
        result = make_graphql_request(token, query, variables)
        deployment = result.get("deploymentCreate", {})
        return deployment.get("id")
    except Exception as e:
        print(f"❌ Failed to trigger deployment: {e}")
        return None

def get_deployment_status(token: str, deployment_id: str) -> str:
    """Get deployment status"""
    query = """
    query GetDeployment($deploymentId: String!) {
        deployment(id: $deploymentId) {
            status
            staticUrl
        }
    }
    """
    
    result = make_graphql_request(token, query, {"deploymentId": deployment_id})
    return result.get("deployment", {})

def main():
    """Main deployment process"""
    print("🚀 Railway Automated Deployment")
    print("=" * 50)
    
    # Check for API token
    token = check_railway_token()
    if not token:
        print("\n⚠️  Alternative: Use Railway CLI")
        print("-" * 50)
        print("1. Install Railway CLI:")
        print("   brew install railway")
        print("\n2. Login to Railway:")
        print("   railway login")
        print("\n3. Run the deployment script:")
        print("   ./deploy_now.sh")
        return 1
    
    print(f"✅ Railway API token found")
    
    # Get project info
    print(f"\n📦 Getting project info...")
    try:
        project = get_project_info(token)
        if not project:
            print(f"❌ Project not found: {PROJECT_ID}")
            return 1
        
        print(f"✅ Project: {project.get('name', 'Unknown')}")
        
        # Get production environment
        environments = project.get("environments", {}).get("edges", [])
        prod_env = None
        for env in environments:
            node = env.get("node", {})
            if node.get("name") == "production":
                prod_env = node.get("id")
                break
        
        if not prod_env:
            print("❌ Production environment not found")
            return 1
        
        print(f"✅ Environment: production ({prod_env})")
        
    except Exception as e:
        print(f"❌ Failed to get project info: {e}")
        return 1
    
    # Set environment variables
    print(f"\n⚙️  Setting environment variables...")
    if set_environment_variables(token, prod_env):
        print(f"✅ Set {len(ENV_VARS)} environment variables")
    else:
        print("⚠️  Some variables may not have been set")
    
    # Trigger deployment
    print(f"\n🚀 Triggering deployment...")
    deployment_id = trigger_deployment(token, prod_env)
    
    if not deployment_id:
        print("❌ Failed to trigger deployment")
        print("\nTry using Railway CLI instead:")
        print("  railway up --detach")
        return 1
    
    print(f"✅ Deployment started: {deployment_id}")
    
    # Monitor deployment
    print(f"\n📊 Monitoring deployment...")
    print("This may take a few minutes...")
    
    max_attempts = 60  # 5 minutes max
    for i in range(max_attempts):
        time.sleep(5)
        
        status_info = get_deployment_status(token, deployment_id)
        status = status_info.get("status", "UNKNOWN")
        
        print(f"  Status: {status}", end="\r")
        
        if status == "SUCCESS":
            print(f"\n✅ Deployment successful!")
            
            url = status_info.get("staticUrl")
            if url:
                print(f"\n🌐 Production URL: {url}")
                print(f"\nSet webhook URL:")
                print(f"  railway variables set WEBHOOK_BASE_URL={url} --yes")
            break
            
        elif status in ["FAILED", "CANCELLED"]:
            print(f"\n❌ Deployment {status.lower()}")
            print("\nCheck logs:")
            print("  railway logs")
            return 1
    
    else:
        print("\n⏱️  Deployment taking longer than expected")
        print("Check status with: railway status")
    
    # Print next steps
    print("\n" + "=" * 50)
    print("📋 Next Steps:")
    print("\n1. Check deployment logs:")
    print("   railway logs --follow")
    print("\n2. Configure Airwallex webhook:")
    print("   - Go to Airwallex dashboard")
    print(f"   - Set webhook URL: {url}/webhook/airwallex" if 'url' in locals() else "   - Set webhook URL: https://your-app.up.railway.app/webhook/airwallex")
    print("\n3. Test your bot:")
    print("   - Open Telegram")
    print("   - Search: @Msvcp60dllgoldbot")
    print("   - Send: /start")
    print("\n" + "=" * 50)
    print("✅ Deployment complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
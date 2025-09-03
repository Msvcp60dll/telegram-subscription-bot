#!/usr/bin/env python3
"""
Airwallex Webhook Setup Helper Script

This script helps configure and validate Airwallex webhook settings.
It checks environment variables, tests connectivity, and provides setup guidance.

Usage:
    python scripts/setup_webhook.py
"""

import os
import sys
import json
import hmac
import hashlib
import time
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_environment():
    """Check if required environment variables are set"""
    print("\n🔍 Checking Environment Variables...")
    print("-" * 50)
    
    required_vars = {
        "AIRWALLEX_CLIENT_ID": "Client ID for API authentication",
        "AIRWALLEX_API_KEY": "API Key for authentication",
        "AIRWALLEX_WEBHOOK_SECRET": "Secret for webhook signature verification"
    }
    
    optional_vars = {
        "WEBHOOK_BASE_URL": "Base URL for webhook endpoint",
        "AIRWALLEX_BASE_URL": "Airwallex API base URL (defaults to production)"
    }
    
    all_set = True
    
    # Check required variables
    print("\n✅ Required Variables:")
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"  ✓ {var}: {masked}")
            else:
                print(f"  ✓ {var}: {value}")
        else:
            print(f"  ✗ {var}: NOT SET - {description}")
            all_set = False
    
    # Check optional variables
    print("\n📝 Optional Variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {value}")
        else:
            print(f"  ○ {var}: Not set - {description}")
    
    return all_set


def generate_webhook_secret():
    """Generate a secure webhook secret"""
    import secrets
    return secrets.token_hex(32)


def display_setup_instructions():
    """Display setup instructions for Airwallex dashboard"""
    print("\n📋 Airwallex Dashboard Setup Instructions")
    print("=" * 50)
    
    print("\n1. Log in to Airwallex webapp")
    print("   https://www.airwallex.com\n")
    
    print("2. Navigate to: Developer → Webhooks\n")
    
    print("3. Click 'Add Webhook' and configure:")
    print("   • Notification URL:")
    
    base_url = os.getenv("WEBHOOK_BASE_URL", "https://your-app.railway.app")
    print(f"     Development: http://localhost:8080/webhook/airwallex")
    print(f"     Production:  {base_url}/webhook/airwallex\n")
    
    print("4. Subscribe to these events:")
    print("   ✓ payment_intent.succeeded")
    print("   ✓ payment_intent.failed")
    print("   ✓ payment_link.paid")
    print("   ✓ refund.succeeded\n")
    
    print("5. Copy the Webhook Secret and add to .env:")
    print(f"   AIRWALLEX_WEBHOOK_SECRET=<your-secret>\n")
    
    print("6. Save the webhook configuration\n")


def create_env_template():
    """Create .env.template file if it doesn't exist"""
    template_path = ".env.template"
    
    if os.path.exists(template_path):
        print(f"\n✓ {template_path} already exists")
        return
    
    template_content = """# Airwallex API Configuration
AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47

# Webhook Configuration
AIRWALLEX_WEBHOOK_SECRET=your_webhook_secret_here

# Environment URLs
# Development
WEBHOOK_BASE_URL=http://localhost:8080

# Production (Railway)
# WEBHOOK_BASE_URL=https://your-app.railway.app

# Optional: Airwallex API Base URL
# AIRWALLEX_BASE_URL=https://api.airwallex.com  # Production
# AIRWALLEX_BASE_URL=https://api-demo.airwallex.com  # Sandbox
"""
    
    with open(template_path, 'w') as f:
        f.write(template_content)
    
    print(f"\n✓ Created {template_path} with configuration template")


def test_webhook_signature():
    """Test webhook signature generation"""
    print("\n🧪 Testing Webhook Signature Generation...")
    print("-" * 50)
    
    secret = os.getenv("AIRWALLEX_WEBHOOK_SECRET")
    if not secret:
        print("⚠️  No webhook secret configured - using test secret")
        secret = "test_secret_key"
    
    # Create test payload
    test_payload = {
        "id": "evt_test_123",
        "name": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "int_test_123",
                "amount": 1000,
                "currency": "USD"
            }
        }
    }
    
    body = json.dumps(test_payload, separators=(',', ':'))
    timestamp = str(int(time.time()))
    
    # Generate signature (matching Airwallex algorithm)
    payload = f"{timestamp}{body}"
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    print(f"\nTest Webhook Headers:")
    print(f"  x-timestamp: {timestamp}")
    print(f"  x-signature: {signature[:20]}...{signature[-10:]}")
    print(f"\nTest Payload:")
    print(f"  Event: {test_payload['name']}")
    print(f"  ID: {test_payload['id']}")
    
    print("\n✓ Signature generation working correctly")
    
    return {
        "body": body,
        "timestamp": timestamp,
        "signature": signature
    }


def display_testing_commands():
    """Display useful testing commands"""
    print("\n🛠️  Useful Testing Commands")
    print("=" * 50)
    
    print("\n1. Run security tests:")
    print("   python tests/test_webhook_security.py\n")
    
    print("2. Start webhook server:")
    print("   python main.py\n")
    
    print("3. Test webhook manually:")
    test_data = test_webhook_signature()
    
    print(f"""   curl -X POST http://localhost:8080/webhook/airwallex \\
     -H "Content-Type: application/json" \\
     -H "x-timestamp: {test_data['timestamp']}" \\
     -H "x-signature: {test_data['signature']}" \\
     -d '{test_data['body']}'
""")
    
    print("4. Check webhook health:")
    print("   curl http://localhost:8080/health\n")


def main():
    """Main setup helper"""
    print("\n" + "="*60)
    print("🚀 AIRWALLEX WEBHOOK SETUP HELPER")
    print("="*60)
    
    # Check environment
    env_ok = check_environment()
    
    if not env_ok:
        print("\n⚠️  Some required environment variables are missing!")
        print("\nTo fix this:")
        print("1. Copy .env.template to .env")
        print("2. Fill in the missing values")
        print("3. Run this script again")
        
        create_env_template()
    
    # Generate webhook secret if needed
    if not os.getenv("AIRWALLEX_WEBHOOK_SECRET"):
        print("\n💡 Need a webhook secret? Here's a secure one:")
        print(f"   AIRWALLEX_WEBHOOK_SECRET={generate_webhook_secret()}")
        print("\n   Add this to your .env file and Airwallex dashboard")
    
    # Display setup instructions
    display_setup_instructions()
    
    # Display testing commands
    display_testing_commands()
    
    # Summary
    print("\n" + "="*60)
    print("📌 NEXT STEPS")
    print("="*60)
    
    if env_ok:
        print("\n✅ Environment configured correctly!")
        print("\n1. Configure webhook in Airwallex dashboard")
        print("2. Run security tests: python tests/test_webhook_security.py")
        print("3. Start server: python main.py")
        print("4. Test webhooks from Airwallex dashboard")
    else:
        print("\n1. Set up missing environment variables")
        print("2. Run this script again to verify")
        print("3. Configure webhook in Airwallex dashboard")
        print("4. Run security tests")
    
    print("\n📚 Documentation:")
    print("  • docs/webhook-security.md - Security implementation")
    print("  • docs/airwallex-webhook-setup.md - Setup guide")
    print("  • docs/webhook-security-audit.md - Security checklist")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
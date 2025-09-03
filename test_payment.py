"""
Test script for Airwallex payment integration
Run this to verify the payment flow is working correctly
"""

import asyncio
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variables for testing
os.environ["AIRWALLEX_CLIENT_ID"] = "BxnIFV1TQkWbrpkEKaADwg"
os.environ["AIRWALLEX_API_KEY"] = "df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47"

from services.airwallex_payment import AirwallexPaymentService
from services.payment_processor import PaymentProcessor


async def test_airwallex_authentication():
    """Test Airwallex API authentication"""
    print("\n=== Testing Airwallex Authentication ===")
    
    service = AirwallexPaymentService()
    await service.initialize()
    
    if service.access_token:
        print("✅ Successfully authenticated with Airwallex")
        print(f"   Token expires at: {service.token_expires_at}")
        return True
    else:
        print("❌ Failed to authenticate with Airwallex")
        return False
    
    await service.close()


async def test_create_payment_link():
    """Test creating a payment link"""
    print("\n=== Testing Payment Link Creation ===")
    
    service = AirwallexPaymentService()
    await service.initialize()
    
    # Create a test payment link
    success, result = await service.create_payment_link(
        amount=10.00,  # $10 USD
        currency="USD",
        customer_email="test@example.com",
        customer_name="Test User",
        telegram_id=123456789,
        telegram_username="testuser",
        plan_id="basic",
        plan_name="Basic (7 days)",
        expires_in_hours=24
    )
    
    if success:
        print("✅ Payment link created successfully!")
        print(f"   Link ID: {result['id']}")
        print(f"   Payment URL: {result['url']}")
        print(f"   Amount: ${result['amount']} {result['currency']}")
        print(f"   Expires at: {result['expires_at']}")
        print(f"\n   Open this URL to test payment: {result['url']}")
        return result['id']
    else:
        print(f"❌ Failed to create payment link: {result.get('error')}")
        return None
    
    await service.close()


async def test_payment_processor():
    """Test the unified payment processor"""
    print("\n=== Testing Payment Processor ===")
    
    processor = PaymentProcessor()
    await processor.initialize()
    
    # Create a test session
    session_id = await processor.create_payment_session(
        user_id=123456789,
        plan_id="basic",
        plan_details={
            "name": "Basic (7 days)",
            "stars": 50,
            "days": 7
        },
        user_info={
            "username": "testuser",
            "name": "Test User",
            "email": "test@example.com"
        }
    )
    
    print(f"✅ Created payment session: {session_id}")
    
    # Test card payment flow
    success, result = await processor.process_card_payment(session_id)
    
    if success:
        print("✅ Card payment processed successfully!")
        print(f"   Payment URL: {result['payment_url']}")
        print(f"   Amount: ${result['amount_usd']:.2f} USD")
    else:
        print(f"❌ Card payment failed: {result.get('error')}")
        if result.get('fallback_available'):
            print(f"   Fallback available: {result.get('fallback_method')}")
    
    # Get revenue stats
    stats = processor.get_revenue_stats()
    print("\n📊 Revenue Statistics:")
    print(f"   Card payments: {stats['card']['transactions']} (${stats['card']['total_usd']:.2f})")
    print(f"   Stars payments: {stats['stars']['transactions']} ({stats['stars']['total_stars']} stars)")
    
    await processor.close()


async def test_webhook_signature():
    """Test webhook signature verification"""
    print("\n=== Testing Webhook Signature ===")
    
    service = AirwallexPaymentService(webhook_secret="test_secret")
    
    # Test with valid signature (this would come from Airwallex in production)
    webhook_id = "webhook_123"
    timestamp = str(int(datetime.now().timestamp()))
    
    # In production, Airwallex would provide the signature
    # This is just to test the verification logic
    is_valid = service.verify_webhook_signature(
        webhook_id=webhook_id,
        timestamp=timestamp,
        signature="invalid_signature_for_test"
    )
    
    print(f"📝 Webhook signature verification: {'✅ Valid' if is_valid else '❌ Invalid'}")
    print("   (Note: This will show as invalid in test as we don't have the actual secret)")


async def main():
    """Run all tests"""
    print("🚀 Starting Airwallex Payment Integration Tests")
    print("=" * 50)
    
    try:
        # Test authentication
        auth_success = await test_airwallex_authentication()
        
        if auth_success:
            # Test payment link creation
            payment_link_id = await test_create_payment_link()
            
            # Test payment processor
            await test_payment_processor()
            
            # Test webhook signature
            await test_webhook_signature()
        
        print("\n" + "=" * 50)
        print("✅ All tests completed!")
        print("\nNOTE: To fully test the payment flow:")
        print("1. Run the bot with: python main.py")
        print("2. Start a conversation with the bot")
        print("3. Choose a subscription plan")
        print("4. Select 'Pay with Card' to test Airwallex")
        print("5. Complete the payment on the Airwallex page")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
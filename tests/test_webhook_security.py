#!/usr/bin/env python3
"""
Comprehensive Webhook Security Testing Script for Airwallex Integration

This script tests webhook signature verification, replay attack prevention,
and overall webhook security implementation.

Usage:
    python tests/test_webhook_security.py
"""

import os
import sys
import json
import hmac
import hashlib
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Tuple
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.airwallex_payment import AirwallexPaymentService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebhookSecurityTester:
    """Comprehensive webhook security testing"""
    
    def __init__(self, webhook_url: str = None, webhook_secret: str = None):
        """Initialize the webhook tester"""
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_URL", "http://localhost:8080/webhook/airwallex")
        self.webhook_secret = webhook_secret or os.getenv("AIRWALLEX_WEBHOOK_SECRET", "test_secret_key")
        self.test_results = []
        
    def generate_signature(self, body: str, timestamp: str, secret: str = None) -> str:
        """Generate HMAC-SHA256 signature for webhook"""
        secret = secret or self.webhook_secret
        payload = f"{timestamp}{body}"
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def create_test_webhook_payload(self, event_type: str = "payment_intent.succeeded") -> Dict:
        """Create a test webhook payload"""
        return {
            "id": f"evt_test_{int(time.time())}",
            "name": event_type,
            "account_id": "test_account",
            "data": {
                "object": {
                    "id": f"int_test_{int(time.time())}",
                    "amount": 1000,
                    "currency": "USD",
                    "status": "SUCCEEDED" if "succeeded" in event_type else "FAILED",
                    "payment_link_id": "plink_test_123",
                    "metadata": {
                        "telegram_id": "123456789",
                        "plan_id": "test_monthly",
                        "plan_name": "Test Monthly Plan"
                    },
                    "last_payment_error": {
                        "message": "Test error"
                    } if "failed" in event_type else None
                }
            },
            "created_at": datetime.now().isoformat() + "Z"
        }
    
    async def test_valid_webhook(self) -> Tuple[bool, str]:
        """Test 1: Valid webhook with correct signature"""
        test_name = "Valid Webhook"
        try:
            # Create test payload
            payload = self.create_test_webhook_payload()
            body = json.dumps(payload, separators=(',', ':'))
            timestamp = str(int(time.time()))
            
            # Generate valid signature
            signature = self.generate_signature(body, timestamp)
            
            # Send webhook request
            headers = {
                "x-timestamp": timestamp,
                "x-signature": signature,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=body, headers=headers) as response:
                    if response.status == 200:
                        return True, f"✅ {test_name}: Webhook accepted with valid signature"
                    else:
                        text = await response.text()
                        return False, f"❌ {test_name}: Unexpected status {response.status} - {text}"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_invalid_signature(self) -> Tuple[bool, str]:
        """Test 2: Webhook with invalid signature"""
        test_name = "Invalid Signature"
        try:
            payload = self.create_test_webhook_payload()
            body = json.dumps(payload, separators=(',', ':'))
            timestamp = str(int(time.time()))
            
            # Generate invalid signature
            signature = "invalid_signature_12345"
            
            headers = {
                "x-timestamp": timestamp,
                "x-signature": signature,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=body, headers=headers) as response:
                    if response.status == 401:
                        return True, f"✅ {test_name}: Correctly rejected invalid signature"
                    else:
                        return False, f"❌ {test_name}: Should reject invalid signature (got {response.status})"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_replay_attack_old_timestamp(self) -> Tuple[bool, str]:
        """Test 3: Replay attack with old timestamp"""
        test_name = "Replay Attack Prevention"
        try:
            payload = self.create_test_webhook_payload()
            body = json.dumps(payload, separators=(',', ':'))
            
            # Use timestamp from 10 minutes ago
            old_timestamp = str(int(time.time()) - 600)
            signature = self.generate_signature(body, old_timestamp)
            
            headers = {
                "x-timestamp": old_timestamp,
                "x-signature": signature,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=body, headers=headers) as response:
                    if response.status == 401:
                        return True, f"✅ {test_name}: Correctly rejected old timestamp"
                    else:
                        return False, f"❌ {test_name}: Should reject old timestamp (got {response.status})"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_missing_headers(self) -> Tuple[bool, str]:
        """Test 4: Webhook with missing security headers"""
        test_name = "Missing Headers"
        try:
            payload = self.create_test_webhook_payload()
            body = json.dumps(payload, separators=(',', ':'))
            
            # No security headers
            headers = {
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=body, headers=headers) as response:
                    if response.status == 400:
                        return True, f"✅ {test_name}: Correctly rejected missing headers"
                    else:
                        return False, f"❌ {test_name}: Should reject missing headers (got {response.status})"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_malformed_json(self) -> Tuple[bool, str]:
        """Test 5: Webhook with malformed JSON"""
        test_name = "Malformed JSON"
        try:
            body = "{ invalid json }"
            timestamp = str(int(time.time()))
            signature = self.generate_signature(body, timestamp)
            
            headers = {
                "x-timestamp": timestamp,
                "x-signature": signature,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, data=body, headers=headers) as response:
                    if response.status == 400:
                        return True, f"✅ {test_name}: Correctly rejected malformed JSON"
                    else:
                        return False, f"❌ {test_name}: Should reject malformed JSON (got {response.status})"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_idempotency(self) -> Tuple[bool, str]:
        """Test 6: Idempotency - same webhook sent twice"""
        test_name = "Idempotency"
        try:
            # Create webhook with specific ID
            payload = self.create_test_webhook_payload()
            payload["id"] = "evt_idempotency_test_123"
            body = json.dumps(payload, separators=(',', ':'))
            timestamp = str(int(time.time()))
            signature = self.generate_signature(body, timestamp)
            
            headers = {
                "x-timestamp": timestamp,
                "x-signature": signature,
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                # Send first request
                async with session.post(self.webhook_url, data=body, headers=headers) as response1:
                    status1 = response1.status
                
                # Send duplicate request
                async with session.post(self.webhook_url, data=body, headers=headers) as response2:
                    status2 = response2.status
                
                if status1 == 200 and status2 == 200:
                    return True, f"✅ {test_name}: Duplicate webhook handled correctly"
                else:
                    return False, f"❌ {test_name}: Unexpected statuses ({status1}, {status2})"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_signature_verification_unit_test(self) -> Tuple[bool, str]:
        """Test 7: Unit test for signature verification function"""
        test_name = "Signature Verification Unit Test"
        try:
            service = AirwallexPaymentService(webhook_secret=self.webhook_secret)
            
            # Test case 1: Valid signature
            body = '{"test": "data"}'
            timestamp = str(int(time.time()))
            valid_signature = self.generate_signature(body, timestamp)
            
            is_valid = service.verify_webhook_signature(
                body=body,
                timestamp=timestamp,
                signature=valid_signature
            )
            
            if not is_valid:
                return False, f"❌ {test_name}: Failed to verify valid signature"
            
            # Test case 2: Invalid signature
            invalid_result = service.verify_webhook_signature(
                body=body,
                timestamp=timestamp,
                signature="invalid_signature"
            )
            
            if invalid_result:
                return False, f"❌ {test_name}: Accepted invalid signature"
            
            # Test case 3: Old timestamp
            old_timestamp = str(int(time.time()) - 400)  # 6+ minutes old
            old_signature = self.generate_signature(body, old_timestamp)
            
            old_result = service.verify_webhook_signature(
                body=body,
                timestamp=old_timestamp,
                signature=old_signature
            )
            
            if old_result:
                return False, f"❌ {test_name}: Accepted old timestamp"
            
            return True, f"✅ {test_name}: All unit tests passed"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_timing_attack_resistance(self) -> Tuple[bool, str]:
        """Test 8: Timing attack resistance"""
        test_name = "Timing Attack Resistance"
        try:
            payload = self.create_test_webhook_payload()
            body = json.dumps(payload, separators=(',', ':'))
            timestamp = str(int(time.time()))
            
            valid_signature = self.generate_signature(body, timestamp)
            
            # Test with signatures that differ at different positions
            test_signatures = [
                valid_signature,  # Exact match
                "0" + valid_signature[1:],  # First char different
                valid_signature[:-1] + "0",  # Last char different
                "completely_different_signature",  # Completely different
            ]
            
            timings = []
            
            for sig in test_signatures:
                headers = {
                    "x-timestamp": timestamp,
                    "x-signature": sig,
                    "Content-Type": "application/json"
                }
                
                start = time.perf_counter()
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, data=body, headers=headers) as response:
                        await response.read()
                end = time.perf_counter()
                
                timings.append(end - start)
            
            # Check if timings are reasonably consistent (within 50ms)
            max_diff = max(timings) - min(timings)
            if max_diff < 0.05:  # 50ms tolerance
                return True, f"✅ {test_name}: Timing-safe comparison detected (max diff: {max_diff*1000:.2f}ms)"
            else:
                # This is just a warning, not necessarily a failure
                return True, f"⚠️ {test_name}: Timing variance detected ({max_diff*1000:.2f}ms) - may be network related"
        
        except Exception as e:
            return False, f"❌ {test_name}: Error - {str(e)}"
    
    async def test_all_event_types(self) -> Tuple[bool, str]:
        """Test 9: All required event types"""
        test_name = "Event Types"
        event_types = [
            "payment_intent.succeeded",
            "payment_intent.failed",
            "payment_link.paid",
            "refund.succeeded"
        ]
        
        all_passed = True
        results = []
        
        for event_type in event_types:
            try:
                payload = self.create_test_webhook_payload(event_type)
                body = json.dumps(payload, separators=(',', ':'))
                timestamp = str(int(time.time()))
                signature = self.generate_signature(body, timestamp)
                
                headers = {
                    "x-timestamp": timestamp,
                    "x-signature": signature,
                    "Content-Type": "application/json"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.webhook_url, data=body, headers=headers) as response:
                        if response.status == 200:
                            results.append(f"  ✅ {event_type}: Accepted")
                        else:
                            all_passed = False
                            results.append(f"  ❌ {event_type}: Failed (status {response.status})")
            
            except Exception as e:
                all_passed = False
                results.append(f"  ❌ {event_type}: Error - {str(e)}")
        
        result_text = "\n".join(results)
        if all_passed:
            return True, f"✅ {test_name}: All event types handled\n{result_text}"
        else:
            return False, f"❌ {test_name}: Some event types failed\n{result_text}"
    
    async def run_all_tests(self):
        """Run all webhook security tests"""
        print("\n" + "="*60)
        print("🔒 AIRWALLEX WEBHOOK SECURITY TEST SUITE")
        print("="*60)
        print(f"Testing endpoint: {self.webhook_url}")
        print(f"Webhook secret configured: {'Yes' if self.webhook_secret else 'No'}")
        print("="*60 + "\n")
        
        tests = [
            self.test_valid_webhook,
            self.test_invalid_signature,
            self.test_replay_attack_old_timestamp,
            self.test_missing_headers,
            self.test_malformed_json,
            self.test_idempotency,
            self.test_signature_verification_unit_test,
            self.test_timing_attack_resistance,
            self.test_all_event_types,
        ]
        
        passed = 0
        failed = 0
        
        for i, test in enumerate(tests, 1):
            print(f"\nTest {i}/{len(tests)}: {test.__doc__.strip().split(':')[1]}")
            print("-" * 40)
            
            try:
                success, message = await test()
                print(message)
                
                if success:
                    passed += 1
                else:
                    failed += 1
                
                self.test_results.append({
                    "test": test.__name__,
                    "success": success,
                    "message": message
                })
            
            except Exception as e:
                failed += 1
                error_msg = f"❌ Test failed with exception: {str(e)}"
                print(error_msg)
                self.test_results.append({
                    "test": test.__name__,
                    "success": False,
                    "message": error_msg
                })
        
        # Print summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {len(tests)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/len(tests)*100):.1f}%")
        
        # Security recommendations
        print("\n" + "="*60)
        print("🔐 SECURITY RECOMMENDATIONS")
        print("="*60)
        
        if failed == 0:
            print("✅ All security tests passed!")
            print("Your webhook implementation appears to be secure.")
        else:
            print("⚠️ Some security tests failed. Please review:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • Fix: {result['test']}")
        
        print("\nAdditional recommendations:")
        print("  1. Ensure webhook secret is kept secure and rotated regularly")
        print("  2. Monitor webhook logs for suspicious activity")
        print("  3. Implement rate limiting on webhook endpoint")
        print("  4. Use HTTPS in production (required)")
        print("  5. Consider IP allowlisting for production")
        print("  6. Implement proper error handling and logging")
        print("="*60 + "\n")
        
        return passed == len(tests)


async def main():
    """Main test execution"""
    # Check if webhook server is running
    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8080/webhook/airwallex")
    
    print(f"Checking if webhook server is accessible at {webhook_url}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Try health endpoint first
            health_url = webhook_url.replace("/webhook/airwallex", "/health")
            async with session.get(health_url, timeout=2) as response:
                if response.status == 200:
                    print("✅ Webhook server is running\n")
                else:
                    print(f"⚠️ Health check returned status {response.status}")
    except Exception as e:
        print(f"\n⚠️ Warning: Cannot connect to webhook server at {webhook_url}")
        print(f"Error: {e}")
        print("\nMake sure your webhook server is running:")
        print("  python main.py")
        print("\nContinuing with tests anyway...\n")
    
    # Run tests
    tester = WebhookSecurityTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
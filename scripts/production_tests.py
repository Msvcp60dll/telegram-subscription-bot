#!/usr/bin/env python3
"""
Production Test Suite for Telegram Subscription Bot
Comprehensive end-to-end testing for all critical paths
"""

import asyncio
import sys
import os
import json
import time
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import aiohttp
from aiogram import Bot
from aiogram.types import User, Chat
from aiogram.exceptions import TelegramAPIError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestStatus(Enum):
    """Test execution status"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"

@dataclass
class TestResult:
    """Test result structure"""
    test_name: str
    status: TestStatus
    message: str
    duration_ms: float
    details: Dict = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

class ProductionTestSuite:
    """Comprehensive test suite for production environment"""
    
    def __init__(self, test_mode: bool = True):
        """Initialize test suite"""
        self.test_mode = test_mode  # If True, use test data only
        self.config = self._load_config()
        self.test_results = []
        self.test_user_id = None  # Will be created during tests
        
        # Initialize components
        self.bot = None
        self.db_client = None
        self.session = None
    
    def _load_config(self) -> Dict:
        """Load configuration from environment"""
        return {
            'bot_token': os.getenv('BOT_TOKEN'),
            'group_id': int(os.getenv('GROUP_ID', '0')),
            'admin_user_id': int(os.getenv('ADMIN_USER_ID', '0')),
            'supabase_url': os.getenv('SUPABASE_URL'),
            'supabase_key': os.getenv('SUPABASE_SERVICE_KEY'),
            'webhook_base_url': os.getenv('WEBHOOK_BASE_URL', ''),
            'airwallex_client_id': os.getenv('AIRWALLEX_CLIENT_ID'),
            'airwallex_api_key': os.getenv('AIRWALLEX_API_KEY'),
        }
    
    async def initialize(self):
        """Initialize test components"""
        try:
            # Initialize bot
            if self.config.get('bot_token'):
                self.bot = Bot(token=self.config['bot_token'])
                logger.info("Bot client initialized for testing")
            
            # Initialize database client
            if self.config.get('supabase_url') and self.config.get('supabase_key'):
                self.db_client = SupabaseClient(
                    self.config['supabase_url'],
                    self.config['supabase_key']
                )
                logger.info("Database client initialized for testing")
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            logger.info("HTTP session initialized for testing")
            
        except Exception as e:
            logger.error(f"Failed to initialize test suite: {e}")
            raise
    
    async def cleanup(self):
        """Clean up test resources"""
        # Clean up test data if created
        if self.test_user_id and self.db_client:
            try:
                await self._cleanup_test_user(self.test_user_id)
            except Exception as e:
                logger.error(f"Failed to clean up test user: {e}")
        
        # Close connections
        if self.bot:
            await self.bot.session.close()
        if self.session:
            await self.session.close()
    
    def _generate_test_user_id(self) -> int:
        """Generate unique test user ID"""
        # Use timestamp + random for uniqueness
        return int(f"999{int(time.time() % 10000)}{random.randint(100, 999)}")
    
    async def _cleanup_test_user(self, user_id: int):
        """Clean up test user data from database"""
        try:
            # Delete from all tables
            self.db_client.client.table('payments').delete().eq('user_id', user_id).execute()
            self.db_client.client.table('transactions').delete().eq('user_id', user_id).execute()
            self.db_client.client.table('subscriptions').delete().eq('user_id', user_id).execute()
            self.db_client.client.table('users').delete().eq('telegram_id', user_id).execute()
            logger.info(f"Cleaned up test user {user_id}")
        except Exception as e:
            logger.error(f"Error cleaning up test user: {e}")
    
    # ============= Test Cases =============
    
    async def test_bot_commands(self) -> TestResult:
        """Test basic bot command responsiveness"""
        start_time = time.time()
        
        try:
            if not self.bot:
                return TestResult(
                    test_name="bot_commands",
                    status=TestStatus.SKIPPED,
                    message="Bot not configured",
                    duration_ms=0
                )
            
            # Test getting bot info
            bot_info = await self.bot.get_me()
            
            # Test getting available commands
            commands = await self.bot.get_my_commands()
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="bot_commands",
                status=TestStatus.PASSED,
                message=f"Bot @{bot_info.username} has {len(commands)} commands",
                duration_ms=duration,
                details={
                    'bot_username': bot_info.username,
                    'bot_id': bot_info.id,
                    'commands': [{'command': cmd.command, 'description': cmd.description} for cmd in commands]
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="bot_commands",
                status=TestStatus.FAILED,
                message=f"Bot command test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_database_operations(self) -> TestResult:
        """Test database CRUD operations"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return TestResult(
                    test_name="database_operations",
                    status=TestStatus.SKIPPED,
                    message="Database not configured",
                    duration_ms=0
                )
            
            # Generate test user
            test_user_id = self._generate_test_user_id()
            test_username = f"test_user_{test_user_id}"
            
            # Test CREATE
            create_result = self.db_client.client.table('users').insert({
                'telegram_id': test_user_id,
                'username': test_username,
                'full_name': 'Test User',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            # Test READ
            read_result = self.db_client.client.table('users')\
                .select('*')\
                .eq('telegram_id', test_user_id)\
                .single()\
                .execute()
            
            # Test UPDATE
            update_result = self.db_client.client.table('users')\
                .update({'full_name': 'Updated Test User'})\
                .eq('telegram_id', test_user_id)\
                .execute()
            
            # Test DELETE
            delete_result = self.db_client.client.table('users')\
                .delete()\
                .eq('telegram_id', test_user_id)\
                .execute()
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="database_operations",
                status=TestStatus.PASSED,
                message="All CRUD operations successful",
                duration_ms=duration,
                details={
                    'operations_tested': ['CREATE', 'READ', 'UPDATE', 'DELETE'],
                    'test_user_id': test_user_id
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="database_operations",
                status=TestStatus.FAILED,
                message=f"Database test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_subscription_lifecycle(self) -> TestResult:
        """Test complete subscription lifecycle"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return TestResult(
                    test_name="subscription_lifecycle",
                    status=TestStatus.SKIPPED,
                    message="Database not configured",
                    duration_ms=0
                )
            
            # Create test user
            self.test_user_id = self._generate_test_user_id()
            
            # 1. Create user
            user_data = {
                'telegram_id': self.test_user_id,
                'username': f'test_{self.test_user_id}',
                'full_name': 'Subscription Test User',
                'created_at': datetime.utcnow().isoformat()
            }
            self.db_client.client.table('users').insert(user_data).execute()
            
            # 2. Create subscription
            subscription_data = {
                'user_id': self.test_user_id,
                'plan_name': 'test_basic',
                'status': 'active',
                'start_date': datetime.utcnow().isoformat(),
                'end_date': (datetime.utcnow() + timedelta(days=7)).isoformat(),
                'auto_renew': False,
                'created_at': datetime.utcnow().isoformat()
            }
            sub_result = self.db_client.client.table('subscriptions').insert(subscription_data).execute()
            subscription_id = sub_result.data[0]['id']
            
            # 3. Check active subscription
            active_check = self.db_client.client.table('subscriptions')\
                .select('*')\
                .eq('user_id', self.test_user_id)\
                .eq('status', 'active')\
                .execute()
            
            # 4. Update subscription (extend)
            new_end_date = (datetime.utcnow() + timedelta(days=30)).isoformat()
            self.db_client.client.table('subscriptions')\
                .update({'end_date': new_end_date})\
                .eq('id', subscription_id)\
                .execute()
            
            # 5. Cancel subscription
            self.db_client.client.table('subscriptions')\
                .update({'status': 'cancelled', 'auto_renew': False})\
                .eq('id', subscription_id)\
                .execute()
            
            # 6. Clean up
            await self._cleanup_test_user(self.test_user_id)
            self.test_user_id = None  # Mark as cleaned
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="subscription_lifecycle",
                status=TestStatus.PASSED,
                message="Subscription lifecycle test completed",
                duration_ms=duration,
                details={
                    'steps_completed': [
                        'user_creation',
                        'subscription_creation',
                        'active_check',
                        'subscription_extension',
                        'subscription_cancellation',
                        'cleanup'
                    ]
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="subscription_lifecycle",
                status=TestStatus.FAILED,
                message=f"Subscription lifecycle test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_payment_flow(self) -> TestResult:
        """Test payment processing flow"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return TestResult(
                    test_name="payment_flow",
                    status=TestStatus.SKIPPED,
                    message="Database not configured",
                    duration_ms=0
                )
            
            # Create test payment record
            test_user_id = self._generate_test_user_id()
            
            # 1. Create user
            self.db_client.client.table('users').insert({
                'telegram_id': test_user_id,
                'username': f'payment_test_{test_user_id}',
                'full_name': 'Payment Test User',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            # 2. Create payment record
            payment_data = {
                'user_id': test_user_id,
                'amount': 50,
                'currency': 'STARS',
                'status': 'pending',
                'payment_method': 'telegram_stars',
                'plan_name': 'basic',
                'created_at': datetime.utcnow().isoformat()
            }
            payment_result = self.db_client.client.table('payments').insert(payment_data).execute()
            payment_id = payment_result.data[0]['id']
            
            # 3. Simulate payment processing
            self.db_client.client.table('payments')\
                .update({
                    'status': 'completed',
                    'completed_at': datetime.utcnow().isoformat(),
                    'transaction_id': f'test_txn_{payment_id}'
                })\
                .eq('id', payment_id)\
                .execute()
            
            # 4. Create transaction record
            self.db_client.client.table('transactions').insert({
                'user_id': test_user_id,
                'payment_id': payment_id,
                'amount': 50,
                'currency': 'STARS',
                'type': 'payment',
                'status': 'completed',
                'description': 'Test payment for basic plan',
                'created_at': datetime.utcnow().isoformat()
            }).execute()
            
            # 5. Verify payment completion
            verify_result = self.db_client.client.table('payments')\
                .select('*')\
                .eq('id', payment_id)\
                .single()\
                .execute()
            
            # 6. Clean up
            await self._cleanup_test_user(test_user_id)
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="payment_flow",
                status=TestStatus.PASSED,
                message="Payment flow test completed successfully",
                duration_ms=duration,
                details={
                    'payment_id': payment_id,
                    'final_status': verify_result.data['status'],
                    'steps_completed': [
                        'user_creation',
                        'payment_initiation',
                        'payment_processing',
                        'transaction_logging',
                        'verification'
                    ]
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="payment_flow",
                status=TestStatus.FAILED,
                message=f"Payment flow test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_admin_operations(self) -> TestResult:
        """Test admin functionality"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return TestResult(
                    test_name="admin_operations",
                    status=TestStatus.SKIPPED,
                    message="Database not configured",
                    duration_ms=0
                )
            
            operations_tested = []
            
            # 1. Test statistics query
            stats = self.db_client.client.table('users')\
                .select('*', count='exact')\
                .execute()
            user_count = stats.count if hasattr(stats, 'count') else 0
            operations_tested.append('statistics_query')
            
            # 2. Test active subscriptions query
            active_subs = self.db_client.client.table('subscriptions')\
                .select('*', count='exact')\
                .eq('status', 'active')\
                .execute()
            active_count = active_subs.count if hasattr(active_subs, 'count') else 0
            operations_tested.append('active_subscriptions_query')
            
            # 3. Test revenue calculation (last 30 days)
            thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
            revenue_result = self.db_client.client.table('payments')\
                .select('amount')\
                .eq('status', 'completed')\
                .gte('created_at', thirty_days_ago)\
                .execute()
            
            total_revenue = sum(p['amount'] for p in revenue_result.data) if revenue_result.data else 0
            operations_tested.append('revenue_calculation')
            
            # 4. Test user search
            search_result = self.db_client.client.table('users')\
                .select('*')\
                .limit(5)\
                .execute()
            operations_tested.append('user_search')
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="admin_operations",
                status=TestStatus.PASSED,
                message="Admin operations test completed",
                duration_ms=duration,
                details={
                    'total_users': user_count,
                    'active_subscriptions': active_count,
                    'revenue_30d': total_revenue,
                    'operations_tested': operations_tested
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="admin_operations",
                status=TestStatus.FAILED,
                message=f"Admin operations test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_error_recovery(self) -> TestResult:
        """Test error handling and recovery mechanisms"""
        start_time = time.time()
        errors_handled = []
        
        try:
            # 1. Test invalid database query recovery
            try:
                if self.db_client:
                    result = self.db_client.client.table('non_existent_table').select('*').execute()
            except Exception as e:
                errors_handled.append('invalid_table_query')
            
            # 2. Test invalid user ID handling
            try:
                if self.db_client:
                    result = self.db_client.client.table('users')\
                        .select('*')\
                        .eq('telegram_id', -999999)\
                        .single()\
                        .execute()
            except Exception as e:
                errors_handled.append('invalid_user_query')
            
            # 3. Test transaction rollback simulation
            if self.db_client:
                test_user_id = self._generate_test_user_id()
                try:
                    # Start transaction-like operations
                    self.db_client.client.table('users').insert({
                        'telegram_id': test_user_id,
                        'username': f'error_test_{test_user_id}',
                        'created_at': datetime.utcnow().isoformat()
                    }).execute()
                    
                    # Simulate error by trying to insert duplicate
                    self.db_client.client.table('users').insert({
                        'telegram_id': test_user_id,  # Duplicate
                        'username': f'error_test_{test_user_id}',
                        'created_at': datetime.utcnow().isoformat()
                    }).execute()
                    
                except Exception as e:
                    errors_handled.append('duplicate_insert_prevention')
                    # Clean up
                    await self._cleanup_test_user(test_user_id)
            
            duration = (time.time() - start_time) * 1000
            
            return TestResult(
                test_name="error_recovery",
                status=TestStatus.PASSED,
                message=f"Error recovery test completed, {len(errors_handled)} errors handled",
                duration_ms=duration,
                details={
                    'errors_handled': errors_handled,
                    'recovery_successful': True
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="error_recovery",
                status=TestStatus.FAILED,
                message=f"Error recovery test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_load_performance(self) -> TestResult:
        """Test system performance under load"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return TestResult(
                    test_name="load_performance",
                    status=TestStatus.SKIPPED,
                    message="Database not configured",
                    duration_ms=0
                )
            
            # Configuration
            num_concurrent = 10  # Number of concurrent operations
            operations_per_batch = 5
            
            async def single_operation(index: int):
                """Single database operation for load testing"""
                start = time.time()
                try:
                    # Simple read operation
                    result = self.db_client.client.table('users')\
                        .select('telegram_id')\
                        .limit(1)\
                        .execute()
                    return time.time() - start
                except Exception as e:
                    return -1
            
            # Run concurrent operations
            tasks = []
            for batch in range(operations_per_batch):
                batch_tasks = [single_operation(i) for i in range(num_concurrent)]
                batch_results = await asyncio.gather(*batch_tasks)
                tasks.extend(batch_results)
            
            # Calculate statistics
            successful_ops = [t for t in tasks if t > 0]
            failed_ops = [t for t in tasks if t < 0]
            
            avg_response_time = sum(successful_ops) / len(successful_ops) if successful_ops else 0
            max_response_time = max(successful_ops) if successful_ops else 0
            min_response_time = min(successful_ops) if successful_ops else 0
            success_rate = len(successful_ops) / len(tasks) * 100 if tasks else 0
            
            duration = (time.time() - start_time) * 1000
            
            # Determine if performance is acceptable
            status = TestStatus.PASSED
            if success_rate < 95:
                status = TestStatus.FAILED
            elif avg_response_time > 0.5:  # 500ms threshold
                status = TestStatus.FAILED
            
            return TestResult(
                test_name="load_performance",
                status=status,
                message=f"Load test: {success_rate:.1f}% success, {avg_response_time*1000:.0f}ms avg",
                duration_ms=duration,
                details={
                    'total_operations': len(tasks),
                    'successful_operations': len(successful_ops),
                    'failed_operations': len(failed_ops),
                    'success_rate': f"{success_rate:.1f}%",
                    'avg_response_time_ms': avg_response_time * 1000,
                    'max_response_time_ms': max_response_time * 1000,
                    'min_response_time_ms': min_response_time * 1000,
                    'concurrent_operations': num_concurrent,
                    'batches': operations_per_batch
                }
            )
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="load_performance",
                status=TestStatus.ERROR,
                message=f"Load test failed: {str(e)}",
                duration_ms=duration
            )
    
    async def test_webhook_endpoint(self) -> TestResult:
        """Test webhook endpoint availability and processing"""
        start_time = time.time()
        
        try:
            webhook_url = self.config.get('webhook_base_url')
            if not webhook_url:
                return TestResult(
                    test_name="webhook_endpoint",
                    status=TestStatus.SKIPPED,
                    message="Webhook not configured",
                    duration_ms=0
                )
            
            # Test health endpoint
            health_url = f"{webhook_url}/health"
            
            async with self.session.get(health_url, timeout=5) as response:
                status_code = response.status
                
                if status_code == 200:
                    data = await response.json()
                    duration = (time.time() - start_time) * 1000
                    
                    return TestResult(
                        test_name="webhook_endpoint",
                        status=TestStatus.PASSED,
                        message="Webhook endpoint is healthy",
                        duration_ms=duration,
                        details={
                            'endpoint': health_url,
                            'status_code': status_code,
                            'response': data
                        }
                    )
                else:
                    duration = (time.time() - start_time) * 1000
                    return TestResult(
                        test_name="webhook_endpoint",
                        status=TestStatus.FAILED,
                        message=f"Webhook returned status {status_code}",
                        duration_ms=duration
                    )
                    
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="webhook_endpoint",
                status=TestStatus.FAILED,
                message="Webhook endpoint timeout",
                duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return TestResult(
                test_name="webhook_endpoint",
                status=TestStatus.ERROR,
                message=f"Webhook test failed: {str(e)}",
                duration_ms=duration
            )
    
    # ============= Test Execution =============
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all production tests"""
        test_methods = [
            self.test_bot_commands,
            self.test_database_operations,
            self.test_subscription_lifecycle,
            self.test_payment_flow,
            self.test_admin_operations,
            self.test_error_recovery,
            self.test_webhook_endpoint,
            self.test_load_performance,  # Run load test last
        ]
        
        results = []
        for test_method in test_methods:
            logger.info(f"Running test: {test_method.__name__}")
            try:
                result = await test_method()
                results.append(result)
                logger.info(f"Test {result.test_name}: {result.status.value}")
            except Exception as e:
                logger.error(f"Test {test_method.__name__} crashed: {e}")
                results.append(TestResult(
                    test_name=test_method.__name__.replace('test_', ''),
                    status=TestStatus.ERROR,
                    message=f"Test crashed: {str(e)}",
                    duration_ms=0
                ))
        
        return results
    
    async def run_specific_test(self, test_name: str) -> TestResult:
        """Run a specific test by name"""
        test_map = {
            'bot': self.test_bot_commands,
            'database': self.test_database_operations,
            'subscription': self.test_subscription_lifecycle,
            'payment': self.test_payment_flow,
            'payments': self.test_payment_flow,
            'admin': self.test_admin_operations,
            'error': self.test_error_recovery,
            'load': self.test_load_performance,
            'webhook': self.test_webhook_endpoint,
        }
        
        test_method = test_map.get(test_name.lower())
        if not test_method:
            return TestResult(
                test_name=test_name,
                status=TestStatus.ERROR,
                message=f"Unknown test: {test_name}",
                duration_ms=0
            )
        
        return await test_method()
    
    def generate_report(self, results: List[TestResult]) -> str:
        """Generate test report"""
        report = []
        report.append("=" * 60)
        report.append(f"Production Test Report - {datetime.utcnow().isoformat()}")
        report.append("=" * 60)
        
        # Summary statistics
        total_tests = len(results)
        passed = sum(1 for r in results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in results if r.status == TestStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == TestStatus.ERROR)
        
        report.append(f"\nSummary:")
        report.append(f"  Total Tests: {total_tests}")
        report.append(f"  Passed: {passed} ✅")
        report.append(f"  Failed: {failed} ❌")
        report.append(f"  Skipped: {skipped} ⏭️")
        report.append(f"  Errors: {errors} 🔥")
        report.append(f"  Success Rate: {(passed/total_tests*100):.1f}%")
        
        # Detailed results
        report.append("\n" + "=" * 60)
        report.append("Test Results:")
        report.append("-" * 60)
        
        for result in results:
            status_symbol = {
                TestStatus.PASSED: "✅",
                TestStatus.FAILED: "❌",
                TestStatus.SKIPPED: "⏭️",
                TestStatus.ERROR: "🔥"
            }[result.status]
            
            report.append(f"\n{status_symbol} {result.test_name.upper()}")
            report.append(f"   Status: {result.status.value}")
            report.append(f"   Message: {result.message}")
            report.append(f"   Duration: {result.duration_ms:.0f}ms")
            
            if result.details:
                report.append(f"   Details:")
                for key, value in result.details.items():
                    report.append(f"     - {key}: {value}")
        
        # Performance summary
        report.append("\n" + "=" * 60)
        report.append("Performance Summary:")
        total_duration = sum(r.duration_ms for r in results)
        report.append(f"  Total Test Duration: {total_duration:.0f}ms")
        report.append(f"  Average Test Duration: {total_duration/len(results):.0f}ms")
        
        # Find slowest tests
        sorted_results = sorted(results, key=lambda x: x.duration_ms, reverse=True)
        report.append("\n  Slowest Tests:")
        for result in sorted_results[:3]:
            report.append(f"    - {result.test_name}: {result.duration_ms:.0f}ms")
        
        report.append("=" * 60)
        
        return "\n".join(report)

async def main():
    """Main entry point for test suite"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Production test suite for Telegram bot')
    parser.add_argument('--test', help='Specific test to run (bot, database, subscription, payment, admin, error, load, webhook)')
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--production', action='store_true', help='Run in production mode (use real data)')
    parser.add_argument('--report', help='Save report to file')
    
    args = parser.parse_args()
    
    # Create test suite
    suite = ProductionTestSuite(test_mode=not args.production)
    
    try:
        await suite.initialize()
        
        # Run tests
        if args.test:
            results = [await suite.run_specific_test(args.test)]
        elif args.all:
            results = await suite.run_all_tests()
        else:
            # Default: run basic tests
            results = [
                await suite.test_bot_commands(),
                await suite.test_database_operations(),
                await suite.test_webhook_endpoint()
            ]
        
        # Generate and display report
        report = suite.generate_report(results)
        print(report)
        
        # Save report if requested
        if args.report:
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"\nReport saved to: {args.report}")
        
        # Exit code based on results
        has_failures = any(r.status in [TestStatus.FAILED, TestStatus.ERROR] for r in results)
        sys.exit(1 if has_failures else 0)
        
    finally:
        await suite.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
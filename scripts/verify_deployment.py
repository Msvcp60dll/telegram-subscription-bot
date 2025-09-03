#!/usr/bin/env python3
"""
Quick Deployment Verification Script
Run this immediately after Railway deployment to verify everything is working
"""

import asyncio
import sys
import os
import time
from datetime import datetime
from typing import Tuple, List

# Try to import required modules
try:
    import aiohttp
    from aiogram import Bot
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database.supabase_client import SupabaseClient
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)

class DeploymentVerifier:
    """Quick verification of production deployment"""
    
    def __init__(self):
        self.checks_passed = []
        self.checks_failed = []
        self.warnings = []
        
        # Load configuration
        self.bot_token = os.getenv('BOT_TOKEN')
        self.group_id = os.getenv('GROUP_ID')
        self.admin_user_id = os.getenv('ADMIN_USER_ID')
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        
    async def run_all_checks(self) -> bool:
        """Run all verification checks"""
        print("=" * 60)
        print(f"DEPLOYMENT VERIFICATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Check environment variables
        print("\n1. Checking Environment Variables...")
        self.check_environment_variables()
        
        # Check bot connection
        print("\n2. Checking Bot Connection...")
        await self.check_bot_connection()
        
        # Check database connection
        print("\n3. Checking Database Connection...")
        await self.check_database_connection()
        
        # Check webhook endpoint
        print("\n4. Checking Webhook Endpoint...")
        await self.check_webhook_endpoint()
        
        # Check admin dashboard
        print("\n5. Checking Admin Dashboard...")
        await self.check_admin_dashboard()
        
        # Print summary
        self.print_summary()
        
        return len(self.checks_failed) == 0
    
    def check_environment_variables(self):
        """Verify all required environment variables are set"""
        required_vars = {
            'BOT_TOKEN': self.bot_token,
            'GROUP_ID': self.group_id,
            'ADMIN_USER_ID': self.admin_user_id,
            'SUPABASE_URL': self.supabase_url,
            'SUPABASE_SERVICE_KEY': self.supabase_key
        }
        
        optional_vars = {
            'WEBHOOK_BASE_URL': self.webhook_base_url,
            'AIRWALLEX_CLIENT_ID': os.getenv('AIRWALLEX_CLIENT_ID'),
            'AIRWALLEX_API_KEY': os.getenv('AIRWALLEX_API_KEY')
        }
        
        for var_name, var_value in required_vars.items():
            if var_value:
                print(f"   ✅ {var_name}: Set")
                self.checks_passed.append(f"{var_name} configured")
            else:
                print(f"   ❌ {var_name}: Missing!")
                self.checks_failed.append(f"{var_name} not configured")
        
        for var_name, var_value in optional_vars.items():
            if var_value:
                print(f"   ✅ {var_name}: Set")
                self.checks_passed.append(f"{var_name} configured")
            else:
                print(f"   ⚠️  {var_name}: Not set (optional)")
                self.warnings.append(f"{var_name} not configured (optional)")
    
    async def check_bot_connection(self):
        """Verify bot can connect to Telegram"""
        if not self.bot_token:
            print("   ⏭️  Skipping - Bot token not configured")
            return
        
        bot = None
        try:
            bot = Bot(token=self.bot_token)
            bot_info = await bot.get_me()
            print(f"   ✅ Bot connected: @{bot_info.username} (ID: {bot_info.id})")
            self.checks_passed.append(f"Bot @{bot_info.username} connected")
            
            # Check group access if configured
            if self.group_id:
                try:
                    group_info = await bot.get_chat(int(self.group_id))
                    print(f"   ✅ Group accessible: {group_info.title}")
                    self.checks_passed.append(f"Group {group_info.title} accessible")
                except Exception as e:
                    print(f"   ❌ Group not accessible: {e}")
                    self.checks_failed.append(f"Cannot access group {self.group_id}")
            
        except Exception as e:
            print(f"   ❌ Bot connection failed: {e}")
            self.checks_failed.append(f"Bot connection failed: {str(e)[:50]}")
        finally:
            if bot:
                await bot.session.close()
    
    async def check_database_connection(self):
        """Verify database connectivity"""
        if not self.supabase_url or not self.supabase_key:
            print("   ⏭️  Skipping - Database not configured")
            return
        
        try:
            db_client = SupabaseClient(self.supabase_url, self.supabase_key)
            
            # Test basic query
            result = db_client.client.table('users').select('telegram_id').limit(1).execute()
            print(f"   ✅ Database connected: Supabase")
            self.checks_passed.append("Database connection successful")
            
            # Check tables exist
            tables_to_check = ['users', 'subscriptions', 'payments', 'transactions']
            for table in tables_to_check:
                try:
                    db_client.client.table(table).select('id').limit(1).execute()
                    print(f"   ✅ Table '{table}' accessible")
                    self.checks_passed.append(f"Table {table} exists")
                except Exception as e:
                    print(f"   ❌ Table '{table}' not accessible: {e}")
                    self.checks_failed.append(f"Table {table} not accessible")
            
        except Exception as e:
            print(f"   ❌ Database connection failed: {e}")
            self.checks_failed.append(f"Database connection failed: {str(e)[:50]}")
    
    async def check_webhook_endpoint(self):
        """Check webhook endpoint availability"""
        if not self.webhook_base_url:
            print("   ⏭️  Skipping - Webhook URL not configured")
            return
        
        health_url = f"{self.webhook_base_url}/health"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(health_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"   ✅ Webhook endpoint healthy: {health_url}")
                        self.checks_passed.append("Webhook endpoint operational")
                        
                        # Check components
                        components = data.get('components', {})
                        for comp, status in components.items():
                            if status == 'operational':
                                print(f"   ✅ {comp}: {status}")
                            else:
                                print(f"   ⚠️  {comp}: {status}")
                    else:
                        print(f"   ❌ Webhook endpoint returned status {response.status}")
                        self.checks_failed.append(f"Webhook unhealthy (status {response.status})")
                        
            except asyncio.TimeoutError:
                print(f"   ❌ Webhook endpoint timeout")
                self.checks_failed.append("Webhook endpoint timeout")
            except Exception as e:
                print(f"   ❌ Webhook check failed: {e}")
                self.checks_failed.append(f"Webhook check failed: {str(e)[:50]}")
    
    async def check_admin_dashboard(self):
        """Check admin dashboard availability"""
        if not self.webhook_base_url:
            print("   ⏭️  Skipping - Base URL not configured")
            return
        
        # Admin dashboard runs on port 8081
        dashboard_url = f"{self.webhook_base_url}:8081/"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(dashboard_url, timeout=10) as response:
                    if response.status == 200:
                        print(f"   ✅ Admin dashboard accessible: {dashboard_url}")
                        self.checks_passed.append("Admin dashboard operational")
                    else:
                        print(f"   ⚠️  Admin dashboard returned status {response.status}")
                        self.warnings.append(f"Admin dashboard status {response.status}")
                        
            except Exception as e:
                print(f"   ⚠️  Admin dashboard not accessible: {e}")
                self.warnings.append("Admin dashboard not accessible")
    
    def print_summary(self):
        """Print verification summary"""
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        total_checks = len(self.checks_passed) + len(self.checks_failed)
        
        print(f"\n📊 Results:")
        print(f"   Total Checks: {total_checks}")
        print(f"   ✅ Passed: {len(self.checks_passed)}")
        print(f"   ❌ Failed: {len(self.checks_failed)}")
        print(f"   ⚠️  Warnings: {len(self.warnings)}")
        
        if self.checks_failed:
            print(f"\n❌ Failed Checks:")
            for check in self.checks_failed:
                print(f"   - {check}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        print("\n" + "=" * 60)
        
        if not self.checks_failed:
            print("✅ DEPLOYMENT VERIFICATION SUCCESSFUL!")
            print("All critical systems are operational.")
        else:
            print("❌ DEPLOYMENT VERIFICATION FAILED!")
            print("Please address the failed checks before proceeding.")
        
        print("=" * 60)
        
        # Provide next steps
        print("\n📝 Next Steps:")
        if not self.checks_failed:
            print("1. Test bot commands: /start, /status, /help")
            print("2. Test payment flow with a small transaction")
            print("3. Verify admin commands work")
            print("4. Monitor logs: railway logs --tail")
            print("5. Run full test suite: python scripts/production_tests.py --all")
        else:
            print("1. Fix the failed checks listed above")
            print("2. Re-run this verification script")
            print("3. Check Railway logs for more details: railway logs --tail 100")

async def main():
    """Main entry point"""
    print("Starting deployment verification...")
    print("This will check all critical systems and configurations.")
    print("")
    
    verifier = DeploymentVerifier()
    
    try:
        success = await verifier.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    # Check if running in Railway environment
    if os.getenv('RAILWAY_ENVIRONMENT'):
        print("🚂 Running in Railway environment")
    else:
        print("💻 Running in local environment")
    
    asyncio.run(main())
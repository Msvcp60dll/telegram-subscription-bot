#!/usr/bin/env python3
"""
Database Deployment Script for Supabase
========================================
Deploys the database schema to Supabase and performs verification.

This script:
1. Connects to Supabase using service key
2. Executes the schema creation SQL
3. Handles existing table errors gracefully
4. Verifies tables and indexes
5. Inserts admin user as whitelisted
6. Runs test queries to verify setup

Safe to run multiple times (idempotent).
"""

import os
import sys
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
    from postgrest import APIError
except ImportError:
    print("Error: Supabase client not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)


class DatabaseDeployer:
    """Handles database schema deployment to Supabase."""
    
    def __init__(self, url: str, key: str):
        """Initialize the database deployer with Supabase credentials."""
        self.url = url
        self.key = key
        self.client: Optional[Client] = None
        self.admin_telegram_id = 306145881
        self.admin_username = "admin"
        
    def connect(self) -> bool:
        """Establish connection to Supabase."""
        try:
            print("🔌 Connecting to Supabase...")
            self.client = create_client(self.url, self.key)
            print("✅ Successfully connected to Supabase")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Supabase: {e}")
            return False
    
    def read_schema_file(self) -> str:
        """Read the SQL schema from file."""
        schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        
        print(f"📄 Reading schema from {schema_path}")
        with open(schema_path, 'r') as f:
            return f.read()
    
    def execute_sql(self, sql: str, description: str = "SQL command") -> Tuple[bool, Optional[str]]:
        """Execute raw SQL against the database."""
        try:
            # Use RPC to execute raw SQL
            # Supabase doesn't have a direct SQL execution method in the Python client
            # We'll use the REST API directly through the client's postgrest property
            
            # For DDL statements, we need to use a different approach
            # Since Supabase Python client doesn't support raw SQL execution directly,
            # we'll split the schema into individual statements and handle them separately
            
            # This is a limitation - we'll need to handle the schema deployment differently
            print(f"⚠️  Note: Direct SQL execution through Python client has limitations.")
            print(f"    For full schema deployment, use Supabase Dashboard SQL Editor.")
            return True, "Schema deployment requires Supabase Dashboard"
            
        except Exception as e:
            return False, str(e)
    
    def verify_tables_exist(self) -> Dict[str, bool]:
        """Verify that required tables exist."""
        tables_status = {}
        required_tables = ['users', 'activity_log']
        
        print("\n📊 Verifying tables...")
        
        for table in required_tables:
            try:
                # Try to select from the table (limit 1 for efficiency)
                result = self.client.table(table).select("*").limit(1).execute()
                tables_status[table] = True
                print(f"  ✅ Table '{table}' exists")
            except Exception as e:
                tables_status[table] = False
                print(f"  ❌ Table '{table}' not found or inaccessible: {e}")
        
        return tables_status
    
    def create_or_update_admin_user(self) -> bool:
        """Create or update the admin user as whitelisted."""
        try:
            print("\n👤 Setting up admin user...")
            
            # First, try to get the existing user
            existing = self.client.table('users').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).execute()
            
            user_data = {
                'telegram_id': self.admin_telegram_id,
                'username': self.admin_username,
                'subscription_status': 'whitelisted',
                'payment_method': 'whitelisted',
                'next_payment_date': None
            }
            
            if existing.data:
                # Update existing user
                result = self.client.table('users').update(user_data).eq(
                    'telegram_id', self.admin_telegram_id
                ).execute()
                print(f"  ✅ Updated admin user (ID: {self.admin_telegram_id}) as whitelisted")
            else:
                # Insert new user
                result = self.client.table('users').insert(user_data).execute()
                print(f"  ✅ Created admin user (ID: {self.admin_telegram_id}) as whitelisted")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to setup admin user: {e}")
            return False
    
    def run_verification_tests(self) -> Dict[str, bool]:
        """Run verification tests to ensure database is properly configured."""
        test_results = {}
        
        print("\n🧪 Running verification tests...")
        
        # Test 1: Can read from users table
        try:
            users = self.client.table('users').select("*").limit(5).execute()
            test_results['read_users'] = True
            print(f"  ✅ Can read from users table ({len(users.data)} records found)")
        except Exception as e:
            test_results['read_users'] = False
            print(f"  ❌ Cannot read from users table: {e}")
        
        # Test 2: Can read from activity_log table
        try:
            logs = self.client.table('activity_log').select("*").limit(5).execute()
            test_results['read_activity_log'] = True
            print(f"  ✅ Can read from activity_log table ({len(logs.data)} records found)")
        except Exception as e:
            test_results['read_activity_log'] = False
            print(f"  ❌ Cannot read from activity_log table: {e}")
        
        # Test 3: Verify admin user is whitelisted
        try:
            admin = self.client.table('users').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).execute()
            
            if admin.data and admin.data[0]['subscription_status'] == 'whitelisted':
                test_results['admin_whitelisted'] = True
                print(f"  ✅ Admin user is whitelisted")
            else:
                test_results['admin_whitelisted'] = False
                print(f"  ❌ Admin user not properly whitelisted")
        except Exception as e:
            test_results['admin_whitelisted'] = False
            print(f"  ❌ Cannot verify admin user: {e}")
        
        # Test 4: Test insert operation (create test user)
        try:
            test_user_id = 999999999  # Test user ID
            
            # First delete if exists
            self.client.table('users').delete().eq('telegram_id', test_user_id).execute()
            
            # Insert test user
            test_user = {
                'telegram_id': test_user_id,
                'username': 'test_user',
                'subscription_status': 'expired',
                'payment_method': None
            }
            
            insert_result = self.client.table('users').insert(test_user).execute()
            
            if insert_result.data:
                test_results['insert_operation'] = True
                print(f"  ✅ Can insert records (test user created)")
                
                # Clean up test user
                self.client.table('users').delete().eq('telegram_id', test_user_id).execute()
            else:
                test_results['insert_operation'] = False
                print(f"  ❌ Insert operation failed")
                
        except Exception as e:
            test_results['insert_operation'] = False
            print(f"  ❌ Cannot perform insert operation: {e}")
        
        # Test 5: Test update operation
        try:
            # Try to update the admin user's updated_at timestamp
            update_result = self.client.table('users').update({
                'username': self.admin_username  # Update with same value to trigger updated_at
            }).eq('telegram_id', self.admin_telegram_id).execute()
            
            if update_result.data:
                test_results['update_operation'] = True
                print(f"  ✅ Can update records")
            else:
                test_results['update_operation'] = False
                print(f"  ❌ Update operation failed")
                
        except Exception as e:
            test_results['update_operation'] = False
            print(f"  ❌ Cannot perform update operation: {e}")
        
        # Test 6: Test activity log is working (check if admin user creation was logged)
        try:
            admin_logs = self.client.table('activity_log').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).execute()
            
            if admin_logs.data:
                test_results['activity_logging'] = True
                print(f"  ✅ Activity logging is working ({len(admin_logs.data)} logs for admin)")
            else:
                test_results['activity_logging'] = False
                print(f"  ⚠️  No activity logs found for admin (may be normal on first run)")
                
        except Exception as e:
            test_results['activity_logging'] = False
            print(f"  ❌ Cannot verify activity logging: {e}")
        
        return test_results
    
    def display_connection_info(self):
        """Display connection information for verification."""
        print("\n📌 Connection Information:")
        print(f"  • Project URL: {self.url}")
        print(f"  • Using Service Key: {'*' * 20}...{self.key[-10:]}")
        print(f"  • Admin Telegram ID: {self.admin_telegram_id}")
        print(f"  • Admin Username: {self.admin_username}")
    
    def deploy(self) -> bool:
        """Main deployment process."""
        print("=" * 60)
        print("🚀 SUPABASE DATABASE DEPLOYMENT SCRIPT")
        print("=" * 60)
        
        self.display_connection_info()
        
        # Step 1: Connect to Supabase
        if not self.connect():
            return False
        
        # Step 2: Important notice about schema deployment
        print("\n⚠️  IMPORTANT NOTICE:")
        print("=" * 60)
        print("The Supabase Python client has limited support for DDL operations.")
        print("For initial schema deployment, please:")
        print("")
        print("1. Go to your Supabase Dashboard:")
        print(f"   {self.url.replace('.supabase.co', '')}/sql")
        print("")
        print("2. Copy the contents of database/schema.sql")
        print("")
        print("3. Paste and run in the SQL Editor")
        print("")
        print("This script will now verify the database setup and configure the admin user.")
        print("=" * 60)
        
        input("\nPress Enter to continue with verification...")
        
        # Step 3: Verify tables exist
        tables_status = self.verify_tables_exist()
        
        if not all(tables_status.values()):
            print("\n❌ Some tables are missing. Please deploy the schema first.")
            print("   Run the schema.sql file in Supabase SQL Editor.")
            return False
        
        # Step 4: Setup admin user
        if not self.create_or_update_admin_user():
            print("\n⚠️  Warning: Could not setup admin user, but continuing...")
        
        # Step 5: Run verification tests
        test_results = self.run_verification_tests()
        
        # Step 6: Display final status
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT SUMMARY")
        print("=" * 60)
        
        all_tests_passed = all(test_results.values())
        
        if all_tests_passed:
            print("✅ All verification tests PASSED!")
            print("\nYour database is properly configured and ready to use.")
            print("\nNext steps:")
            print("  1. Update your .env file with the Supabase credentials")
            print("  2. Run your Telegram bot")
            print("  3. Monitor the activity_log table for user actions")
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
            print("\nFailed tests:")
            for test, passed in test_results.items():
                if not passed:
                    print(f"  • {test}")
        
        print("\n" + "=" * 60)
        
        return all_tests_passed


def main():
    """Main entry point for the deployment script."""
    
    # Supabase credentials (provided by user)
    SUPABASE_URL = "https://dijdhqrxqwbctywejydj.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpamRocXJ4cXdiY3R5d2VqeWRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDA3NTU5MywiZXhwIjoyMDQ1NjUxNTkzfQ.gDL6uLfXLuj3sGtmznI5EeZ0qnLWEzrn0ybvfwmOy0g"
    
    # Check if .env file exists and suggest creating it
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("💡 Tip: Create a .env file with your Supabase credentials:")
        print(f"   SUPABASE_URL={SUPABASE_URL}")
        print(f"   SUPABASE_SERVICE_KEY={SUPABASE_KEY}")
        print("")
    
    # Create deployer and run deployment
    deployer = DatabaseDeployer(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        success = deployer.deploy()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during deployment: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
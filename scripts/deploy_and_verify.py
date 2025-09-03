#!/usr/bin/env python3
"""
Supabase Database Deployment and Verification Script
====================================================
This script verifies database deployment and sets up initial data.

IMPORTANT: Before running this script, you must deploy the schema manually:

1. Go to Supabase SQL Editor:
   https://dijdhqrxqwbctywejydj.supabase.co/project/dijdhqrxqwbctywejydj/sql/new

2. Copy ALL contents from database/schema.sql

3. Paste in SQL Editor and click "Run"

4. Then run this script to verify and setup admin user
"""

import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: Supabase not installed. Run: pip install supabase")
    sys.exit(1)


class DatabaseVerifier:
    """Verifies database deployment and sets up initial data."""
    
    def __init__(self):
        """Initialize with Supabase credentials."""
        self.url = "https://dijdhqrxqwbctywejydj.supabase.co"
        self.key = "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1"  # Service key as provided
        self.admin_telegram_id = 306145881
        self.admin_username = "admin"
        self.client: Optional[Client] = None
        
    def connect(self) -> bool:
        """Connect to Supabase."""
        try:
            print("🔌 Connecting to Supabase...")
            self.client = create_client(self.url, self.key)
            print("✅ Connected successfully")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def check_tables(self) -> Dict[str, bool]:
        """Check if required tables exist."""
        tables = {
            'users': False,
            'activity_log': False
        }
        
        print("\n📊 Checking tables...")
        
        for table in tables.keys():
            try:
                result = self.client.table(table).select("count").limit(1).execute()
                tables[table] = True
                print(f"  ✅ Table '{table}' exists")
            except Exception as e:
                error = str(e)
                if "PGRST205" in error or "not find the table" in error:
                    print(f"  ❌ Table '{table}' NOT FOUND - Deploy schema first!")
                else:
                    print(f"  ⚠️  Table '{table}' error: {error[:50]}")
        
        return tables
    
    def setup_admin_user(self) -> bool:
        """Create or update admin user as whitelisted."""
        try:
            print("\n👤 Setting up admin user...")
            
            # Check if user exists
            existing = self.client.table('users').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).execute()
            
            user_data = {
                'telegram_id': self.admin_telegram_id,
                'username': self.admin_username,
                'subscription_status': 'whitelisted',
                'payment_method': 'whitelisted',
                'next_payment_date': None,
                'airwallex_payment_id': None,
                'stars_transaction_id': None
            }
            
            if existing.data:
                # Update existing
                result = self.client.table('users').update({
                    'subscription_status': 'whitelisted',
                    'payment_method': 'whitelisted',
                    'username': self.admin_username,
                    'next_payment_date': None
                }).eq('telegram_id', self.admin_telegram_id).execute()
                
                print(f"  ✅ Updated admin user @{self.admin_username} (ID: {self.admin_telegram_id})")
            else:
                # Insert new
                result = self.client.table('users').insert(user_data).execute()
                print(f"  ✅ Created admin user @{self.admin_username} (ID: {self.admin_telegram_id})")
            
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to setup admin user: {e}")
            return False
    
    def run_tests(self) -> Dict[str, bool]:
        """Run comprehensive tests."""
        tests = {}
        
        print("\n🧪 Running verification tests...")
        
        # Test 1: Read users
        try:
            users = self.client.table('users').select("*").execute()
            tests['read_users'] = True
            print(f"  ✅ Can read users table ({len(users.data)} users)")
        except Exception as e:
            tests['read_users'] = False
            print(f"  ❌ Cannot read users: {e}")
        
        # Test 2: Read activity log
        try:
            logs = self.client.table('activity_log').select("*").limit(10).execute()
            tests['read_logs'] = True
            print(f"  ✅ Can read activity log ({len(logs.data)} entries)")
        except Exception as e:
            tests['read_logs'] = False
            print(f"  ❌ Cannot read activity log: {e}")
        
        # Test 3: Verify admin is whitelisted
        try:
            admin = self.client.table('users').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).single().execute()
            
            if admin.data['subscription_status'] == 'whitelisted':
                tests['admin_whitelisted'] = True
                print(f"  ✅ Admin user is whitelisted")
            else:
                tests['admin_whitelisted'] = False
                print(f"  ❌ Admin user status: {admin.data['subscription_status']}")
        except Exception as e:
            tests['admin_whitelisted'] = False
            print(f"  ❌ Cannot verify admin: {e}")
        
        # Test 4: Test insert (create test user)
        try:
            test_id = 999999999
            
            # Delete if exists
            self.client.table('users').delete().eq('telegram_id', test_id).execute()
            
            # Insert test user
            test_user = {
                'telegram_id': test_id,
                'username': 'test_user',
                'subscription_status': 'expired'
            }
            
            result = self.client.table('users').insert(test_user).execute()
            
            if result.data:
                tests['insert_works'] = True
                print(f"  ✅ Can insert records")
                
                # Clean up
                self.client.table('users').delete().eq('telegram_id', test_id).execute()
            else:
                tests['insert_works'] = False
                print(f"  ❌ Insert failed")
                
        except Exception as e:
            tests['insert_works'] = False
            print(f"  ❌ Cannot insert: {e}")
        
        # Test 5: Test update
        try:
            result = self.client.table('users').update({
                'username': self.admin_username
            }).eq('telegram_id', self.admin_telegram_id).execute()
            
            if result.data:
                tests['update_works'] = True
                print(f"  ✅ Can update records")
            else:
                tests['update_works'] = False
                print(f"  ❌ Update failed")
                
        except Exception as e:
            tests['update_works'] = False
            print(f"  ❌ Cannot update: {e}")
        
        # Test 6: Check activity logs for admin
        try:
            admin_logs = self.client.table('activity_log').select("*").eq(
                'telegram_id', self.admin_telegram_id
            ).execute()
            
            if admin_logs.data:
                tests['logging_works'] = True
                print(f"  ✅ Activity logging works ({len(admin_logs.data)} admin logs)")
                
                # Show recent logs
                if admin_logs.data:
                    print("\n  📝 Recent admin activity:")
                    for log in admin_logs.data[:3]:
                        print(f"     • {log['action']} at {log['timestamp']}")
            else:
                tests['logging_works'] = False
                print(f"  ⚠️  No activity logs for admin yet")
                
        except Exception as e:
            tests['logging_works'] = False
            print(f"  ❌ Cannot check logs: {e}")
        
        return tests
    
    def create_sample_users(self) -> bool:
        """Create sample users for testing."""
        print("\n👥 Creating sample users for testing...")
        
        sample_users = [
            {
                'telegram_id': 123456789,
                'username': 'john_doe',
                'subscription_status': 'active',
                'payment_method': 'card',
                'next_payment_date': '2025-01-15'
            },
            {
                'telegram_id': 987654321,
                'username': 'jane_smith',
                'subscription_status': 'expired',
                'payment_method': 'stars',
                'next_payment_date': '2024-12-01'
            },
            {
                'telegram_id': 555555555,
                'username': 'test_user',
                'subscription_status': 'active',
                'payment_method': 'stars',
                'next_payment_date': '2025-01-20'
            }
        ]
        
        created = 0
        for user in sample_users:
            try:
                # Check if exists
                existing = self.client.table('users').select("telegram_id").eq(
                    'telegram_id', user['telegram_id']
                ).execute()
                
                if not existing.data:
                    self.client.table('users').insert(user).execute()
                    created += 1
                    print(f"  ✅ Created user: @{user['username']}")
                else:
                    print(f"  ⚠️  User already exists: @{user['username']}")
                    
            except Exception as e:
                print(f"  ❌ Failed to create {user['username']}: {e}")
        
        print(f"  📊 Created {created} new sample users")
        return created > 0
    
    def display_summary(self, tables: Dict, tests: Dict):
        """Display final summary."""
        print("\n" + "=" * 70)
        print("📋 DEPLOYMENT VERIFICATION SUMMARY")
        print("=" * 70)
        
        all_tables = all(tables.values())
        all_tests = all(tests.values())
        
        if not all_tables:
            print("\n⚠️  SCHEMA NOT DEPLOYED!")
            print("\nTo deploy the database schema:")
            print(f"1. Go to: {self.url}/project/dijdhqrxqwbctywejydj/sql/new")
            print("2. Copy contents of database/schema.sql")
            print("3. Paste and click 'Run'")
            print("4. Run this script again")
        elif all_tests:
            print("\n✅ DATABASE FULLY OPERATIONAL!")
            print("\nYour database is ready for production use.")
            
            # Display current users
            try:
                users = self.client.table('users').select("*").execute()
                print(f"\n📊 Current Users ({len(users.data)} total):")
                for user in users.data:
                    status_emoji = {
                        'active': '🟢',
                        'expired': '🔴',
                        'whitelisted': '⭐'
                    }.get(user['subscription_status'], '❓')
                    
                    print(f"  {status_emoji} @{user['username'] or 'unknown'} " +
                          f"(ID: {user['telegram_id']}) - {user['subscription_status']}")
            except:
                pass
                
            print("\n📝 Next Steps:")
            print("  1. Create .env file with credentials")
            print("  2. Run your Telegram bot")
            print("  3. Test subscription commands")
            print("  4. Monitor activity_log table")
        else:
            print("\n⚠️  Some tests failed. Review issues above.")
            failed = [name for name, passed in tests.items() if not passed]
            if failed:
                print(f"\nFailed tests: {', '.join(failed)}")
        
        print("\n🔐 Connection Details:")
        print(f"  • Project URL: {self.url}")
        print(f"  • Service Key: {self.key[:20]}...{self.key[-10:]}")
        print(f"  • Admin User: {self.admin_telegram_id} (@{self.admin_username})")
        
        print("\n" + "=" * 70)
        
        return all_tables and all_tests
    
    def run(self) -> bool:
        """Run the complete verification process."""
        print("=" * 70)
        print("🚀 SUPABASE DATABASE DEPLOYMENT VERIFICATION")
        print("=" * 70)
        
        if not self.connect():
            return False
        
        tables = self.check_tables()
        
        if all(tables.values()):
            # Tables exist, proceed with setup
            self.setup_admin_user()
            self.create_sample_users()
            tests = self.run_tests()
        else:
            # Tables don't exist
            tests = {}
            print("\n❌ Cannot proceed - database schema not deployed")
        
        success = self.display_summary(tables, tests)
        
        # Create .env file template if it doesn't exist
        env_path = Path(__file__).parent.parent / ".env"
        if not env_path.exists() and success:
            print("\n📝 Creating .env file template...")
            env_content = f"""# Supabase Configuration
SUPABASE_URL={self.url}
SUPABASE_SERVICE_KEY={self.key}

# Telegram Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Admin Configuration
ADMIN_TELEGRAM_ID={self.admin_telegram_id}
ADMIN_USERNAME={self.admin_username}

# Payment Configuration
AIRWALLEX_API_KEY=YOUR_AIRWALLEX_KEY_HERE
TELEGRAM_STARS_ENABLED=true

# Environment
ENVIRONMENT=production
"""
            with open(env_path, 'w') as f:
                f.write(env_content)
            print(f"  ✅ Created .env file at {env_path}")
            print("     ⚠️  Remember to add your BOT_TOKEN!")
        
        return success


def main():
    """Main entry point."""
    verifier = DatabaseVerifier()
    
    try:
        success = verifier.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
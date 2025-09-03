#!/usr/bin/env python3
"""
Complete Database Setup Script for Supabase
Reads schema.sql and provides instructions for deployment
"""

import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ Supabase library not installed. Run: pip install supabase")
    sys.exit(1)

from database.supabase_client import SupabaseClient, SubscriptionStatus

# Configuration
SUPABASE_URL = "https://dijdhqrxqwbctywejydj.supabase.co"
SUPABASE_KEY = "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1"
ADMIN_TELEGRAM_ID = 306145881

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def read_schema():
    """Read the SQL schema file"""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    if not schema_path.exists():
        print(f"❌ Schema file not found at: {schema_path}")
        return None
    
    with open(schema_path, 'r') as f:
        return f.read()

def check_tables_exist(client: Client):
    """Check if required tables exist"""
    tables_exist = {}
    
    try:
        # Try to query users table
        client.table('users').select('*').limit(1).execute()
        tables_exist['users'] = True
    except:
        tables_exist['users'] = False
    
    try:
        # Try to query activity_log table
        client.table('activity_log').select('*').limit(1).execute()
        tables_exist['activity_log'] = True
    except:
        tables_exist['activity_log'] = False
    
    return tables_exist

def setup_admin_user(db_client: SupabaseClient):
    """Set up the admin user as whitelisted"""
    try:
        # Check if admin exists
        admin = db_client.get_user(ADMIN_TELEGRAM_ID)
        
        if admin:
            print(f"  ✅ Admin user exists: {admin.telegram_id} (@{admin.username})")
            if admin.subscription_status != SubscriptionStatus.WHITELISTED.value:
                # Update to whitelisted
                db_client.whitelist_user(ADMIN_TELEGRAM_ID)
                print(f"  ✅ Admin user whitelisted")
        else:
            # Create admin user
            db_client.create_user(
                telegram_id=ADMIN_TELEGRAM_ID,
                username="admin",
                subscription_status=SubscriptionStatus.WHITELISTED.value,
                payment_method="whitelisted"
            )
            print(f"  ✅ Admin user created and whitelisted: {ADMIN_TELEGRAM_ID}")
            
        return True
    except Exception as e:
        print(f"  ❌ Error setting up admin: {e}")
        return False

def main():
    """Main deployment process"""
    print_header("SUPABASE DATABASE SETUP")
    
    # Read schema
    print("\n📖 Reading schema file...")
    schema_sql = read_schema()
    if not schema_sql:
        sys.exit(1)
    print("  ✅ Schema file loaded")
    
    # Connect to Supabase
    print("\n🔌 Connecting to Supabase...")
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("  ✅ Connected successfully")
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        sys.exit(1)
    
    # Check tables
    print("\n📊 Checking existing tables...")
    tables = check_tables_exist(client)
    
    if not all(tables.values()):
        print_header("⚠️  MANUAL DEPLOYMENT REQUIRED")
        
        print("\nThe database schema needs to be deployed manually.")
        print("\n📋 Follow these steps:\n")
        print("1. Open your browser and go to:")
        print(f"   {SUPABASE_URL}/project/dijdhqrxqwbctywejydj/sql/new")
        print("\n2. Copy ALL the SQL from this file:")
        print(f"   {Path(__file__).parent.parent / 'database' / 'schema.sql'}")
        print("\n3. Paste it into the SQL Editor")
        print("\n4. Click 'Run' button (or press Ctrl/Cmd + Enter)")
        print("\n5. You should see: 'Success. No rows returned'")
        print("\n6. Run this script again after deployment")
        
        print("\n" + "=" * 70)
        print("📝 Quick Copy Command:")
        print("=" * 70)
        print("Run this to copy the schema to clipboard (Mac):")
        print(f"cat {Path(__file__).parent.parent}/database/schema.sql | pbcopy")
        
        print("\n" + "=" * 70)
        print("🔗 Direct Link to SQL Editor:")
        print("=" * 70)
        print(f"{SUPABASE_URL}/project/dijdhqrxqwbctywejydj/sql/new")
        
        print("\n❌ Please deploy the schema manually first, then run this script again.")
        sys.exit(1)
    
    print("  ✅ All required tables found!")
    
    # Setup admin user
    print("\n👤 Setting up admin user...")
    db_client = SupabaseClient(SUPABASE_URL, SUPABASE_KEY)
    if setup_admin_user(db_client):
        print("  ✅ Admin setup complete")
    
    # Run verification tests
    print("\n🧪 Running verification tests...")
    
    # Test user operations
    test_user_id = 123456789
    try:
        # Create test user
        test_user = db_client.create_user(
            telegram_id=test_user_id,
            username="test_user",
            subscription_status="active"
        )
        print("  ✅ Create user: SUCCESS")
        
        # Read test user
        user = db_client.get_user(test_user_id)
        if user:
            print("  ✅ Read user: SUCCESS")
        
        # Update test user
        db_client.update_user(
            telegram_id=test_user_id,
            subscription_status="expired"
        )
        print("  ✅ Update user: SUCCESS")
        
        # Log activity
        db_client.log_activity(
            telegram_id=test_user_id,
            action="subscription_expired",
            details={"test": True}
        )
        print("  ✅ Log activity: SUCCESS")
        
        # Delete test user (cleanup)
        client.table('users').delete().eq('telegram_id', test_user_id).execute()
        print("  ✅ Delete user: SUCCESS")
        
    except Exception as e:
        print(f"  ❌ Test failed: {e}")
    
    # Get statistics
    print("\n📊 Database Statistics:")
    try:
        stats = db_client.get_subscription_stats()
        print(f"  • Total users: {stats.get('total_users', 0)}")
        print(f"  • Active subscriptions: {stats.get('active_count', 0)}")
        print(f"  • Whitelisted users: {stats.get('whitelisted_count', 0)}")
        print(f"  • Expired subscriptions: {stats.get('expired_count', 0)}")
    except Exception as e:
        print(f"  ❌ Could not get statistics: {e}")
    
    # Success summary
    print_header("✅ DATABASE SETUP COMPLETE")
    print("\n🎉 Your database is ready!")
    print("\n📋 Next steps:")
    print("  1. Start your bot: python main.py")
    print("  2. Access admin dashboard: http://localhost:8081/")
    print("  3. Migrate existing members: python scripts/migrate_existing_members.py")
    print("  4. Deploy to Railway: ./deploy.sh")
    
    print("\n🔐 Admin Credentials:")
    print(f"  • Telegram ID: {ADMIN_TELEGRAM_ID}")
    print("  • Username: @admin")
    print("  • Status: WHITELISTED (permanent free access)")
    
    print("\n" + "=" * 70)
    print("✨ Happy botting!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
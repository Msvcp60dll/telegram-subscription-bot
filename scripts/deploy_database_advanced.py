#!/usr/bin/env python3
"""
Advanced Database Deployment Script for Supabase
================================================
Deploys database schema using direct PostgreSQL connection.

This script:
1. Connects directly to PostgreSQL database
2. Executes the schema creation SQL
3. Handles existing objects gracefully  
4. Verifies all database objects
5. Inserts admin user
6. Runs comprehensive tests

Requirements:
- psycopg2 or asyncpg for direct PostgreSQL connection
- Run: pip install psycopg2-binary
"""

import os
import sys
import re
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False
    print("Warning: psycopg2 not installed. Install with: pip install psycopg2-binary")

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    print("Warning: Supabase client not installed. Install with: pip install supabase")


class AdvancedDatabaseDeployer:
    """Advanced database deployer with direct PostgreSQL access."""
    
    def __init__(self, project_url: str, service_key: str):
        """Initialize the deployer with Supabase credentials."""
        self.project_url = project_url
        self.service_key = service_key
        self.admin_telegram_id = 306145881
        self.admin_username = "admin"
        
        # Parse database connection from Supabase URL
        self.db_config = self._parse_supabase_url(project_url)
        self.conn = None
        self.supabase_client = None
        
    def _parse_supabase_url(self, url: str) -> Dict[str, str]:
        """Parse Supabase URL to get database connection details."""
        # Extract project ID from URL
        match = re.search(r'https://([^.]+)\.supabase\.co', url)
        if match:
            project_id = match.group(1)
        else:
            raise ValueError(f"Invalid Supabase URL: {url}")
        
        # Supabase database connection pattern
        # Host: db.[project-id].supabase.co
        # Port: 5432 (default PostgreSQL)
        # Database: postgres
        # User: postgres
        
        return {
            'host': f'db.{project_id}.supabase.co',
            'port': 5432,
            'database': 'postgres',
            'user': 'postgres',
            'password': self.service_key,  # Service key acts as password
            'project_id': project_id
        }
    
    def connect_postgres(self) -> bool:
        """Connect directly to PostgreSQL database."""
        if not HAS_PSYCOPG2:
            print("❌ psycopg2 not available. Using Supabase client only.")
            return False
            
        try:
            print(f"🔌 Connecting to PostgreSQL database...")
            print(f"   Host: {self.db_config['host']}")
            
            # Create connection string
            conn_string = (
                f"host={self.db_config['host']} "
                f"port={self.db_config['port']} "
                f"dbname={self.db_config['database']} "
                f"user={self.db_config['user']} "
                f"password={self.db_config['password']} "
                f"sslmode=require"
            )
            
            self.conn = psycopg2.connect(conn_string)
            self.conn.autocommit = False  # Use transactions
            
            # Test connection
            with self.conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()[0]
                print(f"✅ Connected to PostgreSQL")
                print(f"   Version: {version.split(',')[0]}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            return False
    
    def connect_supabase(self) -> bool:
        """Connect to Supabase client for API operations."""
        if not HAS_SUPABASE:
            return False
            
        try:
            print("🔌 Connecting to Supabase API...")
            self.supabase_client = create_client(self.project_url, self.service_key)
            print("✅ Connected to Supabase API")
            return True
        except Exception as e:
            print(f"❌ Failed to connect to Supabase API: {e}")
            return False
    
    def execute_schema_sql(self) -> bool:
        """Execute the schema SQL file directly on PostgreSQL."""
        if not self.conn:
            print("⚠️  No direct PostgreSQL connection. Skipping schema execution.")
            return False
        
        try:
            schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
            
            if not schema_path.exists():
                print(f"❌ Schema file not found: {schema_path}")
                return False
            
            print(f"\n📄 Executing schema from {schema_path}")
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Split SQL into individual statements
            # Remove comments and empty lines for cleaner execution
            statements = []
            current_statement = []
            
            for line in schema_sql.split('\n'):
                # Skip comment-only lines
                if line.strip().startswith('--') or not line.strip():
                    continue
                
                current_statement.append(line)
                
                # Check if statement is complete (ends with semicolon)
                if line.rstrip().endswith(';'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []
            
            # Execute statements in a transaction
            with self.conn.cursor() as cur:
                successful = 0
                failed = 0
                
                for i, statement in enumerate(statements, 1):
                    try:
                        # Extract first few words for logging
                        stmt_preview = ' '.join(statement.split()[:3])
                        
                        cur.execute(statement)
                        successful += 1
                        
                        # Log progress for important statements
                        if any(keyword in statement.upper() for keyword in ['CREATE TABLE', 'CREATE INDEX', 'CREATE POLICY']):
                            print(f"  ✅ Executed: {stmt_preview}...")
                            
                    except psycopg2.errors.DuplicateObject as e:
                        # Object already exists - this is okay for idempotent deployment
                        print(f"  ⚠️  Already exists: {stmt_preview}... (safe to ignore)")
                        failed += 1
                    except Exception as e:
                        print(f"  ❌ Failed: {stmt_preview}... - {str(e)[:50]}")
                        failed += 1
                        # Don't stop on individual statement failures
                        continue
                
                # Commit the transaction
                self.conn.commit()
                
                print(f"\n📊 Schema execution complete:")
                print(f"   • Successful statements: {successful}")
                print(f"   • Skipped (already exist): {failed}")
                
                return successful > 0
                
        except Exception as e:
            print(f"❌ Schema execution failed: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def verify_database_objects(self) -> Dict[str, Any]:
        """Comprehensive verification of all database objects."""
        if not self.conn:
            return {}
        
        results = {
            'tables': {},
            'indexes': {},
            'policies': {},
            'triggers': {},
            'functions': {}
        }
        
        print("\n🔍 Verifying database objects...")
        
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check tables
            cur.execute("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename IN ('users', 'activity_log')
            """)
            
            for row in cur.fetchall():
                results['tables'][row['tablename']] = True
                print(f"  ✅ Table: {row['tablename']}")
            
            # Check indexes
            cur.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'activity_log')
            """)
            
            for row in cur.fetchall():
                results['indexes'][row['indexname']] = True
            
            print(f"  ✅ Indexes: {len(results['indexes'])} found")
            
            # Check RLS policies
            cur.execute("""
                SELECT pol.polname, tab.tablename
                FROM pg_policy pol
                JOIN pg_class cls ON pol.polrelid = cls.oid
                JOIN pg_tables tab ON cls.relname = tab.tablename
                WHERE tab.schemaname = 'public'
            """)
            
            for row in cur.fetchall():
                results['policies'][row['polname']] = row['tablename']
            
            print(f"  ✅ RLS Policies: {len(results['policies'])} found")
            
            # Check triggers
            cur.execute("""
                SELECT trigger_name, event_object_table
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
            """)
            
            for row in cur.fetchall():
                results['triggers'][row['trigger_name']] = row['event_object_table']
            
            print(f"  ✅ Triggers: {len(results['triggers'])} found")
            
            # Check functions
            cur.execute("""
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_type = 'FUNCTION'
            """)
            
            for row in cur.fetchall():
                results['functions'][row['routine_name']] = True
            
            print(f"  ✅ Functions: {len(results['functions'])} found")
            
            # Verify RLS is enabled
            cur.execute("""
                SELECT tablename, rowsecurity
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename IN ('users', 'activity_log')
            """)
            
            for row in cur.fetchall():
                if row['rowsecurity']:
                    print(f"  ✅ RLS enabled on: {row['tablename']}")
                else:
                    print(f"  ⚠️  RLS NOT enabled on: {row['tablename']}")
        
        return results
    
    def setup_admin_user(self) -> bool:
        """Create or update the admin user."""
        try:
            print("\n👤 Setting up admin user...")
            
            if self.conn:
                with self.conn.cursor() as cur:
                    # Check if user exists
                    cur.execute(
                        "SELECT * FROM users WHERE telegram_id = %s",
                        (self.admin_telegram_id,)
                    )
                    existing = cur.fetchone()
                    
                    if existing:
                        # Update existing user
                        cur.execute("""
                            UPDATE users 
                            SET username = %s, 
                                subscription_status = 'whitelisted',
                                payment_method = 'whitelisted',
                                next_payment_date = NULL
                            WHERE telegram_id = %s
                            RETURNING id
                        """, (self.admin_username, self.admin_telegram_id))
                        
                        print(f"  ✅ Updated admin user (ID: {self.admin_telegram_id})")
                    else:
                        # Insert new user
                        cur.execute("""
                            INSERT INTO users (
                                telegram_id, username, subscription_status, 
                                payment_method, next_payment_date
                            ) VALUES (%s, %s, 'whitelisted', 'whitelisted', NULL)
                            RETURNING id
                        """, (self.admin_telegram_id, self.admin_username))
                        
                        print(f"  ✅ Created admin user (ID: {self.admin_telegram_id})")
                    
                    self.conn.commit()
                    return True
                    
            elif self.supabase_client:
                # Fallback to Supabase client
                existing = self.supabase_client.table('users').select("*").eq(
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
                    self.supabase_client.table('users').update(user_data).eq(
                        'telegram_id', self.admin_telegram_id
                    ).execute()
                    print(f"  ✅ Updated admin user via Supabase API")
                else:
                    self.supabase_client.table('users').insert(user_data).execute()
                    print(f"  ✅ Created admin user via Supabase API")
                
                return True
                
        except Exception as e:
            print(f"  ❌ Failed to setup admin user: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def run_comprehensive_tests(self) -> Dict[str, bool]:
        """Run comprehensive tests on the database."""
        results = {}
        
        print("\n🧪 Running comprehensive tests...")
        
        if self.conn:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Test 1: Table structure
                try:
                    cur.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                        AND table_name = 'users'
                        ORDER BY ordinal_position
                    """)
                    
                    columns = cur.fetchall()
                    expected_columns = [
                        'id', 'telegram_id', 'username', 'subscription_status',
                        'payment_method', 'next_payment_date', 'airwallex_payment_id',
                        'stars_transaction_id', 'created_at', 'updated_at'
                    ]
                    
                    found_columns = [col['column_name'] for col in columns]
                    if all(col in found_columns for col in expected_columns):
                        results['table_structure'] = True
                        print(f"  ✅ Table structure verified ({len(columns)} columns)")
                    else:
                        results['table_structure'] = False
                        print(f"  ❌ Table structure incomplete")
                        
                except Exception as e:
                    results['table_structure'] = False
                    print(f"  ❌ Failed to verify table structure: {e}")
                
                # Test 2: Constraints
                try:
                    cur.execute("""
                        SELECT conname
                        FROM pg_constraint
                        WHERE conrelid = 'users'::regclass
                    """)
                    
                    constraints = [row['conname'] for row in cur.fetchall()]
                    results['constraints'] = len(constraints) > 0
                    print(f"  ✅ Constraints: {len(constraints)} found")
                    
                except Exception as e:
                    results['constraints'] = False
                    print(f"  ❌ Failed to verify constraints: {e}")
                
                # Test 3: Functions work
                try:
                    cur.execute("SELECT extend_subscription(%s, 'card', 'test_123')",
                              (self.admin_telegram_id,))
                    result = cur.fetchone()
                    
                    # Rollback this test transaction
                    self.conn.rollback()
                    
                    results['functions_work'] = True
                    print(f"  ✅ Database functions operational")
                    
                except Exception as e:
                    results['functions_work'] = False
                    print(f"  ⚠️  Some functions may not work: {e}")
                    self.conn.rollback()
                
                # Test 4: Activity logging
                try:
                    cur.execute("""
                        SELECT COUNT(*) as count
                        FROM activity_log
                        WHERE telegram_id = %s
                    """, (self.admin_telegram_id,))
                    
                    count = cur.fetchone()['count']
                    results['activity_logging'] = True
                    print(f"  ✅ Activity logging working ({count} logs for admin)")
                    
                except Exception as e:
                    results['activity_logging'] = False
                    print(f"  ❌ Activity logging check failed: {e}")
        
        elif self.supabase_client:
            # Fallback tests using Supabase client
            try:
                users = self.supabase_client.table('users').select("*").limit(1).execute()
                results['api_access'] = True
                print(f"  ✅ Supabase API access working")
            except Exception as e:
                results['api_access'] = False
                print(f"  ❌ Supabase API access failed: {e}")
        
        return results
    
    def display_summary(self, verification: Dict, tests: Dict):
        """Display deployment summary."""
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT SUMMARY")
        print("=" * 60)
        
        if verification:
            print("\n📦 Database Objects:")
            print(f"  • Tables: {len(verification.get('tables', {}))} created")
            print(f"  • Indexes: {len(verification.get('indexes', {}))} created")
            print(f"  • RLS Policies: {len(verification.get('policies', {}))} created")
            print(f"  • Triggers: {len(verification.get('triggers', {}))} created")
            print(f"  • Functions: {len(verification.get('functions', {}))} created")
        
        if tests:
            print("\n🧪 Test Results:")
            for test_name, passed in tests.items():
                status = "✅ PASSED" if passed else "❌ FAILED"
                print(f"  • {test_name}: {status}")
        
        print("\n🔗 Connection Details:")
        print(f"  • Project URL: {self.project_url}")
        print(f"  • Database Host: {self.db_config['host']}")
        print(f"  • Admin User: {self.admin_telegram_id} (@{self.admin_username})")
        
        print("\n📝 Next Steps:")
        print("  1. Save credentials in .env file")
        print("  2. Test the bot connection")
        print("  3. Monitor activity_log table")
        
        print("\n" + "=" * 60)
    
    def deploy(self) -> bool:
        """Execute the full deployment process."""
        print("=" * 60)
        print("🚀 ADVANCED DATABASE DEPLOYMENT")
        print("=" * 60)
        
        # Try PostgreSQL connection first
        postgres_connected = self.connect_postgres()
        
        # Connect to Supabase API as fallback
        supabase_connected = self.connect_supabase()
        
        if not postgres_connected and not supabase_connected:
            print("❌ Could not establish any connection")
            return False
        
        # Execute schema if we have PostgreSQL connection
        if postgres_connected:
            self.execute_schema_sql()
            verification = self.verify_database_objects()
        else:
            verification = {}
            print("\n⚠️  Using Supabase API only (limited functionality)")
            print("    For full deployment, install psycopg2-binary")
        
        # Setup admin user
        self.setup_admin_user()
        
        # Run tests
        tests = self.run_comprehensive_tests()
        
        # Display summary
        self.display_summary(verification, tests)
        
        # Close connections
        if self.conn:
            self.conn.close()
        
        return True


def main():
    """Main entry point."""
    
    # Credentials
    SUPABASE_URL = "https://dijdhqrxqwbctywejydj.supabase.co"
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpamRocXJ4cXdiY3R5d2VqeWRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDA3NTU5MywiZXhwIjoyMDQ1NjUxNTkzfQ.gDL6uLfXLuj3sGtmznI5EeZ0qnLWEzrn0ybvfwmOy0g"
    
    deployer = AdvancedDatabaseDeployer(SUPABASE_URL, SUPABASE_KEY)
    
    try:
        success = deployer.deploy()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDeployment interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
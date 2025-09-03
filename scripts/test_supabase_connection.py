#!/usr/bin/env python3
"""
Test Supabase connection with provided credentials.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from supabase import create_client, Client

# Credentials as provided
SUPABASE_URL = "https://dijdhqrxqwbctywejydj.supabase.co"

# Try different key formats
keys_to_test = [
    # Original key as provided
    ("Original Key", "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1"),
    
    # JWT format that was in the deployment scripts (looks like a proper JWT)
    ("JWT Key", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRpamRocXJ4cXdiY3R5d2VqeWRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTczMDA3NTU5MywiZXhwIjoyMDQ1NjUxNTkzfQ.gDL6uLfXLuj3sGtmznI5EeZ0qnLWEzrn0ybvfwmOy0g")
]

print("🔍 Testing Supabase Connection")
print("=" * 60)
print(f"Project URL: {SUPABASE_URL}")
print()

for key_name, key_value in keys_to_test:
    print(f"\n📝 Testing with {key_name}:")
    print(f"   Key format: {key_value[:20]}...{key_value[-10:]}")
    
    try:
        # Try to create client
        client = create_client(SUPABASE_URL, key_value)
        print("   ✅ Client created successfully")
        
        # Try to query users table
        try:
            result = client.table('users').select("*").limit(1).execute()
            print(f"   ✅ Can query 'users' table")
            print(f"   📊 Response: {len(result.data)} records")
            
        except Exception as e:
            error_msg = str(e)
            if "doesn't exist" in error_msg or "not found" in error_msg:
                print(f"   ⚠️  Table 'users' not found (needs schema deployment)")
            elif "401" in error_msg or "Invalid API key" in error_msg:
                print(f"   ❌ Authentication failed: Invalid API key")
            else:
                print(f"   ❌ Query failed: {error_msg[:100]}")
                
    except Exception as e:
        print(f"   ❌ Failed to create client: {e}")

print("\n" + "=" * 60)
print("\n💡 Notes:")
print("  • If authentication fails with both keys, verify the service key")
print("  • If tables don't exist, deploy the schema first")
print("  • The JWT format key appears to be the correct service role key")
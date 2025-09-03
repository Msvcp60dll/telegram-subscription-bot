# Supabase Reference Guide

**Version**: Latest  
**Last Updated**: 2025-09-03  
**Official Documentation**: https://supabase.com/docs

## Table of Contents
1. [Python Client Setup](#python-client-setup)
2. [Basic CRUD Operations](#basic-crud-operations)
3. [Row Level Security (RLS) Policies](#row-level-security-rls-policies)
4. [PostgreSQL Table Creation](#postgresql-table-creation)
5. [Connection Handling](#connection-handling)
6. [Advanced Patterns](#advanced-patterns)

## Python Client Setup

### Installation
```bash
pip install supabase
```

### Basic Client Initialization
```python
from supabase import create_client, Client
from typing import Optional
import os

# Basic setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY")

# Create client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
```

### Advanced Client Configuration
```python
from supabase import create_client, Client
from supabase.client import ClientOptions
import httpx

class SupabaseService:
    def __init__(
        self,
        url: str,
        key: str,
        service_key: Optional[str] = None
    ):
        # Client with custom options
        options = ClientOptions(
            schema="public",  # Default schema
            headers={
                "x-custom-header": "value"
            },
            auto_refresh_token=True,  # Auto refresh auth tokens
            persist_session=True,  # Persist session to storage
        )
        
        # Public client (with anon key)
        self.client = create_client(url, key, options)
        
        # Service client (with service key for admin operations)
        if service_key:
            self.service_client = create_client(url, service_key, options)
    
    def get_client(self, use_service_role: bool = False) -> Client:
        """Get appropriate client based on requirements"""
        if use_service_role and hasattr(self, 'service_client'):
            return self.service_client
        return self.client
```

## Basic CRUD Operations

### CREATE - Insert Operations
```python
# Single row insert
async def create_user(user_data: dict):
    response = supabase.table("users").insert(user_data).execute()
    return response.data

# Multiple rows insert
async def create_multiple_users(users_list: list):
    response = supabase.table("users").insert(users_list).execute()
    return response.data

# Insert with return specific columns
async def create_and_return_id(data: dict):
    response = (
        supabase.table("products")
        .insert(data)
        .select("id, created_at")
        .execute()
    )
    return response.data

# Upsert (insert or update if exists)
async def upsert_user(user_data: dict):
    response = (
        supabase.table("users")
        .upsert(user_data, on_conflict="email")
        .execute()
    )
    return response.data
```

### READ - Select Operations
```python
# Select all columns
async def get_all_users():
    response = supabase.table("users").select("*").execute()
    return response.data

# Select specific columns
async def get_user_names():
    response = supabase.table("users").select("id, name, email").execute()
    return response.data

# With filters
async def get_active_users():
    response = (
        supabase.table("users")
        .select("*")
        .eq("status", "active")
        .execute()
    )
    return response.data

# Complex filters
async def get_filtered_users(min_age: int, country: str):
    response = (
        supabase.table("users")
        .select("*")
        .gte("age", min_age)  # Greater than or equal
        .eq("country", country)
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )
    return response.data

# Join related tables
async def get_users_with_profiles():
    response = (
        supabase.table("users")
        .select("*, profiles(*)")  # Join profiles table
        .execute()
    )
    return response.data

# Text search
async def search_users(search_term: str):
    response = (
        supabase.table("users")
        .select("*")
        .text_search("name", search_term)
        .execute()
    )
    return response.data

# Range queries
async def get_users_in_age_range(min_age: int, max_age: int):
    response = (
        supabase.table("users")
        .select("*")
        .gte("age", min_age)
        .lte("age", max_age)
        .execute()
    )
    return response.data
```

### UPDATE - Update Operations
```python
# Update single row by ID
async def update_user(user_id: int, update_data: dict):
    response = (
        supabase.table("users")
        .update(update_data)
        .eq("id", user_id)
        .execute()
    )
    return response.data

# Update multiple rows
async def deactivate_old_users(days_inactive: int):
    cutoff_date = datetime.now() - timedelta(days=days_inactive)
    response = (
        supabase.table("users")
        .update({"status": "inactive"})
        .lt("last_login", cutoff_date.isoformat())
        .execute()
    )
    return response.data

# Increment/decrement values
async def increment_user_credits(user_id: int, amount: int):
    response = (
        supabase.table("users")
        .update({"credits": f"credits + {amount}"})
        .eq("id", user_id)
        .execute()
    )
    return response.data

# Update with return
async def update_and_return(user_id: int, data: dict):
    response = (
        supabase.table("users")
        .update(data)
        .eq("id", user_id)
        .select()
        .execute()
    )
    return response.data
```

### DELETE - Delete Operations
```python
# Delete single row
async def delete_user(user_id: int):
    response = (
        supabase.table("users")
        .delete()
        .eq("id", user_id)
        .execute()
    )
    return response.data

# Delete multiple rows
async def delete_inactive_users():
    response = (
        supabase.table("users")
        .delete()
        .eq("status", "inactive")
        .execute()
    )
    return response.data

# Delete with conditions
async def delete_old_logs(days_old: int):
    cutoff_date = datetime.now() - timedelta(days=days_old)
    response = (
        supabase.table("logs")
        .delete()
        .lt("created_at", cutoff_date.isoformat())
        .execute()
    )
    return response.data
```

## Row Level Security (RLS) Policies

### Enable RLS on Tables
```sql
-- Enable RLS on a table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Enable RLS on multiple tables
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
```

### Basic RLS Policies
```sql
-- Allow users to see only their own data
CREATE POLICY "Users can view own data"
ON users
FOR SELECT
USING (auth.uid() = id);

-- Allow users to update only their own data
CREATE POLICY "Users can update own data"
ON users
FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- Allow users to delete only their own data
CREATE POLICY "Users can delete own data"
ON users
FOR DELETE
USING (auth.uid() = id);

-- Allow authenticated users to insert their own data
CREATE POLICY "Users can insert own data"
ON users
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = id);
```

### Advanced RLS Policies
```sql
-- Policy with role-based access
CREATE POLICY "Admins can view all users"
ON users
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_roles.user_id = auth.uid()
        AND user_roles.role = 'admin'
    )
);

-- Time-based access policy
CREATE POLICY "Users can edit recent posts"
ON posts
FOR UPDATE
TO authenticated
USING (
    auth.uid() = user_id 
    AND created_at > NOW() - INTERVAL '24 hours'
);

-- Subscription-based access
CREATE POLICY "Premium users can access premium content"
ON premium_content
FOR SELECT
TO authenticated
USING (
    EXISTS (
        SELECT 1 FROM subscriptions
        WHERE subscriptions.user_id = auth.uid()
        AND subscriptions.status = 'active'
        AND subscriptions.plan IN ('premium', 'pro')
    )
);

-- Organization-based access
CREATE POLICY "Users can view their organization data"
ON organization_data
FOR SELECT
TO authenticated
USING (
    organization_id IN (
        SELECT organization_id 
        FROM organization_members 
        WHERE user_id = auth.uid()
    )
);
```

### RLS Helper Functions
```sql
-- Create helper function for checking user role
CREATE OR REPLACE FUNCTION auth.is_admin()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_roles
        WHERE user_id = auth.uid()
        AND role = 'admin'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Use helper function in policy
CREATE POLICY "Admins can manage all data"
ON sensitive_data
FOR ALL
TO authenticated
USING (auth.is_admin());

-- Function to check subscription status
CREATE OR REPLACE FUNCTION auth.has_active_subscription()
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM subscriptions
        WHERE user_id = auth.uid()
        AND status = 'active'
        AND expires_at > NOW()
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

## PostgreSQL Table Creation

### Users and Authentication Tables
```sql
-- Users table
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

### Subscriptions Table
```sql
-- Subscriptions table
CREATE TABLE subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL CHECK (plan IN ('basic', 'pro', 'premium')),
    status VARCHAR(50) NOT NULL DEFAULT 'pending' 
        CHECK (status IN ('pending', 'active', 'cancelled', 'expired')),
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    started_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);

-- Enable RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
```

### Payments Table
```sql
-- Payments table
CREATE TABLE payments (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'refunded')),
    provider VARCHAR(50) NOT NULL CHECK (provider IN ('telegram_stars', 'airwallex')),
    provider_payment_id VARCHAR(255) UNIQUE,
    provider_charge_id VARCHAR(255),
    payment_method JSONB,
    error_message TEXT,
    paid_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_subscription_id ON payments(subscription_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_provider_payment_id ON payments(provider_payment_id);

-- Enable RLS
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
```

### Audit Logs Table
```sql
-- Audit logs table
CREATE TABLE audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Partitioning by month (optional for large datasets)
-- CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
-- FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
```

### Database Functions and Triggers
```sql
-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to check subscription expiry
CREATE OR REPLACE FUNCTION check_subscription_expiry()
RETURNS void AS $$
BEGIN
    UPDATE subscriptions
    SET status = 'expired'
    WHERE status = 'active'
    AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Schedule function to run periodically (using pg_cron or external scheduler)
```

## Connection Handling

### Connection Pool Management
```python
from supabase import create_client, Client
from typing import Optional
import asyncio
from contextlib import asynccontextmanager

class SupabaseConnectionPool:
    def __init__(self, url: str, key: str, max_connections: int = 10):
        self.url = url
        self.key = key
        self.max_connections = max_connections
        self._pool = []
        self._semaphore = asyncio.Semaphore(max_connections)
    
    @asynccontextmanager
    async def get_connection(self) -> Client:
        """Get a connection from the pool"""
        async with self._semaphore:
            if self._pool:
                client = self._pool.pop()
            else:
                client = create_client(self.url, self.key)
            
            try:
                yield client
            finally:
                # Return connection to pool
                if len(self._pool) < self.max_connections:
                    self._pool.append(client)
```

### Retry Logic and Error Handling
```python
import time
from typing import TypeVar, Callable, Optional
from functools import wraps

T = TypeVar('T')

def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
):
    """Decorator for retrying Supabase operations"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    
                    if attempt >= max_attempts:
                        raise
                    
                    print(f"Attempt {attempt} failed: {e}")
                    print(f"Retrying in {current_delay} seconds...")
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise Exception(f"Failed after {max_attempts} attempts")
        
        return wrapper
    return decorator

# Usage
@with_retry(max_attempts=3, delay=1.0)
def fetch_user(user_id: int):
    response = supabase.table("users").select("*").eq("id", user_id).execute()
    return response.data
```

### Transaction Handling
```python
class SupabaseTransaction:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.operations = []
    
    def add_operation(self, table: str, operation: str, data: dict, filters: dict = None):
        """Add operation to transaction"""
        self.operations.append({
            "table": table,
            "operation": operation,
            "data": data,
            "filters": filters
        })
    
    async def execute(self):
        """Execute all operations in transaction"""
        results = []
        
        try:
            for op in self.operations:
                if op["operation"] == "insert":
                    result = self.supabase.table(op["table"]).insert(op["data"]).execute()
                elif op["operation"] == "update":
                    query = self.supabase.table(op["table"]).update(op["data"])
                    for key, value in op["filters"].items():
                        query = query.eq(key, value)
                    result = query.execute()
                elif op["operation"] == "delete":
                    query = self.supabase.table(op["table"]).delete()
                    for key, value in op["filters"].items():
                        query = query.eq(key, value)
                    result = query.execute()
                
                results.append(result)
            
            return results
            
        except Exception as e:
            # Rollback logic would go here
            raise Exception(f"Transaction failed: {e}")
```

## Advanced Patterns

### Real-time Subscriptions
```python
# Subscribe to changes
def handle_changes(payload):
    print(f"Change received: {payload}")

# Subscribe to INSERT events
channel = supabase.channel('db-changes')
channel.on_postgres_changes(
    event='INSERT',
    schema='public',
    table='messages',
    callback=handle_changes
).subscribe()

# Subscribe to all changes for a table
channel = supabase.channel('all-changes')
channel.on_postgres_changes(
    event='*',  # Listen to INSERT, UPDATE, DELETE
    schema='public',
    table='users',
    callback=handle_changes
).subscribe()

# Filter subscriptions
channel = supabase.channel('user-changes')
channel.on_postgres_changes(
    event='UPDATE',
    schema='public',
    table='users',
    filter=f'id=eq.{user_id}',
    callback=handle_changes
).subscribe()
```

### Storage Operations
```python
# Upload file
def upload_file(file_path: str, bucket: str, file_name: str):
    with open(file_path, 'rb') as file:
        response = supabase.storage.from_(bucket).upload(
            path=file_name,
            file=file,
            file_options={"content-type": "image/png"}
        )
    return response

# Download file
def download_file(bucket: str, file_path: str):
    response = supabase.storage.from_(bucket).download(file_path)
    return response

# Get public URL
def get_public_url(bucket: str, file_path: str):
    response = supabase.storage.from_(bucket).get_public_url(file_path)
    return response

# Delete file
def delete_file(bucket: str, file_path: str):
    response = supabase.storage.from_(bucket).remove([file_path])
    return response
```

### RPC Functions
```sql
-- Create a custom function
CREATE OR REPLACE FUNCTION get_user_subscription_status(user_id_param UUID)
RETURNS TABLE (
    has_subscription BOOLEAN,
    plan VARCHAR,
    expires_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        TRUE as has_subscription,
        s.plan,
        s.expires_at
    FROM subscriptions s
    WHERE s.user_id = user_id_param
    AND s.status = 'active'
    ORDER BY s.expires_at DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, NULL::VARCHAR, NULL::TIMESTAMPTZ;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

```python
# Call RPC function from Python
async def get_subscription_status(user_id: str):
    response = supabase.rpc(
        'get_user_subscription_status',
        {'user_id_param': user_id}
    ).execute()
    return response.data
```

### Batch Operations
```python
async def batch_insert_users(users_data: list, batch_size: int = 100):
    """Insert users in batches"""
    results = []
    
    for i in range(0, len(users_data), batch_size):
        batch = users_data[i:i + batch_size]
        response = supabase.table("users").insert(batch).execute()
        results.extend(response.data)
    
    return results

async def batch_update_status(user_ids: list, new_status: str):
    """Update multiple users' status"""
    response = (
        supabase.table("users")
        .update({"status": new_status})
        .in_("id", user_ids)
        .execute()
    )
    return response.data
```

### Edge Functions Integration
```python
import httpx

async def call_edge_function(function_name: str, payload: dict):
    """Call Supabase Edge Function"""
    
    url = f"{SUPABASE_URL}/functions/v1/{function_name}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers=headers,
            json=payload
        )
        
        response.raise_for_status()
        return response.json()
```

## Error Handling Best Practices

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class SupabaseError(Exception):
    """Base exception for Supabase operations"""
    pass

class SupabaseQueryError(SupabaseError):
    """Query execution error"""
    pass

class SupabaseAuthError(SupabaseError):
    """Authentication error"""
    pass

def safe_query(func):
    """Decorator for safe query execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            response = func(*args, **kwargs)
            
            if hasattr(response, 'error') and response.error:
                logger.error(f"Supabase error: {response.error}")
                raise SupabaseQueryError(response.error)
            
            return response.data if hasattr(response, 'data') else response
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise SupabaseQueryError(f"Query execution failed: {e}")
    
    return wrapper

# Usage
@safe_query
def get_user_by_id(user_id: str):
    return supabase.table("users").select("*").eq("id", user_id).execute()
```

## Performance Optimization

### Query Optimization
```python
# Use select with specific columns instead of *
response = supabase.table("users").select("id, name, email").execute()

# Use limit for pagination
response = (
    supabase.table("users")
    .select("*")
    .range(0, 9)  # Get first 10 records
    .execute()
)

# Use count without fetching data
response = (
    supabase.table("users")
    .select("*", count="exact")
    .eq("status", "active")
    .execute()
)
count = response.count

# Create proper indexes in PostgreSQL
# CREATE INDEX idx_users_status ON users(status);
# CREATE INDEX idx_users_created_at ON users(created_at DESC);
```

### Caching Strategy
```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedSupabase:
    def __init__(self, supabase: Client):
        self.supabase = supabase
        self._cache = {}
        self._cache_expiry = {}
    
    def get_cached(
        self,
        key: str,
        query_func: Callable,
        ttl_seconds: int = 300
    ):
        """Get data with caching"""
        
        # Check if cache is valid
        if key in self._cache:
            if datetime.now() < self._cache_expiry[key]:
                return self._cache[key]
        
        # Fetch fresh data
        data = query_func()
        
        # Update cache
        self._cache[key] = data
        self._cache_expiry[key] = datetime.now() + timedelta(seconds=ttl_seconds)
        
        return data
    
    def invalidate_cache(self, key: Optional[str] = None):
        """Invalidate cache entries"""
        if key:
            self._cache.pop(key, None)
            self._cache_expiry.pop(key, None)
        else:
            self._cache.clear()
            self._cache_expiry.clear()
```

## Security Best Practices

1. **Always enable RLS** on tables in public schema
2. **Use service role key sparingly** - only for admin operations
3. **Validate input data** before database operations
4. **Use parameterized queries** to prevent SQL injection
5. **Implement rate limiting** for API endpoints
6. **Audit sensitive operations** using audit logs
7. **Encrypt sensitive data** before storing
8. **Use environment variables** for credentials
9. **Implement proper session management**
10. **Regular security audits** of RLS policies

## Additional Resources

- Official Documentation: https://supabase.com/docs
- Python Client GitHub: https://github.com/supabase/supabase-py
- RLS Guide: https://supabase.com/docs/guides/database/postgres/row-level-security
- PostgreSQL Documentation: https://www.postgresql.org/docs/
- Community Discord: https://discord.supabase.com/
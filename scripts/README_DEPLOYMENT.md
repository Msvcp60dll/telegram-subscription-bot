# Database Deployment Guide

## Quick Start

Follow these steps to deploy the database to Supabase:

### Step 1: Deploy the Schema (Manual - Required First)

1. **Go to Supabase SQL Editor:**
   ```
   https://dijdhqrxqwbctywejydj.supabase.co/project/dijdhqrxqwbctywejydj/sql/new
   ```

2. **Copy the entire contents of:**
   ```
   database/schema.sql
   ```

3. **Paste into the SQL Editor and click "Run"**

   The schema includes:
   - Tables: `users` and `activity_log`
   - Indexes for performance
   - RLS policies for security
   - Triggers for automatic logging
   - Helper functions for subscription management

### Step 2: Verify Deployment and Setup Admin

After deploying the schema, run the verification script:

```bash
# Make sure you're in the project directory
cd /Users/antongladkov/TGbot

# Activate virtual environment
source venv/bin/activate

# Run verification and setup
python scripts/deploy_and_verify.py
```

This script will:
- ✅ Verify tables were created
- ✅ Setup admin user as whitelisted
- ✅ Create sample users for testing
- ✅ Run comprehensive tests
- ✅ Create .env file template

## Scripts Overview

### 1. `deploy_and_verify.py` (Main Script)
- **Purpose:** Verify deployment and setup initial data
- **When to use:** After manually deploying schema
- **Safe to run multiple times:** Yes

### 2. `test_supabase_connection.py`
- **Purpose:** Test connection to Supabase
- **When to use:** To verify credentials are working
- **Output:** Connection status and basic queries

### 3. `deploy_database.py`
- **Purpose:** Basic deployment helper
- **Note:** Limited by Supabase Python client capabilities
- **Alternative:** Use `deploy_and_verify.py` instead

### 4. `deploy_database_advanced.py`
- **Purpose:** Advanced deployment with PostgreSQL direct connection
- **Requirements:** `psycopg2-binary` package
- **Note:** Requires additional setup for direct DB access

## Connection Details

```
Project URL: https://dijdhqrxqwbctywejydj.supabase.co
Service Key: sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1
Admin User: 306145881 (@admin)
```

## Verification Checklist

After deployment, the script will verify:

- [ ] Tables exist (`users`, `activity_log`)
- [ ] Indexes are created
- [ ] RLS policies are enabled
- [ ] Admin user is whitelisted
- [ ] CRUD operations work
- [ ] Activity logging works
- [ ] Triggers fire correctly

## Troubleshooting

### Tables Not Found
- Make sure you ran the SQL in Supabase Dashboard
- Check for any errors in the SQL Editor output
- Verify you're connected to the right project

### Authentication Failed
- Verify the service key is correct
- Check if the key starts with `sb_secret_`
- Ensure you're using the service key, not the anon key

### Cannot Insert/Update
- Check if RLS policies are blocking operations
- Verify the service key has proper permissions
- Look for constraint violations in error messages

## Next Steps

After successful deployment:

1. **Update .env file** with your Telegram bot token
2. **Run the bot** to test functionality
3. **Monitor activity_log** table for events
4. **Test subscription flows** with test users

## Database Schema Overview

### Users Table
- Stores subscription information
- Tracks payment methods (card/stars/whitelisted)
- Maintains subscription status and expiry dates

### Activity Log Table
- Records all user actions
- Tracks subscription changes
- Provides audit trail

### Key Features
- Automatic timestamp updates
- Activity logging via triggers
- Row Level Security for data protection
- Helper functions for subscription management
- Performance-optimized indexes

## Support

For issues or questions:
1. Check the SQL Editor output for errors
2. Review the verification script output
3. Ensure all credentials are correct
4. Verify network connectivity to Supabase
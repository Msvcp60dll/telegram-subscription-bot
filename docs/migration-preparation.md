# Migration Preparation Guide

## Overview
This guide covers the complete preparation process for migrating 1100 existing Telegram group members to whitelisted status in your Supabase database.

## Pre-Migration Checklist

### 1. Environment Setup
- [ ] Verify Supabase database is operational
- [ ] Confirm Railway deployment is ready
- [ ] Test database connectivity from local environment
- [ ] Ensure sufficient database capacity for 1100+ users
- [ ] Check rate limits on Supabase (default: 300 requests/minute)

### 2. Backup Requirements
- [ ] Create full database backup in Supabase dashboard
- [ ] Export current whitelisted users (if any)
- [ ] Document current database statistics
- [ ] Save backup credentials securely
- [ ] Test backup restoration process (on staging if available)

### 3. Data Collection

#### Option A: Export from Telegram Desktop
1. Open Telegram Desktop
2. Go to your group (-1002384609773)
3. Click on group info → Members
4. Export member list:
   - Click "..." menu → Export Members
   - Choose JSON format if available
   - Save as `telegram_members_export.json`

#### Option B: Manual Export via Bot (Limited)
```bash
# This will only get administrators
python scripts/migrate_existing_members.py --source group --dry-run
```

#### Option C: Use Telegram Client API
```python
# Using Telethon (requires phone authentication)
from telethon import TelegramClient

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'
group_id = -1002384609773

async def export_members():
    client = TelegramClient('session', api_id, api_hash)
    await client.start()
    
    participants = await client.get_participants(group_id)
    members = []
    
    for user in participants:
        members.append({
            'telegram_id': user.id,
            'username': user.username,
            'full_name': f"{user.first_name} {user.last_name}".strip()
        })
    
    with open('members_export.json', 'w') as f:
        json.dump(members, f, indent=2)
```

### 4. Data Preparation
```bash
# Convert exported data to migration format
python scripts/convert_member_list.py telegram_members_export.json -o members_for_migration.json

# Validate the data
python scripts/convert_member_list.py members_for_migration.json --validate
```

### 5. Environment Variables
Ensure these are set in your production environment:
```bash
export SUPABASE_URL="https://dijdhqrxqwbctywejydj.supabase.co"
export SUPABASE_SERVICE_KEY="your_service_role_key"
export BOT_TOKEN="your_bot_token"
export GROUP_ID="-1002384609773"
export ENVIRONMENT="production"
```

## Timing Recommendations

### Best Time to Migrate
- **Recommended**: During low activity hours (2-6 AM local time)
- **Avoid**: Peak usage hours (6-10 PM)
- **Duration**: Expect ~20-30 minutes for 1100 users

### Performance Expectations
- Batch size: 100 users
- Processing rate: ~50-100 users/minute
- Total time: 15-25 minutes
- Database load: Moderate (well within Supabase limits)

## Pre-Migration Testing

### 1. Dry Run Test
```bash
# Test with sample data first
python scripts/production_migration.py --file sample_users.json --dry-run

# Full dry run with actual data
python scripts/production_migration.py --file members_for_migration.json --dry-run
```

### 2. Small Batch Test
```bash
# Create test file with 10 users
head -n 10 members_for_migration.json > test_batch.json

# Run actual migration on test batch
python scripts/production_migration.py --file test_batch.json

# Verify results
python scripts/verify_migration.py --file test_batch.json
```

## Migration Execution Steps

### 1. Final Preparation
```bash
# Create working directory
mkdir -p migration_$(date +%Y%m%d)
cd migration_$(date +%Y%m%d)

# Copy necessary files
cp ../members_for_migration.json .
cp ../scripts/production_migration.py .
```

### 2. Start Migration
```bash
# Production migration with safety checks
python production_migration.py --file members_for_migration.json

# System will prompt for confirmation
# Type 'PROCEED' to continue
```

### 3. Monitor Progress
```bash
# In another terminal, monitor logs
tail -f production_migration.log

# Check database statistics
python scripts/migration_monitor.py
```

## Rollback Plan

### Automatic Rollback
The migration script creates automatic backups before starting. If migration fails:

1. Locate backup file in `migration_backups/` directory
2. Note the migration ID from logs
3. Contact system administrator with backup file path

### Manual Rollback Steps
```sql
-- If needed, remove all whitelisted users added during migration
-- Run in Supabase SQL editor

-- First, verify the migration timestamp
SELECT COUNT(*) 
FROM users 
WHERE subscription_status = 'whitelisted'
AND created_at > 'MIGRATION_START_TIME';

-- Create backup of current state
CREATE TABLE users_backup_YYYYMMDD AS 
SELECT * FROM users;

-- Restore specific users from backup
UPDATE users 
SET subscription_status = 'expired',
    payment_method = NULL
WHERE telegram_id IN (
    SELECT telegram_id 
    FROM activity_log 
    WHERE action = 'user_whitelisted'
    AND details->>'migration_id' = 'YOUR_MIGRATION_ID'
);
```

### Recovery Procedures

#### If Migration Partially Completes
```bash
# Resume from checkpoint
python production_migration.py --resume migration_20240101_120000

# Verify which users were processed
python scripts/verify_migration.py --checkpoint migration_20240101_120000
```

#### If Database Connection Fails
1. Check Supabase service status
2. Verify network connectivity
3. Confirm credentials are correct
4. Wait 5 minutes and retry
5. Use checkpoint to resume

## Post-Migration Verification

### 1. Immediate Checks
```bash
# Run verification script
python scripts/verify_migration.py --file members_for_migration.json

# Check migration report
cat migration_reports/migration_*_report.json | python -m json.tool
```

### 2. Database Verification
```sql
-- Check total whitelisted users
SELECT COUNT(*) FROM users WHERE subscription_status = 'whitelisted';

-- Verify recent additions
SELECT COUNT(*) 
FROM activity_log 
WHERE action = 'user_whitelisted' 
AND timestamp > NOW() - INTERVAL '1 hour';

-- Sample check of whitelisted users
SELECT telegram_id, username, subscription_status, created_at
FROM users 
WHERE subscription_status = 'whitelisted'
ORDER BY created_at DESC
LIMIT 10;
```

### 3. Bot Verification
1. Have a whitelisted user try to access the group
2. Verify bot recognizes their status
3. Check bot logs for any errors
4. Test with multiple users from different batches

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Rate Limiting
**Symptom**: "Too many requests" errors
**Solution**: 
- Reduce batch size in script
- Increase delay between operations
- Wait 5 minutes and resume from checkpoint

#### Issue: Duplicate Users
**Symptom**: "Unique constraint violation" errors
**Solution**:
- Script handles duplicates automatically
- Check logs for duplicate user IDs
- These are safely skipped

#### Issue: Memory Issues
**Symptom**: Script crashes with large file
**Solution**:
- Split input file into smaller chunks
- Process in multiple runs
- Use system with more RAM

#### Issue: Network Timeout
**Symptom**: Connection errors during migration
**Solution**:
- Check internet stability
- Verify Supabase is accessible
- Resume from checkpoint after connection restored

## Support and Monitoring

### During Migration
- Keep migration terminal open
- Monitor logs in real-time
- Have database dashboard open
- Be ready to pause if needed (Ctrl+C)

### After Migration
- Save all log files
- Archive backup files
- Document any issues encountered
- Update this guide with learnings

## Contact Information

For emergencies during migration:
- Supabase Support: support.supabase.com
- Database Admin: [Your contact]
- Bot Developer: [Your contact]
- Telegram Group Admin: [Your contact]

## Success Criteria

Migration is considered successful when:
1. ✅ All 1100 users are in database
2. ✅ All users have status 'whitelisted'
3. ✅ No data loss occurred
4. ✅ Bot recognizes whitelisted users
5. ✅ Verification script passes all checks
6. ✅ Group access works for migrated users
7. ✅ Activity logs show migration events
8. ✅ Backup file is safely stored

## Next Steps After Migration

1. Monitor bot performance for 24 hours
2. Check for any user complaints
3. Review migration logs for optimization opportunities
4. Update documentation with actual metrics
5. Schedule follow-up verification in 1 week
6. Archive migration data after 30 days
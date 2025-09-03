# Migration Guide - Whitelisting Existing Group Members

This guide explains how to migrate your existing 1100 Telegram group members to whitelist status, giving them permanent free access to your subscription bot.

## Overview

The migration system provides:
- Bulk whitelisting of existing group members
- Progress tracking and resume capability
- Data validation and deduplication
- Automatic backup before migration
- Detailed logging and error reporting
- Multiple migration methods (API, file import)

## Prerequisites

1. **Bot Admin Access**: The bot must be an administrator in your Telegram group
2. **Database Access**: Supabase credentials must be configured
3. **Member Data**: Either bot API access or a JSON file with member IDs

## Migration Methods

### Method 1: Using Bot Commands (Recommended)

#### Step 1: Export Group Members
Since Telegram Bot API can only fetch administrators directly, you need to export your member list:

**Option A: Telegram Desktop Export**
1. Open Telegram Desktop
2. Go to your group settings
3. Click on members list
4. Export as JSON/CSV
5. Convert to our format (see below)

**Option B: Use Telegram Client API**
Use tools like Telethon or Pyrogram with your phone number to fetch all members.

#### Step 2: Prepare Member Data
Create a JSON file with one of these formats:

**Full Format:**
```json
[
  {
    "telegram_id": 123456789,
    "username": "john_doe",
    "full_name": "John Doe"
  },
  ...
]
```

**Simple ID List:**
```json
[123456789, 987654321, 555555555, ...]
```

#### Step 3: Run Migration via Bot

1. **Start the bot**:
   ```bash
   python main.py
   ```

2. **Use admin commands**:
   - `/migrate` - Open migration panel
   - Choose "📁 Import from File"
   - Send your JSON file
   - Wait for completion

### Method 2: Using CLI Script

Run the migration script directly:

```bash
cd scripts

# Dry run first (no changes made)
python migrate_existing_members.py --dry-run --source file --file ../members.json

# Actual migration
python migrate_existing_members.py --source file --file ../members.json

# Verify migration
python migrate_existing_members.py --verify-only
```

### Method 3: Via Admin Panel in Bot

1. Send `/migrate` to the bot
2. Choose migration source:
   - **Start Migration**: Fetch from group (admins only)
   - **Import from File**: Upload JSON file with all members

## Migration Process

### Phase 1: Pre-Migration
- Creates backup of existing whitelist
- Validates member data
- Checks for duplicates
- Creates checkpoint file

### Phase 2: Migration
- Processes users in batches of 100
- Updates database with whitelist status
- Logs all activities
- Saves progress every 10 users

### Phase 3: Post-Migration
- Generates migration report
- Verifies data integrity
- Provides success statistics

## Safety Features

### 1. Automatic Backup
Before migration starts, a backup is created:
- File: `migration_backup_YYYYMMDD_HHMMSS.json`
- Contains all existing whitelisted users

### 2. Resume Capability
If migration is interrupted:
- Progress is saved in `migration_checkpoint.json`
- Next run will resume from last position
- No duplicate processing

### 3. Dry Run Mode
Test the migration without making changes:
```bash
python migrate_existing_members.py --dry-run
```

### 4. Rollback Support
While automatic rollback isn't implemented, you can:
1. Use the backup file to identify changes
2. Manually restore if needed
3. Contact support for assistance

## Monitoring Progress

### Via Bot Commands
- `/migrate_status` - Quick status check
- `/migrate_verify` - Verify completion
- Migration panel shows real-time progress

### Via Log Files
- `migration.log` - Detailed migration logs
- `bot.log` - General bot operations

### Progress Indicators
- Progress percentage
- Success/Failed counts
- Estimated time remaining
- Batch processing status

## Verification

After migration, verify success:

1. **Check Statistics**:
   ```
   /migrate_verify
   ```
   Expected output:
   - Whitelisted Users: ~1100
   - All users have "whitelisted" status

2. **Test User Access**:
   - Whitelisted users can access group
   - No subscription prompts for them
   - Activity logs show whitelist status

3. **Database Verification**:
   Check Supabase dashboard:
   - Users table has ~1100 entries
   - subscription_status = "whitelisted"
   - payment_method = "whitelisted"

## Troubleshooting

### Common Issues

1. **"Bot API can only fetch administrators"**
   - Solution: Use file import method
   - Export members from Telegram Desktop

2. **"Migration stuck/frozen"**
   - Check `migration.log` for errors
   - Restart with resume capability
   - Use `/migrate_status` to check progress

3. **"Some users failed to migrate"**
   - Check failed users in report
   - Retry with just failed users
   - May be deleted accounts

4. **"Database connection errors"**
   - Verify Supabase credentials
   - Check internet connection
   - Review rate limits

### Error Recovery

If migration fails:

1. **Check checkpoint**:
   ```bash
   cat migration_checkpoint.json
   ```

2. **Resume migration**:
   - Just run migration again
   - Will continue from checkpoint

3. **Reset if needed**:
   ```bash
   # Reset checkpoint
   rm migration_checkpoint.json
   
   # Or via bot
   /migrate → Reset Checkpoint
   ```

## Best Practices

1. **Timing**:
   - Run during low activity hours
   - Inform users beforehand
   - Allow 10-15 minutes for 1100 users

2. **Preparation**:
   - Export member list first
   - Validate JSON format
   - Run dry-run test
   - Back up database

3. **Monitoring**:
   - Watch progress in real-time
   - Check logs for errors
   - Verify random samples
   - Test user access after

4. **Post-Migration**:
   - Keep backup for 30 days
   - Monitor user access
   - Check activity logs
   - Document completion

## File Formats

### Input Format Examples

**From Telegram Export**:
```json
[
  {"id": 123456789, "username": "user1", "first_name": "John", "last_name": "Doe"},
  {"id": 987654321, "username": "user2", "first_name": "Jane", "last_name": "Smith"}
]
```

**Convert to Migration Format**:
```python
import json

# Read Telegram export
with open('telegram_export.json', 'r') as f:
    telegram_data = json.load(f)

# Convert to our format
members = []
for user in telegram_data:
    members.append({
        'telegram_id': user['id'],
        'username': user.get('username'),
        'full_name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    })

# Save for migration
with open('members_for_migration.json', 'w') as f:
    json.dump(members, f, indent=2)
```

### Output Reports

Migration creates these files:
- `migration_report_YYYYMMDD_HHMMSS.json` - Full report
- `migration_checkpoint.json` - Progress tracking
- `migration_backup_YYYYMMDD_HHMMSS.json` - Data backup

## Support

If you encounter issues:

1. Check this guide first
2. Review log files
3. Try dry-run mode
4. Contact admin support

## Important Notes

⚠️ **Warning**: This migration grants permanent free access to all whitelisted users. Make sure this is intended.

✅ **Recommendation**: Always run a dry-run first to verify the process.

🔄 **Automation**: After initial migration, new members should be handled through normal bot workflows, not bulk migration.
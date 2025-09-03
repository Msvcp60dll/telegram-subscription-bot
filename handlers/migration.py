"""
Migration Handlers Module
Provides admin commands for managing bulk user migrations and whitelist operations
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

from aiogram import Router, Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

# Import database and services
from database.supabase_client import SupabaseClient, ActivityAction
from scripts.migrate_existing_members import (
    GroupMemberMigration, MemberData, MigrationTracker,
    CHECKPOINT_FILE, BATCH_SIZE
)

logger = logging.getLogger(__name__)

# Create router for migration handlers
router = Router(name="migration")

# Migration states
class MigrationStates(StatesGroup):
    confirming_migration = State()
    migration_running = State()
    importing_file = State()
    
# Migration status tracking
migration_status = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'success': 0,
    'failed': 0,
    'start_time': None,
    'current_batch': 0,
    'total_batches': 0
}

# Configuration (imported from main)
GROUP_ID = int("-1002384609773")
ADMIN_USER_ID = int("306145881")

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID

def get_migration_keyboard() -> InlineKeyboardMarkup:
    """Get migration control keyboard"""
    builder = InlineKeyboardBuilder()
    
    if not migration_status['is_running']:
        builder.button(text="🚀 Start Migration", callback_data="migrate_start")
        builder.button(text="📁 Import from File", callback_data="migrate_import")
        builder.button(text="🔍 Check Status", callback_data="migrate_status")
        builder.button(text="✅ Verify Migration", callback_data="migrate_verify")
        builder.button(text="📊 View Report", callback_data="migrate_report")
        builder.button(text="🔄 Reset Checkpoint", callback_data="migrate_reset")
    else:
        builder.button(text="⏸ Pause Migration", callback_data="migrate_pause")
        builder.button(text="📊 Current Progress", callback_data="migrate_progress")
    
    builder.button(text="❌ Close", callback_data="migrate_close")
    builder.adjust(2)
    return builder.as_markup()

@router.message(F.text == "/migrate")
async def migrate_command(message: Message):
    """Start migration process via command"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return
    
    text = """
<b>🔄 Group Member Migration Tool</b>

This tool will migrate existing group members to whitelist status, giving them permanent free access.

<b>Current Configuration:</b>
• Group ID: <code>{}</code>
• Batch Size: {} users
• Processing Mode: Sequential

<b>Important:</b>
• This process will whitelist ALL current group members
• Members will have permanent free access
• The process can be resumed if interrupted
• A backup will be created before migration

Choose an action:
""".format(GROUP_ID, BATCH_SIZE)
    
    await message.answer(text, reply_markup=get_migration_keyboard())

@router.callback_query(lambda c: c.data == "migrate_start")
async def start_migration_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Start the migration process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    if migration_status['is_running']:
        await callback.answer("Migration already in progress!", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(MigrationStates.confirming_migration)
    
    # Check for existing checkpoint
    checkpoint_exists = Path(CHECKPOINT_FILE).exists()
    
    text = """
<b>⚠️ Confirm Migration</b>

{}

You are about to start the migration process.

<b>This will:</b>
• Fetch all current group members
• Add them to the whitelist database
• Grant permanent free access
• Create activity logs

<b>Note:</b> Bot API can only fetch administrators directly.
For all 1100 members, you should use "Import from File" instead.

Do you want to proceed?
""".format(
        "📌 <b>Checkpoint found!</b> Migration will resume from last position.\n" 
        if checkpoint_exists else ""
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Confirm & Start", callback_data="migrate_confirm")
    builder.button(text="❌ Cancel", callback_data="migrate_cancel")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data == "migrate_confirm")
async def confirm_migration(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Confirm and start migration"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Starting migration...")
    await state.set_state(MigrationStates.migration_running)
    
    # Update status
    migration_status['is_running'] = True
    migration_status['start_time'] = datetime.now()
    migration_status['progress'] = 0
    migration_status['success'] = 0
    migration_status['failed'] = 0
    
    # Initialize database client
    from database.supabase_client import create_client_from_env
    db_client = create_client_from_env()
    
    # Create migration instance
    migration = GroupMemberMigration(
        bot_token=bot.token,
        group_id=GROUP_ID,
        db_client=db_client,
        dry_run=False
    )
    
    # Start migration in background
    asyncio.create_task(run_migration_async(migration, callback, bot, state))
    
    text = """
<b>🚀 Migration Started!</b>

The migration process is now running in the background.

<b>Status:</b> Initializing...

Use the buttons below to monitor progress.
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_migration_keyboard())
    except TelegramBadRequest:
        pass

async def run_migration_async(migration: GroupMemberMigration, callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Run migration in background"""
    try:
        # Send progress updates periodically
        async def progress_callback(current: int, total: int, message: str):
            migration_status['progress'] = current
            migration_status['total'] = total
            
            # Update message every 10%
            if current % max(1, total // 10) == 0:
                progress_text = f"""
<b>🔄 Migration in Progress</b>

<b>Progress:</b> {current}/{total} ({current/total*100:.1f}%)
<b>Status:</b> {message}
<b>Success:</b> {migration_status['success']}
<b>Failed:</b> {migration_status['failed']}

⏱ Elapsed: {(datetime.now() - migration_status['start_time']).seconds}s
"""
                try:
                    await callback.message.edit_text(progress_text, reply_markup=get_migration_keyboard())
                except:
                    pass
        
        # Run migration
        result = await migration.run_migration(source='group')
        
        # Update final status
        migration_status['is_running'] = False
        migration_status['success'] = result.get('successfully_whitelisted', 0)
        migration_status['failed'] = result.get('failed', 0)
        
        # Send completion message
        completion_text = f"""
<b>✅ Migration Complete!</b>

<b>Results:</b>
• Total Processed: {result.get('total_members', 0)}
• Successfully Whitelisted: {result.get('successfully_whitelisted', 0)}
• Failed: {result.get('failed', 0)}
• Skipped: {result.get('skipped', 0)}

<b>Time Taken:</b> {(datetime.now() - migration_status['start_time']).seconds}s

{'<b>Backup saved to:</b> ' + result.get('backup_file', 'N/A') if result.get('backup_file') else ''}

Migration completed successfully!
"""
        
        await callback.message.edit_text(completion_text, reply_markup=get_migration_keyboard())
        
        # Send notification to admin
        await bot.send_message(
            ADMIN_USER_ID,
            f"✅ Migration completed!\n\n"
            f"Whitelisted: {result.get('successfully_whitelisted', 0)} users\n"
            f"Failed: {result.get('failed', 0)} users"
        )
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        migration_status['is_running'] = False
        
        error_text = f"""
<b>❌ Migration Failed!</b>

<b>Error:</b> {str(e)}

<b>Progress before failure:</b>
• Processed: {migration_status['progress']}
• Success: {migration_status['success']}
• Failed: {migration_status['failed']}

The migration checkpoint has been saved. You can resume from where it stopped.
"""
        
        await callback.message.edit_text(error_text, reply_markup=get_migration_keyboard())
    
    finally:
        await state.clear()

@router.callback_query(lambda c: c.data == "migrate_import")
async def import_from_file_handler(callback: CallbackQuery, state: FSMContext):
    """Import members from file"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(MigrationStates.importing_file)
    
    text = """
<b>📁 Import Members from File</b>

Send me a JSON file containing member data.

<b>Supported formats:</b>

<b>Format 1 - Full data:</b>
<code>[
  {
    "telegram_id": 123456789,
    "username": "user1",
    "full_name": "John Doe"
  },
  ...
]</code>

<b>Format 2 - ID list:</b>
<code>[123456789, 987654321, ...]</code>

<b>Format 3 - Simple objects:</b>
<code>[
  {"id": 123456789},
  {"user_id": 987654321},
  ...
]</code>

Send the file or /cancel to cancel.
"""
    
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

@router.message(MigrationStates.importing_file)
async def process_import_file(message: Message, state: FSMContext, bot: Bot):
    """Process imported file"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Import cancelled.", reply_markup=get_migration_keyboard())
        return
    
    if not message.document:
        await message.answer("Please send a JSON file.")
        return
    
    try:
        # Download file
        file = await bot.get_file(message.document.file_id)
        file_path = f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        await bot.download_file(file.file_path, file_path)
        
        await message.answer("📥 File received. Starting import...")
        
        # Initialize database client
        from database.supabase_client import create_client_from_env
        db_client = create_client_from_env()
        
        # Create migration instance
        migration = GroupMemberMigration(
            bot_token=bot.token,
            group_id=GROUP_ID,
            db_client=db_client,
            dry_run=False
        )
        
        # Run migration from file
        result = await migration.run_migration(source='file', file_path=file_path)
        
        # Clean up file
        Path(file_path).unlink(missing_ok=True)
        
        await state.clear()
        
        success_text = f"""
<b>✅ Import Complete!</b>

<b>Results:</b>
• Total Members: {result.get('total_members', 0)}
• Successfully Whitelisted: {result.get('successfully_whitelisted', 0)}
• Failed: {result.get('failed', 0)}
• Skipped: {result.get('skipped', 0)}
• Duplicates: {result.get('duplicates_found', 0)}

All members have been processed!
"""
        
        await message.answer(success_text, reply_markup=get_migration_keyboard())
        
    except Exception as e:
        logger.error(f"Import failed: {e}")
        await state.clear()
        await message.answer(
            f"❌ Import failed: {str(e)}",
            reply_markup=get_migration_keyboard()
        )

@router.callback_query(lambda c: c.data == "migrate_status")
async def check_migration_status(callback: CallbackQuery):
    """Check current migration status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    # Load checkpoint to get current status
    tracker = MigrationTracker()
    summary = tracker.get_summary()
    
    text = f"""
<b>📊 Migration Status</b>

<b>Overall Status:</b> {summary.get('status', 'Unknown')}

<b>Progress:</b>
• Total Members: {summary.get('total_count', 0)}
• Processed: {summary.get('processed_count', 0)}
• Failed: {summary.get('failed_count', 0)}
• Success Rate: {summary.get('success_rate', 0):.1f}%

<b>Started:</b> {summary.get('start_time', 'N/A')}

<b>Current Status:</b> {'🟢 Running' if migration_status['is_running'] else '⭕ Not running'}
"""
    
    if summary.get('failed_count', 0) > 0 and tracker.state.get('failed_users'):
        text += "\n\n<b>Failed Users (last 5):</b>\n"
        for failed in tracker.state['failed_users'][-5:]:
            text += f"• {failed['telegram_id']}: {failed['error']}\n"
    
    try:
        await callback.message.edit_text(text, reply_markup=get_migration_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=get_migration_keyboard())

@router.callback_query(lambda c: c.data == "migrate_verify")
async def verify_migration(callback: CallbackQuery):
    """Verify migration results"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Verifying migration...")
    
    try:
        # Initialize database client
        from database.supabase_client import create_client_from_env
        db_client = create_client_from_env()
        
        # Get statistics
        stats = db_client.get_subscription_stats()
        
        # Check group member count (this requires proper permissions)
        bot = callback.bot
        try:
            chat = await bot.get_chat(GROUP_ID)
            group_member_count = await bot.get_chat_member_count(GROUP_ID)
        except:
            group_member_count = "Unable to fetch"
        
        text = f"""
<b>✅ Migration Verification</b>

<b>Database Statistics:</b>
• Total Users: {stats.get('total_users', 0)}
• Whitelisted Users: {stats.get('whitelisted_users', 0)}
• Active Subscriptions: {stats.get('active_subscriptions', 0)}
• Expired Subscriptions: {stats.get('expired_subscriptions', 0)}

<b>Group Information:</b>
• Group Members: {group_member_count}
• Expected Whitelist: ~1100

<b>Verification Result:</b>
"""
        
        if stats.get('whitelisted_users', 0) >= 1000:
            text += "✅ Migration appears successful!"
        elif stats.get('whitelisted_users', 0) > 0:
            text += f"⚠️ Partial migration: {stats.get('whitelisted_users', 0)} users whitelisted"
        else:
            text += "❌ No whitelisted users found"
        
        await callback.message.edit_text(text, reply_markup=get_migration_keyboard())
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        await callback.message.edit_text(
            f"❌ Verification failed: {str(e)}",
            reply_markup=get_migration_keyboard()
        )

@router.callback_query(lambda c: c.data == "migrate_report")
async def view_migration_report(callback: CallbackQuery):
    """View or download migration report"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    # Find latest report file
    report_files = list(Path('.').glob('migration_report_*.json'))
    
    if not report_files:
        await callback.message.answer("No migration reports found.")
        return
    
    latest_report = max(report_files, key=lambda p: p.stat().st_mtime)
    
    try:
        with open(latest_report, 'r') as f:
            report = json.load(f)
        
        text = f"""
<b>📊 Migration Report</b>

<b>File:</b> {latest_report.name}

<b>Summary:</b>
• Status: {report.get('status', 'Unknown')}
• Total Members: {report.get('total_members', 0)}
• Whitelisted: {report.get('successfully_whitelisted', 0)}
• Failed: {report.get('failed', 0)}
• Skipped: {report.get('skipped', 0)}

<b>Mode:</b> {'Dry Run' if report.get('dry_run') else 'Production'}

Sending full report as file...
"""
        
        await callback.message.edit_text(text)
        
        # Send report file
        report_file = FSInputFile(latest_report)
        await callback.message.answer_document(
            report_file,
            caption="📊 Full Migration Report"
        )
        
    except Exception as e:
        logger.error(f"Failed to read report: {e}")
        await callback.message.edit_text(
            f"❌ Failed to read report: {str(e)}",
            reply_markup=get_migration_keyboard()
        )

@router.callback_query(lambda c: c.data == "migrate_reset")
async def reset_checkpoint(callback: CallbackQuery):
    """Reset migration checkpoint"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    checkpoint_file = Path(CHECKPOINT_FILE)
    
    if checkpoint_file.exists():
        checkpoint_file.unlink()
        await callback.answer("✅ Checkpoint reset successfully!", show_alert=True)
        
        text = """
<b>✅ Checkpoint Reset</b>

Migration checkpoint has been cleared.
Next migration will start from the beginning.
"""
    else:
        await callback.answer("No checkpoint found", show_alert=True)
        text = """
<b>ℹ️ No Checkpoint</b>

No migration checkpoint exists.
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_migration_keyboard())
    except TelegramBadRequest:
        pass

@router.callback_query(lambda c: c.data == "migrate_close")
async def close_migration_panel(callback: CallbackQuery, state: FSMContext):
    """Close migration panel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await state.clear()
    await callback.message.delete()

@router.callback_query(lambda c: c.data == "migrate_cancel")
async def cancel_migration(callback: CallbackQuery, state: FSMContext):
    """Cancel migration confirmation"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Migration cancelled")
    await state.clear()
    
    text = """
<b>Migration cancelled.</b>

Use the menu below to start again or perform other actions.
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_migration_keyboard())
    except TelegramBadRequest:
        pass

# Additional commands

@router.message(F.text == "/migrate_status")
async def migrate_status_command(message: Message):
    """Quick status check command"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return
    
    tracker = MigrationTracker()
    summary = tracker.get_summary()
    
    text = f"""
<b>Migration Status</b>

Status: {summary.get('status', 'Unknown')}
Progress: {summary.get('processed_count', 0)}/{summary.get('total_count', 0)}
Success Rate: {summary.get('success_rate', 0):.1f}%
"""
    
    await message.answer(text)

@router.message(F.text == "/migrate_verify")
async def migrate_verify_command(message: Message):
    """Quick verification command"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return
    
    try:
        from database.supabase_client import create_client_from_env
        db_client = create_client_from_env()
        stats = db_client.get_subscription_stats()
        
        text = f"""
<b>Quick Verification</b>

Whitelisted Users: {stats.get('whitelisted_users', 0)}
Total Users: {stats.get('total_users', 0)}
Active Subs: {stats.get('active_subscriptions', 0)}

Status: {'✅ OK' if stats.get('whitelisted_users', 0) > 0 else '❌ No whitelist'}
"""
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Verification failed: {str(e)}")
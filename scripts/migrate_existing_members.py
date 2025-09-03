"""
Migration Script for Existing Telegram Group Members
Fetches all current group members and whitelists them in the database
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import argparse
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot
from aiogram.types import ChatMember
from aiogram.enums import ChatMemberStatus
from database.supabase_client import SupabaseClient, ActivityAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o")
GROUP_ID = int(os.getenv("GROUP_ID", "-1002384609773"))
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dijdhqrxqwbctywejydj.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1")

# Migration configuration
BATCH_SIZE = 100  # Process users in batches
RATE_LIMIT_DELAY = 0.1  # Delay between API calls (seconds)
CHECKPOINT_FILE = "migration_checkpoint.json"
BACKUP_FILE = "migration_backup_{timestamp}.json"

@dataclass
class MemberData:
    """Data structure for group member"""
    telegram_id: int
    username: Optional[str]
    full_name: Optional[str]
    status: str
    join_date: Optional[datetime]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'full_name': self.full_name,
            'status': self.status,
            'join_date': self.join_date.isoformat() if self.join_date else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemberData':
        """Create from dictionary"""
        return cls(
            telegram_id=data['telegram_id'],
            username=data.get('username'),
            full_name=data.get('full_name'),
            status=data['status'],
            join_date=datetime.fromisoformat(data['join_date']) if data.get('join_date') else None
        )

class MigrationTracker:
    """Tracks migration progress and enables resume capability"""
    
    def __init__(self, checkpoint_file: str = CHECKPOINT_FILE):
        self.checkpoint_file = checkpoint_file
        self.state = self.load_checkpoint()
    
    def load_checkpoint(self) -> Dict:
        """Load checkpoint from file if exists"""
        if Path(self.checkpoint_file).exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                    logger.info(f"Loaded checkpoint: {data.get('processed_count', 0)} users processed")
                    return data
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
        return {
            'processed_users': [],
            'failed_users': [],
            'processed_count': 0,
            'total_count': 0,
            'start_time': datetime.now().isoformat(),
            'status': 'pending'
        }
    
    def save_checkpoint(self):
        """Save current state to checkpoint file"""
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug("Checkpoint saved")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def mark_processed(self, telegram_id: int):
        """Mark user as processed"""
        self.state['processed_users'].append(telegram_id)
        self.state['processed_count'] = len(self.state['processed_users'])
        
        # Save checkpoint every 10 users
        if self.state['processed_count'] % 10 == 0:
            self.save_checkpoint()
    
    def mark_failed(self, telegram_id: int, error: str):
        """Mark user as failed"""
        self.state['failed_users'].append({
            'telegram_id': telegram_id,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        })
    
    def is_processed(self, telegram_id: int) -> bool:
        """Check if user is already processed"""
        return telegram_id in self.state['processed_users']
    
    def get_summary(self) -> Dict:
        """Get migration summary"""
        return {
            'total_count': self.state['total_count'],
            'processed_count': self.state['processed_count'],
            'failed_count': len(self.state['failed_users']),
            'success_rate': (self.state['processed_count'] / self.state['total_count'] * 100) 
                          if self.state['total_count'] > 0 else 0,
            'start_time': self.state['start_time'],
            'status': self.state['status']
        }

class GroupMemberMigration:
    """Main migration class for whitelisting group members"""
    
    def __init__(self, bot_token: str, group_id: int, db_client: SupabaseClient, dry_run: bool = False):
        self.bot = Bot(token=bot_token)
        self.group_id = group_id
        self.db_client = db_client
        self.dry_run = dry_run
        self.tracker = MigrationTracker()
        self.members_data: List[MemberData] = []
    
    async def fetch_group_members(self) -> List[MemberData]:
        """Fetch all members from the Telegram group"""
        logger.info(f"Fetching members from group {self.group_id}")
        members = []
        
        try:
            # Get chat information first
            chat = await self.bot.get_chat(self.group_id)
            logger.info(f"Group: {chat.title} (Type: {chat.type})")
            
            # Note: get_chat_administrators only returns admins
            # For regular members, we need to use different approach
            # Telegram Bot API doesn't provide a way to get all members directly
            # We'll get administrators first
            admins = await self.bot.get_chat_administrators(self.group_id)
            
            for admin in admins:
                member = admin.user
                members.append(MemberData(
                    telegram_id=member.id,
                    username=member.username,
                    full_name=member.full_name,
                    status='admin',
                    join_date=None
                ))
                await asyncio.sleep(RATE_LIMIT_DELAY)
            
            logger.info(f"Fetched {len(members)} administrators from the group")
            
            # Important note: Regular members cannot be fetched via Bot API
            # You'll need to either:
            # 1. Use Telegram Client API (requires phone number authentication)
            # 2. Track members as they interact with the bot
            # 3. Import from existing data source
            
            logger.warning(
                "Note: Bot API can only fetch administrators. "
                "For all 1100 members, you need to:\n"
                "1. Export member list from Telegram desktop app\n"
                "2. Use Telegram Client API (telethon/pyrogram)\n"
                "3. Import from existing database/file"
            )
            
            return members
            
        except Exception as e:
            logger.error(f"Failed to fetch group members: {e}")
            raise
    
    async def fetch_members_from_file(self, file_path: str) -> List[MemberData]:
        """Load members from a JSON file (for bulk import)"""
        logger.info(f"Loading members from file: {file_path}")
        members = []
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            for item in data:
                # Handle different file formats
                if isinstance(item, dict):
                    telegram_id = item.get('telegram_id') or item.get('id') or item.get('user_id')
                    username = item.get('username')
                    full_name = item.get('full_name') or item.get('name')
                else:
                    # Simple list of IDs
                    telegram_id = int(item)
                    username = None
                    full_name = None
                
                if telegram_id:
                    members.append(MemberData(
                        telegram_id=int(telegram_id),
                        username=username,
                        full_name=full_name,
                        status='member',
                        join_date=None
                    ))
            
            logger.info(f"Loaded {len(members)} members from file")
            return members
            
        except Exception as e:
            logger.error(f"Failed to load members from file: {e}")
            raise
    
    def validate_members(self, members: List[MemberData]) -> Tuple[List[MemberData], List[Dict]]:
        """Validate and deduplicate members"""
        logger.info("Validating members...")
        
        seen_ids = set()
        valid_members = []
        duplicates = []
        
        for member in members:
            if member.telegram_id in seen_ids:
                duplicates.append(member.to_dict())
            else:
                seen_ids.add(member.telegram_id)
                valid_members.append(member)
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} duplicate members")
        
        logger.info(f"Validated {len(valid_members)} unique members")
        return valid_members, duplicates
    
    async def whitelist_batch(self, batch: List[MemberData]) -> Dict[str, int]:
        """Whitelist a batch of users"""
        results = {'success': 0, 'failed': 0, 'skipped': 0}
        
        for member in batch:
            # Skip if already processed
            if self.tracker.is_processed(member.telegram_id):
                results['skipped'] += 1
                continue
            
            try:
                if not self.dry_run:
                    # Add to whitelist in database
                    success = self.db_client.whitelist_user(
                        telegram_id=member.telegram_id,
                        username=member.username
                    )
                    
                    if success:
                        # Log activity
                        self.db_client.log_activity(
                            telegram_id=member.telegram_id,
                            action=ActivityAction.USER_WHITELISTED.value,
                            details={
                                'migration': True,
                                'source': 'bulk_migration',
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                        results['success'] += 1
                        self.tracker.mark_processed(member.telegram_id)
                    else:
                        results['failed'] += 1
                        self.tracker.mark_failed(member.telegram_id, "Database operation failed")
                else:
                    # Dry run - just mark as would be processed
                    results['success'] += 1
                    logger.debug(f"[DRY RUN] Would whitelist user {member.telegram_id}")
                
            except Exception as e:
                logger.error(f"Failed to whitelist user {member.telegram_id}: {e}")
                results['failed'] += 1
                self.tracker.mark_failed(member.telegram_id, str(e))
            
            await asyncio.sleep(0.01)  # Small delay to avoid overwhelming the database
        
        return results
    
    async def create_backup(self) -> str:
        """Create backup of existing data before migration"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = BACKUP_FILE.format(timestamp=timestamp)
        
        logger.info(f"Creating backup: {backup_file}")
        
        try:
            # Get current whitelist from database
            existing_users = self.db_client.get_active_users()
            whitelisted = [u for u in existing_users if u.subscription_status == 'whitelisted']
            
            backup_data = {
                'timestamp': timestamp,
                'total_whitelisted': len(whitelisted),
                'users': [{'telegram_id': u.telegram_id, 'username': u.username} for u in whitelisted]
            }
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backup created: {backup_file} ({len(whitelisted)} existing whitelisted users)")
            return backup_file
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    async def run_migration(self, source: str = 'group', file_path: Optional[str] = None) -> Dict:
        """Run the complete migration process"""
        logger.info("=" * 60)
        logger.info("Starting Migration Process")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"Source: {source}")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Create backup
            if not self.dry_run:
                backup_file = await self.create_backup()
            else:
                logger.info("[DRY RUN] Skipping backup creation")
            
            # Phase 2: Fetch members
            if source == 'file' and file_path:
                self.members_data = await self.fetch_members_from_file(file_path)
            else:
                self.members_data = await self.fetch_group_members()
            
            # Phase 3: Validate and deduplicate
            valid_members, duplicates = self.validate_members(self.members_data)
            self.tracker.state['total_count'] = len(valid_members)
            
            # Phase 4: Process in batches
            logger.info(f"Processing {len(valid_members)} members in batches of {BATCH_SIZE}")
            total_results = {'success': 0, 'failed': 0, 'skipped': 0}
            
            for i in range(0, len(valid_members), BATCH_SIZE):
                batch = valid_members[i:i + BATCH_SIZE]
                batch_num = (i // BATCH_SIZE) + 1
                total_batches = (len(valid_members) + BATCH_SIZE - 1) // BATCH_SIZE
                
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} users)")
                
                batch_results = await self.whitelist_batch(batch)
                
                # Update totals
                for key, value in batch_results.items():
                    total_results[key] += value
                
                # Progress report
                progress = ((i + len(batch)) / len(valid_members)) * 100
                logger.info(
                    f"Progress: {progress:.1f}% | "
                    f"Success: {total_results['success']} | "
                    f"Failed: {total_results['failed']} | "
                    f"Skipped: {total_results['skipped']}"
                )
                
                # Save checkpoint
                self.tracker.save_checkpoint()
                
                # Rate limiting between batches
                await asyncio.sleep(1)
            
            # Phase 5: Final report
            self.tracker.state['status'] = 'completed'
            self.tracker.save_checkpoint()
            
            summary = {
                'status': 'success' if total_results['failed'] == 0 else 'completed_with_errors',
                'total_members': len(valid_members),
                'successfully_whitelisted': total_results['success'],
                'failed': total_results['failed'],
                'skipped': total_results['skipped'],
                'duplicates_found': len(duplicates),
                'backup_file': backup_file if not self.dry_run else None,
                'dry_run': self.dry_run
            }
            
            # Print final report
            logger.info("=" * 60)
            logger.info("Migration Complete!")
            logger.info("=" * 60)
            for key, value in summary.items():
                logger.info(f"{key}: {value}")
            
            return summary
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.tracker.state['status'] = 'failed'
            self.tracker.state['error'] = str(e)
            self.tracker.save_checkpoint()
            raise
        
        finally:
            await self.bot.session.close()
    
    async def verify_migration(self) -> Dict:
        """Verify migration results"""
        logger.info("Verifying migration...")
        
        try:
            # Get statistics from database
            stats = self.db_client.get_subscription_stats()
            
            # Get all whitelisted users
            all_users = self.db_client.get_active_users()
            whitelisted = [u for u in all_users if u.subscription_status == 'whitelisted']
            
            verification = {
                'database_whitelisted_count': stats.get('whitelisted_users', 0),
                'actual_whitelisted_count': len(whitelisted),
                'expected_count': self.tracker.state['total_count'],
                'processed_count': self.tracker.state['processed_count'],
                'match': len(whitelisted) >= self.tracker.state['processed_count']
            }
            
            logger.info("Verification Results:")
            for key, value in verification.items():
                logger.info(f"  {key}: {value}")
            
            return verification
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {'error': str(e)}
    
    async def rollback_migration(self, backup_file: str) -> bool:
        """Rollback migration using backup file"""
        logger.warning(f"Rolling back migration using backup: {backup_file}")
        
        try:
            # This would require implementing a rollback mechanism
            # For now, just log the intention
            logger.error("Rollback not implemented - manual intervention required")
            logger.info(f"Please restore from backup: {backup_file}")
            return False
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Migrate existing Telegram group members to whitelist')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode (no changes)')
    parser.add_argument('--source', choices=['group', 'file'], default='group', 
                       help='Source of member data')
    parser.add_argument('--file', type=str, help='Path to JSON file with member data')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing migration')
    parser.add_argument('--reset', action='store_true', help='Reset migration checkpoint')
    
    args = parser.parse_args()
    
    # Reset checkpoint if requested
    if args.reset:
        checkpoint_file = Path(CHECKPOINT_FILE)
        if checkpoint_file.exists():
            checkpoint_file.unlink()
            logger.info("Migration checkpoint reset")
    
    # Initialize database client
    db_client = SupabaseClient(url=SUPABASE_URL, key=SUPABASE_SERVICE_KEY)
    
    # Create migration instance
    migration = GroupMemberMigration(
        bot_token=BOT_TOKEN,
        group_id=GROUP_ID,
        db_client=db_client,
        dry_run=args.dry_run
    )
    
    try:
        if args.verify_only:
            # Only run verification
            result = await migration.verify_migration()
            print(json.dumps(result, indent=2))
        else:
            # Run full migration
            result = await migration.run_migration(
                source=args.source,
                file_path=args.file
            )
            
            # Verify after migration
            if not args.dry_run:
                verification = await migration.verify_migration()
                result['verification'] = verification
            
            # Save final report
            report_file = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(result, f, indent=2)
            logger.info(f"Migration report saved: {report_file}")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
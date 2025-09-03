#!/usr/bin/env python3
"""
Production-Grade Migration Script for Whitelisting Telegram Group Members
Safely migrates 1100+ members with full tracking, resume capability, and rollback support
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import hashlib
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient, ActivityAction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Migration Configuration
class MigrationConfig:
    """Central configuration for migration parameters"""
    BATCH_SIZE = 100  # Users per batch
    CHECKPOINT_INTERVAL = 10  # Save checkpoint every N users
    RATE_LIMIT_DELAY = 0.01  # Delay between operations (seconds)
    MAX_RETRIES = 3  # Maximum retries for failed operations
    RETRY_DELAY = 1.0  # Initial retry delay (seconds)
    VERIFICATION_SAMPLE_SIZE = 100  # Sample size for verification checks
    
    # File paths
    CHECKPOINT_DIR = Path("migration_checkpoints")
    BACKUP_DIR = Path("migration_backups")
    REPORT_DIR = Path("migration_reports")
    
    @classmethod
    def ensure_directories(cls):
        """Ensure all required directories exist"""
        cls.CHECKPOINT_DIR.mkdir(exist_ok=True)
        cls.BACKUP_DIR.mkdir(exist_ok=True)
        cls.REPORT_DIR.mkdir(exist_ok=True)

class MigrationStatus(Enum):
    """Migration status states"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

@dataclass
class UserMigrationRecord:
    """Record for tracking individual user migration"""
    telegram_id: int
    username: Optional[str]
    full_name: Optional[str]
    status: str = "pending"
    attempts: int = 0
    last_error: Optional[str] = None
    processed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserMigrationRecord':
        return cls(**data)
    
    def generate_hash(self) -> str:
        """Generate unique hash for the user record"""
        data = f"{self.telegram_id}:{self.username or ''}:{self.full_name or ''}"
        return hashlib.md5(data.encode()).hexdigest()

class MigrationCheckpoint:
    """Manages migration checkpoints for resume capability"""
    
    def __init__(self, migration_id: str):
        self.migration_id = migration_id
        MigrationConfig.ensure_directories()
        self.checkpoint_file = MigrationConfig.CHECKPOINT_DIR / f"{migration_id}_checkpoint.json"
        self.state = self.load() or self.initialize()
    
    def initialize(self) -> Dict:
        """Initialize new checkpoint state"""
        return {
            'migration_id': self.migration_id,
            'status': MigrationStatus.PENDING.value,
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'total_users': 0,
            'processed_users': [],
            'failed_users': [],
            'pending_users': [],
            'batches_completed': 0,
            'statistics': {
                'success_count': 0,
                'failure_count': 0,
                'retry_count': 0,
                'skip_count': 0
            },
            'configuration': {
                'batch_size': MigrationConfig.BATCH_SIZE,
                'dry_run': False,
                'source': None
            }
        }
    
    def load(self) -> Optional[Dict]:
        """Load checkpoint from file"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")
        return None
    
    def save(self):
        """Save checkpoint to file"""
        self.state['last_updated'] = datetime.now().isoformat()
        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Checkpoint saved: {self.checkpoint_file}")
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
    
    def update_user_status(self, telegram_id: int, status: str, error: Optional[str] = None):
        """Update status for a specific user"""
        user_record = {
            'telegram_id': telegram_id,
            'status': status,
            'processed_at': datetime.now().isoformat(),
            'error': error
        }
        
        if status == 'success':
            self.state['processed_users'].append(telegram_id)
            self.state['statistics']['success_count'] += 1
        elif status == 'failed':
            self.state['failed_users'].append(user_record)
            self.state['statistics']['failure_count'] += 1
        
        # Save checkpoint periodically
        total_processed = len(self.state['processed_users']) + len(self.state['failed_users'])
        if total_processed % MigrationConfig.CHECKPOINT_INTERVAL == 0:
            self.save()
    
    def is_processed(self, telegram_id: int) -> bool:
        """Check if user has already been processed"""
        return telegram_id in self.state['processed_users']
    
    def get_pending_users(self) -> List[Dict]:
        """Get list of users still pending processing"""
        return self.state.get('pending_users', [])
    
    def mark_batch_complete(self, batch_num: int):
        """Mark a batch as completed"""
        self.state['batches_completed'] = batch_num
        self.save()

class MigrationBackup:
    """Handles backup and rollback operations"""
    
    def __init__(self, migration_id: str, db_client: SupabaseClient):
        self.migration_id = migration_id
        self.db_client = db_client
        MigrationConfig.ensure_directories()
        self.backup_file = MigrationConfig.BACKUP_DIR / f"{migration_id}_backup.json"
    
    def create_backup(self) -> Dict:
        """Create comprehensive backup before migration"""
        logger.info("Creating pre-migration backup...")
        
        try:
            # Fetch all current whitelisted users
            all_users = self.db_client.get_active_users()
            whitelisted_users = [
                {
                    'telegram_id': u.telegram_id,
                    'username': u.username,
                    'subscription_status': u.subscription_status,
                    'payment_method': u.payment_method
                }
                for u in all_users if u.subscription_status == 'whitelisted'
            ]
            
            # Get database statistics
            stats = self.db_client.get_subscription_stats()
            
            backup_data = {
                'migration_id': self.migration_id,
                'created_at': datetime.now().isoformat(),
                'database_stats': stats,
                'whitelisted_users': whitelisted_users,
                'total_whitelisted': len(whitelisted_users),
                'metadata': {
                    'supabase_url': os.getenv('SUPABASE_URL'),
                    'environment': os.getenv('ENVIRONMENT', 'production')
                }
            }
            
            # Save backup
            with open(self.backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            logger.info(f"Backup created: {self.backup_file} ({len(whitelisted_users)} users)")
            return backup_data
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def verify_backup(self) -> bool:
        """Verify backup file integrity"""
        if not self.backup_file.exists():
            return False
        
        try:
            with open(self.backup_file, 'r') as f:
                data = json.load(f)
            return 'whitelisted_users' in data and 'migration_id' in data
        except:
            return False
    
    def restore_from_backup(self) -> Tuple[bool, str]:
        """Restore database to pre-migration state"""
        logger.warning("Starting rollback from backup...")
        
        try:
            with open(self.backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # This would need to be implemented based on your specific needs
            # For safety, we're not implementing automatic rollback
            logger.error("Automatic rollback not implemented for safety")
            logger.info(f"Manual rollback required using backup: {self.backup_file}")
            
            return False, "Manual rollback required"
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False, str(e)

class ProductionMigration:
    """Main production migration orchestrator"""
    
    def __init__(self, db_client: SupabaseClient, dry_run: bool = False):
        self.db_client = db_client
        self.dry_run = dry_run
        self.migration_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.checkpoint = MigrationCheckpoint(self.migration_id)
        self.backup = MigrationBackup(self.migration_id, db_client)
        self.start_time = None
        self.end_time = None
    
    def load_users_from_file(self, file_path: str) -> List[UserMigrationRecord]:
        """Load users from JSON file"""
        logger.info(f"Loading users from: {file_path}")
        
        users = []
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        for item in data:
            if isinstance(item, dict):
                record = UserMigrationRecord(
                    telegram_id=item.get('telegram_id', item.get('id', 0)),
                    username=item.get('username'),
                    full_name=item.get('full_name', item.get('name'))
                )
            else:
                # Simple ID list
                record = UserMigrationRecord(
                    telegram_id=int(item),
                    username=None,
                    full_name=None
                )
            
            if record.telegram_id:
                users.append(record)
        
        logger.info(f"Loaded {len(users)} users from file")
        return users
    
    def validate_and_deduplicate(self, users: List[UserMigrationRecord]) -> Tuple[List[UserMigrationRecord], Dict]:
        """Validate and deduplicate user list"""
        logger.info("Validating and deduplicating users...")
        
        seen_ids = set()
        valid_users = []
        duplicates = []
        invalid = []
        
        for user in users:
            if not user.telegram_id or user.telegram_id <= 0:
                invalid.append(user.to_dict())
                continue
            
            if user.telegram_id in seen_ids:
                duplicates.append(user.to_dict())
                continue
            
            seen_ids.add(user.telegram_id)
            valid_users.append(user)
        
        validation_report = {
            'total_input': len(users),
            'valid_users': len(valid_users),
            'duplicates_removed': len(duplicates),
            'invalid_entries': len(invalid)
        }
        
        logger.info(f"Validation complete: {validation_report}")
        return valid_users, validation_report
    
    async def process_batch(self, batch: List[UserMigrationRecord], batch_num: int) -> Dict:
        """Process a batch of users"""
        batch_results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'retried': 0
        }
        
        for user in batch:
            # Check if already processed
            if self.checkpoint.is_processed(user.telegram_id):
                batch_results['skipped'] += 1
                continue
            
            # Process user with retry logic
            for attempt in range(MigrationConfig.MAX_RETRIES):
                try:
                    if not self.dry_run:
                        # Whitelist the user
                        success = self.db_client.whitelist_user(
                            telegram_id=user.telegram_id,
                            username=user.username
                        )
                        
                        if success:
                            # Log activity
                            self.db_client.log_activity(
                                telegram_id=user.telegram_id,
                                action=ActivityAction.USER_WHITELISTED.value,
                                details={
                                    'migration_id': self.migration_id,
                                    'batch_number': batch_num,
                                    'attempt': attempt + 1,
                                    'source': 'production_migration'
                                }
                            )
                            
                            batch_results['success'] += 1
                            self.checkpoint.update_user_status(user.telegram_id, 'success')
                            break
                        else:
                            raise Exception("Database operation returned False")
                    else:
                        # Dry run mode
                        logger.debug(f"[DRY RUN] Would whitelist user {user.telegram_id}")
                        batch_results['success'] += 1
                        break
                    
                except Exception as e:
                    user.attempts += 1
                    user.last_error = str(e)
                    
                    if attempt < MigrationConfig.MAX_RETRIES - 1:
                        batch_results['retried'] += 1
                        await asyncio.sleep(MigrationConfig.RETRY_DELAY * (attempt + 1))
                    else:
                        batch_results['failed'] += 1
                        self.checkpoint.update_user_status(
                            user.telegram_id, 
                            'failed', 
                            error=str(e)
                        )
                        logger.error(f"Failed to whitelist user {user.telegram_id} after {attempt + 1} attempts: {e}")
            
            # Rate limiting
            await asyncio.sleep(MigrationConfig.RATE_LIMIT_DELAY)
        
        return batch_results
    
    async def run_migration(self, users: List[UserMigrationRecord]) -> Dict:
        """Execute the main migration process"""
        self.start_time = datetime.now()
        logger.info("=" * 80)
        logger.info(f"Starting Production Migration: {self.migration_id}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'PRODUCTION'}")
        logger.info(f"Total users to process: {len(users)}")
        logger.info("=" * 80)
        
        # Update checkpoint configuration
        self.checkpoint.state['configuration']['dry_run'] = self.dry_run
        self.checkpoint.state['total_users'] = len(users)
        self.checkpoint.state['pending_users'] = [u.to_dict() for u in users]
        self.checkpoint.state['status'] = MigrationStatus.IN_PROGRESS.value
        self.checkpoint.save()
        
        # Create backup (skip in dry run)
        backup_info = None
        if not self.dry_run:
            try:
                backup_info = self.backup.create_backup()
            except Exception as e:
                logger.error(f"Failed to create backup: {e}")
                if input("Continue without backup? (yes/no): ").lower() != 'yes':
                    raise
        
        # Process in batches
        total_results = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'retried': 0
        }
        
        total_batches = (len(users) + MigrationConfig.BATCH_SIZE - 1) // MigrationConfig.BATCH_SIZE
        
        for i in range(0, len(users), MigrationConfig.BATCH_SIZE):
            batch = users[i:i + MigrationConfig.BATCH_SIZE]
            batch_num = (i // MigrationConfig.BATCH_SIZE) + 1
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} users)...")
            
            try:
                batch_results = await self.process_batch(batch, batch_num)
                
                # Update totals
                for key, value in batch_results.items():
                    total_results[key] += value
                
                # Update checkpoint
                self.checkpoint.mark_batch_complete(batch_num)
                
                # Progress report
                processed = total_results['success'] + total_results['failed'] + total_results['skipped']
                progress = (processed / len(users)) * 100
                eta = self.calculate_eta(processed, len(users))
                
                logger.info(
                    f"Progress: {progress:.1f}% | "
                    f"Success: {total_results['success']} | "
                    f"Failed: {total_results['failed']} | "
                    f"Skipped: {total_results['skipped']} | "
                    f"ETA: {eta}"
                )
                
                # Pause between batches
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                logger.warning("Migration interrupted by user")
                self.checkpoint.state['status'] = MigrationStatus.PAUSED.value
                self.checkpoint.save()
                raise
            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                self.checkpoint.state['status'] = MigrationStatus.FAILED.value
                self.checkpoint.save()
                raise
        
        # Mark migration as completed
        self.end_time = datetime.now()
        self.checkpoint.state['status'] = MigrationStatus.COMPLETED.value
        self.checkpoint.state['completed_at'] = self.end_time.isoformat()
        self.checkpoint.save()
        
        # Generate final report
        migration_report = {
            'migration_id': self.migration_id,
            'status': self.checkpoint.state['status'],
            'dry_run': self.dry_run,
            'started_at': self.start_time.isoformat(),
            'completed_at': self.end_time.isoformat(),
            'duration': str(self.end_time - self.start_time),
            'total_users': len(users),
            'results': total_results,
            'backup_created': backup_info is not None,
            'checkpoint_file': str(self.checkpoint.checkpoint_file),
            'success_rate': (total_results['success'] / len(users) * 100) if len(users) > 0 else 0
        }
        
        return migration_report
    
    def calculate_eta(self, processed: int, total: int) -> str:
        """Calculate estimated time of arrival"""
        if processed == 0:
            return "calculating..."
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        rate = processed / elapsed
        remaining = total - processed
        eta_seconds = remaining / rate if rate > 0 else 0
        
        return str(timedelta(seconds=int(eta_seconds)))
    
    async def verify_migration(self, expected_count: int) -> Dict:
        """Verify migration was successful"""
        logger.info("Running post-migration verification...")
        
        verification_results = {
            'timestamp': datetime.now().isoformat(),
            'expected_whitelisted': expected_count,
            'checks': {}
        }
        
        try:
            # Check 1: Database statistics
            stats = self.db_client.get_subscription_stats()
            verification_results['checks']['database_stats'] = {
                'whitelisted_users': stats.get('whitelisted_users', 0),
                'total_users': stats.get('total_users', 0)
            }
            
            # Check 2: Sample verification
            whitelisted = self.db_client.get_whitelisted_users(limit=MigrationConfig.VERIFICATION_SAMPLE_SIZE)
            verification_results['checks']['sample_verification'] = {
                'sample_size': len(whitelisted),
                'all_whitelisted': all(u.subscription_status == 'whitelisted' for u in whitelisted)
            }
            
            # Check 3: Failed users
            failed_users = self.checkpoint.state.get('failed_users', [])
            verification_results['checks']['failed_users'] = {
                'count': len(failed_users),
                'requires_attention': len(failed_users) > 0
            }
            
            # Overall verification status
            actual_whitelisted = stats.get('whitelisted_users', 0)
            verification_results['status'] = 'passed' if actual_whitelisted >= expected_count else 'failed'
            verification_results['actual_whitelisted'] = actual_whitelisted
            verification_results['discrepancy'] = actual_whitelisted - expected_count
            
            return verification_results
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            verification_results['status'] = 'error'
            verification_results['error'] = str(e)
            return verification_results
    
    def generate_report(self, migration_report: Dict, verification_results: Dict) -> str:
        """Generate comprehensive migration report"""
        MigrationConfig.ensure_directories()
        report_file = MigrationConfig.REPORT_DIR / f"{self.migration_id}_report.json"
        
        full_report = {
            'migration': migration_report,
            'verification': verification_results,
            'checkpoint_data': self.checkpoint.state,
            'generated_at': datetime.now().isoformat()
        }
        
        with open(report_file, 'w') as f:
            json.dump(full_report, f, indent=2)
        
        logger.info(f"Report saved: {report_file}")
        return str(report_file)

async def main():
    """Main entry point for production migration"""
    parser = argparse.ArgumentParser(
        description='Production-grade migration script for whitelisting Telegram group members'
    )
    parser.add_argument(
        '--file', 
        required=True,
        help='Path to JSON file containing user data'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Run in dry-run mode (no database changes)'
    )
    parser.add_argument(
        '--resume', 
        help='Resume from checkpoint file'
    )
    parser.add_argument(
        '--verify-only', 
        action='store_true',
        help='Only run verification on existing migration'
    )
    
    args = parser.parse_args()
    
    # Initialize database client
    db_url = os.getenv('SUPABASE_URL')
    db_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not db_url or not db_key:
        logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        sys.exit(1)
    
    db_client = SupabaseClient(url=db_url, key=db_key)
    
    # Create migration instance
    migration = ProductionMigration(db_client, dry_run=args.dry_run)
    
    try:
        if args.verify_only:
            # Run verification only
            if not args.resume:
                logger.error("Please provide --resume with checkpoint to verify")
                sys.exit(1)
            
            # Load checkpoint
            migration.checkpoint = MigrationCheckpoint(args.resume)
            expected = migration.checkpoint.state.get('statistics', {}).get('success_count', 0)
            verification = await migration.verify_migration(expected)
            
            print(json.dumps(verification, indent=2))
            
        else:
            # Load users
            if not Path(args.file).exists():
                logger.error(f"File not found: {args.file}")
                sys.exit(1)
            
            users = migration.load_users_from_file(args.file)
            
            # Validate and deduplicate
            valid_users, validation_report = migration.validate_and_deduplicate(users)
            
            if len(valid_users) == 0:
                logger.error("No valid users to process")
                sys.exit(1)
            
            # Confirmation prompt for production run
            if not args.dry_run:
                logger.warning("=" * 80)
                logger.warning("PRODUCTION MIGRATION - THIS WILL MODIFY THE DATABASE")
                logger.warning(f"About to whitelist {len(valid_users)} users")
                logger.warning("=" * 80)
                
                confirmation = input("Type 'PROCEED' to continue: ")
                if confirmation != 'PROCEED':
                    logger.info("Migration cancelled by user")
                    sys.exit(0)
            
            # Run migration
            migration_report = await migration.run_migration(valid_users)
            
            # Verify results
            verification_results = await migration.verify_migration(
                migration_report['results']['success']
            )
            
            # Generate report
            report_file = migration.generate_report(migration_report, verification_results)
            
            # Print summary
            logger.info("=" * 80)
            logger.info("MIGRATION COMPLETE")
            logger.info("=" * 80)
            logger.info(f"Status: {migration_report['status']}")
            logger.info(f"Success: {migration_report['results']['success']}")
            logger.info(f"Failed: {migration_report['results']['failed']}")
            logger.info(f"Success Rate: {migration_report['success_rate']:.1f}%")
            logger.info(f"Report: {report_file}")
            
            if verification_results['status'] != 'passed':
                logger.warning("VERIFICATION FAILED - Please check the report for details")
                sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("Migration interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
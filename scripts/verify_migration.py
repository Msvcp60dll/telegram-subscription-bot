#!/usr/bin/env python3
"""
Post-Migration Verification Script
Compares group members with database and generates reconciliation reports
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional, Tuple
from pathlib import Path
import argparse

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationVerifier:
    """Comprehensive migration verification and reconciliation"""
    
    def __init__(self, db_client: SupabaseClient):
        self.db_client = db_client
        self.verification_results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'discrepancies': [],
            'recommendations': []
        }
    
    def load_expected_users(self, source: str) -> Set[int]:
        """Load expected user IDs from various sources"""
        expected_ids = set()
        
        if source.endswith('.json'):
            # JSON file with member data
            with open(source, 'r') as f:
                data = json.load(f)
            
            for item in data:
                if isinstance(item, dict):
                    telegram_id = item.get('telegram_id') or item.get('id')
                else:
                    telegram_id = item
                
                if telegram_id:
                    expected_ids.add(int(telegram_id))
        
        elif source.endswith('_checkpoint.json'):
            # Migration checkpoint file
            with open(source, 'r') as f:
                data = json.load(f)
            
            processed = data.get('processed_users', [])
            expected_ids.update(processed)
        
        else:
            raise ValueError(f"Unsupported source format: {source}")
        
        logger.info(f"Loaded {len(expected_ids)} expected user IDs from {source}")
        return expected_ids
    
    def get_database_users(self) -> Tuple[Set[int], Dict[int, Dict]]:
        """Get all whitelisted users from database"""
        whitelisted_ids = set()
        user_details = {}
        
        try:
            users = self.db_client.get_whitelisted_users()
            
            for user in users:
                whitelisted_ids.add(user.telegram_id)
                user_details[user.telegram_id] = {
                    'username': user.username,
                    'status': user.subscription_status,
                    'created_at': user.created_at.isoformat() if user.created_at else None
                }
            
            logger.info(f"Found {len(whitelisted_ids)} whitelisted users in database")
            return whitelisted_ids, user_details
            
        except Exception as e:
            logger.error(f"Failed to get database users: {e}")
            return set(), {}
    
    def verify_basic_counts(self, expected_ids: Set[int], database_ids: Set[int]) -> Dict:
        """Verify basic count matching"""
        return {
            'expected_count': len(expected_ids),
            'database_count': len(database_ids),
            'match': len(expected_ids) == len(database_ids),
            'difference': len(database_ids) - len(expected_ids)
        }
    
    def find_discrepancies(self, expected_ids: Set[int], database_ids: Set[int]) -> Dict:
        """Find missing and extra users"""
        missing_from_db = expected_ids - database_ids
        extra_in_db = database_ids - expected_ids
        correctly_migrated = expected_ids & database_ids
        
        return {
            'missing_from_database': list(missing_from_db),
            'extra_in_database': list(extra_in_db),
            'correctly_migrated': len(correctly_migrated),
            'missing_count': len(missing_from_db),
            'extra_count': len(extra_in_db),
            'accuracy_percentage': (len(correctly_migrated) / len(expected_ids) * 100) if expected_ids else 0
        }
    
    def verify_data_integrity(self, sample_size: int = 100) -> Dict:
        """Verify data integrity for a sample of users"""
        try:
            users = self.db_client.get_whitelisted_users(limit=sample_size)
            
            integrity_checks = {
                'sample_size': len(users),
                'all_whitelisted': True,
                'all_have_valid_ids': True,
                'payment_method_correct': True,
                'invalid_users': []
            }
            
            for user in users:
                # Check whitelist status
                if user.subscription_status != 'whitelisted':
                    integrity_checks['all_whitelisted'] = False
                    integrity_checks['invalid_users'].append({
                        'telegram_id': user.telegram_id,
                        'issue': 'not_whitelisted',
                        'status': user.subscription_status
                    })
                
                # Check ID validity
                if not user.telegram_id or user.telegram_id <= 0:
                    integrity_checks['all_have_valid_ids'] = False
                    integrity_checks['invalid_users'].append({
                        'telegram_id': user.telegram_id,
                        'issue': 'invalid_id'
                    })
                
                # Check payment method
                if user.payment_method and user.payment_method != 'whitelisted':
                    integrity_checks['payment_method_correct'] = False
                    integrity_checks['invalid_users'].append({
                        'telegram_id': user.telegram_id,
                        'issue': 'wrong_payment_method',
                        'payment_method': user.payment_method
                    })
            
            integrity_checks['passed'] = (
                integrity_checks['all_whitelisted'] and 
                integrity_checks['all_have_valid_ids'] and 
                integrity_checks['payment_method_correct']
            )
            
            return integrity_checks
            
        except Exception as e:
            logger.error(f"Data integrity check failed: {e}")
            return {'error': str(e), 'passed': False}
    
    def check_activity_logs(self, migration_id: Optional[str] = None, hours: int = 24) -> Dict:
        """Check activity logs for migration events"""
        try:
            since = datetime.now() - timedelta(hours=hours)
            
            # This would need to be implemented in the SupabaseClient
            # For now, we'll do a basic check
            stats = self.db_client.get_subscription_stats()
            
            return {
                'checked': True,
                'total_whitelisted': stats.get('whitelisted_users', 0),
                'period_hours': hours,
                'migration_id': migration_id
            }
            
        except Exception as e:
            logger.error(f"Activity log check failed: {e}")
            return {'error': str(e), 'checked': False}
    
    def verify_database_consistency(self) -> Dict:
        """Check database consistency and constraints"""
        consistency_checks = {
            'no_duplicates': True,
            'statistics_match': True,
            'issues': []
        }
        
        try:
            # Get statistics
            stats = self.db_client.get_subscription_stats()
            
            # Get actual count
            all_users = self.db_client.get_whitelisted_users()
            actual_count = len(all_users)
            
            # Check if stats match reality
            if stats.get('whitelisted_users') != actual_count:
                consistency_checks['statistics_match'] = False
                consistency_checks['issues'].append({
                    'type': 'stats_mismatch',
                    'stats_count': stats.get('whitelisted_users'),
                    'actual_count': actual_count
                })
            
            # Check for duplicates
            seen_ids = set()
            for user in all_users:
                if user.telegram_id in seen_ids:
                    consistency_checks['no_duplicates'] = False
                    consistency_checks['issues'].append({
                        'type': 'duplicate',
                        'telegram_id': user.telegram_id
                    })
                seen_ids.add(user.telegram_id)
            
            consistency_checks['passed'] = (
                consistency_checks['no_duplicates'] and 
                consistency_checks['statistics_match']
            )
            
            return consistency_checks
            
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return {'error': str(e), 'passed': False}
    
    def fix_discrepancies(self, missing_users: List[int], dry_run: bool = True) -> Dict:
        """Attempt to fix identified discrepancies"""
        fix_results = {
            'attempted': len(missing_users),
            'successful': 0,
            'failed': 0,
            'dry_run': dry_run,
            'fixed_users': [],
            'failed_users': []
        }
        
        for telegram_id in missing_users:
            try:
                if not dry_run:
                    success = self.db_client.whitelist_user(telegram_id)
                    if success:
                        fix_results['successful'] += 1
                        fix_results['fixed_users'].append(telegram_id)
                        logger.info(f"Fixed: Added user {telegram_id} to whitelist")
                    else:
                        fix_results['failed'] += 1
                        fix_results['failed_users'].append(telegram_id)
                        logger.error(f"Failed to fix user {telegram_id}")
                else:
                    logger.info(f"[DRY RUN] Would add user {telegram_id} to whitelist")
                    fix_results['successful'] += 1
                    
            except Exception as e:
                fix_results['failed'] += 1
                fix_results['failed_users'].append(telegram_id)
                logger.error(f"Error fixing user {telegram_id}: {e}")
        
        return fix_results
    
    def generate_reconciliation_report(self, 
                                      expected_ids: Set[int],
                                      database_ids: Set[int],
                                      user_details: Dict[int, Dict]) -> str:
        """Generate comprehensive reconciliation report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("MIGRATION VERIFICATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().isoformat()}")
        report_lines.append("")
        
        # Basic counts
        counts = self.verify_basic_counts(expected_ids, database_ids)
        report_lines.append("SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Expected users: {counts['expected_count']}")
        report_lines.append(f"Database users: {counts['database_count']}")
        report_lines.append(f"Difference: {counts['difference']}")
        report_lines.append(f"Status: {'✅ MATCH' if counts['match'] else '❌ MISMATCH'}")
        report_lines.append("")
        
        # Discrepancies
        discrepancies = self.find_discrepancies(expected_ids, database_ids)
        report_lines.append("DISCREPANCY ANALYSIS")
        report_lines.append("-" * 40)
        report_lines.append(f"Correctly migrated: {discrepancies['correctly_migrated']}")
        report_lines.append(f"Missing from database: {discrepancies['missing_count']}")
        report_lines.append(f"Extra in database: {discrepancies['extra_count']}")
        report_lines.append(f"Accuracy: {discrepancies['accuracy_percentage']:.2f}%")
        report_lines.append("")
        
        # Missing users detail
        if discrepancies['missing_from_database']:
            report_lines.append("MISSING USERS (need to be added)")
            report_lines.append("-" * 40)
            for user_id in discrepancies['missing_from_database'][:20]:  # First 20
                report_lines.append(f"  - {user_id}")
            if len(discrepancies['missing_from_database']) > 20:
                report_lines.append(f"  ... and {len(discrepancies['missing_from_database']) - 20} more")
            report_lines.append("")
        
        # Extra users detail
        if discrepancies['extra_in_database']:
            report_lines.append("EXTRA USERS (not in source)")
            report_lines.append("-" * 40)
            for user_id in discrepancies['extra_in_database'][:20]:  # First 20
                details = user_details.get(user_id, {})
                username = f"@{details['username']}" if details.get('username') else "N/A"
                report_lines.append(f"  - {user_id} ({username})")
            if len(discrepancies['extra_in_database']) > 20:
                report_lines.append(f"  ... and {len(discrepancies['extra_in_database']) - 20} more")
            report_lines.append("")
        
        # Data integrity
        integrity = self.verify_data_integrity()
        report_lines.append("DATA INTEGRITY CHECK")
        report_lines.append("-" * 40)
        report_lines.append(f"Sample size: {integrity.get('sample_size', 0)}")
        report_lines.append(f"All whitelisted: {'✅' if integrity.get('all_whitelisted') else '❌'}")
        report_lines.append(f"Valid IDs: {'✅' if integrity.get('all_have_valid_ids') else '❌'}")
        report_lines.append(f"Payment method correct: {'✅' if integrity.get('payment_method_correct') else '❌'}")
        
        if integrity.get('invalid_users'):
            report_lines.append("\nInvalid users found:")
            for invalid in integrity['invalid_users'][:5]:
                report_lines.append(f"  - ID: {invalid['telegram_id']}, Issue: {invalid['issue']}")
        report_lines.append("")
        
        # Database consistency
        consistency = self.verify_database_consistency()
        report_lines.append("DATABASE CONSISTENCY")
        report_lines.append("-" * 40)
        report_lines.append(f"No duplicates: {'✅' if consistency.get('no_duplicates') else '❌'}")
        report_lines.append(f"Statistics match: {'✅' if consistency.get('statistics_match') else '❌'}")
        
        if consistency.get('issues'):
            report_lines.append("\nIssues found:")
            for issue in consistency['issues'][:5]:
                report_lines.append(f"  - {issue}")
        report_lines.append("")
        
        # Overall status
        overall_pass = (
            counts['match'] and 
            discrepancies['accuracy_percentage'] >= 99 and
            integrity.get('passed', False) and
            consistency.get('passed', False)
        )
        
        report_lines.append("OVERALL VERIFICATION")
        report_lines.append("-" * 40)
        report_lines.append(f"Status: {'✅ PASSED' if overall_pass else '❌ FAILED'}")
        
        if not overall_pass:
            report_lines.append("\nRECOMMENDATIONS:")
            if discrepancies['missing_count'] > 0:
                report_lines.append(f"1. Run fix command to add {discrepancies['missing_count']} missing users")
            if not integrity.get('passed'):
                report_lines.append("2. Review and fix data integrity issues")
            if not consistency.get('passed'):
                report_lines.append("3. Review and fix database consistency issues")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    async def run_verification(self, source: str, fix: bool = False, dry_run: bool = True) -> Dict:
        """Run complete verification process"""
        logger.info("Starting migration verification...")
        
        # Load expected users
        expected_ids = self.load_expected_users(source)
        
        # Get database users
        database_ids, user_details = self.get_database_users()
        
        # Run all checks
        self.verification_results['checks']['counts'] = self.verify_basic_counts(expected_ids, database_ids)
        self.verification_results['checks']['discrepancies'] = self.find_discrepancies(expected_ids, database_ids)
        self.verification_results['checks']['integrity'] = self.verify_data_integrity()
        self.verification_results['checks']['consistency'] = self.verify_database_consistency()
        self.verification_results['checks']['activity'] = self.check_activity_logs()
        
        # Generate report
        report = self.generate_reconciliation_report(expected_ids, database_ids, user_details)
        self.verification_results['report'] = report
        
        # Print report
        print(report)
        
        # Fix discrepancies if requested
        if fix:
            missing_users = self.verification_results['checks']['discrepancies']['missing_from_database']
            if missing_users:
                print("\n" + "=" * 80)
                print("ATTEMPTING FIXES")
                print("=" * 80)
                
                fix_results = self.fix_discrepancies(missing_users, dry_run=dry_run)
                self.verification_results['fixes'] = fix_results
                
                print(f"Fixed {fix_results['successful']} out of {fix_results['attempted']} missing users")
                if fix_results['failed'] > 0:
                    print(f"Failed to fix {fix_results['failed']} users")
            else:
                print("\nNo fixes needed - all users properly migrated!")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"verification_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.verification_results, f, indent=2)
        
        logger.info(f"Verification report saved: {report_file}")
        
        return self.verification_results

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Verify migration and generate reconciliation report'
    )
    parser.add_argument(
        '--file',
        help='Source file with expected users (JSON or checkpoint file)'
    )
    parser.add_argument(
        '--checkpoint',
        help='Migration checkpoint file to verify'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Attempt to fix discrepancies by adding missing users'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Dry run mode for fixes (default: True)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually execute fixes (disables dry-run)'
    )
    
    args = parser.parse_args()
    
    # Determine source
    source = args.file or args.checkpoint
    if not source:
        # Try to find latest checkpoint
        checkpoint_dir = Path("migration_checkpoints")
        if checkpoint_dir.exists():
            checkpoints = list(checkpoint_dir.glob("*_checkpoint.json"))
            if checkpoints:
                source = str(max(checkpoints, key=lambda p: p.stat().st_mtime))
                print(f"Using latest checkpoint: {source}")
    
    if not source:
        print("Error: No source file specified and no checkpoint found")
        print("Use --file or --checkpoint to specify the source")
        sys.exit(1)
    
    # Initialize database
    db_url = os.getenv('SUPABASE_URL')
    db_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not db_url or not db_key:
        print("Error: Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variables")
        sys.exit(1)
    
    db_client = SupabaseClient(url=db_url, key=db_key)
    
    # Run verification
    verifier = MigrationVerifier(db_client)
    
    # Determine if we're doing actual fixes
    dry_run = not args.execute if args.fix else True
    
    if args.fix and not dry_run:
        print("WARNING: Running in EXECUTE mode - this will modify the database!")
        confirmation = input("Type 'CONFIRM' to proceed: ")
        if confirmation != 'CONFIRM':
            print("Cancelled by user")
            sys.exit(0)
    
    results = await verifier.run_verification(source, fix=args.fix, dry_run=dry_run)
    
    # Exit code based on verification status
    overall_pass = all(
        check.get('passed', False) 
        for check in results['checks'].values() 
        if isinstance(check, dict) and 'passed' in check
    )
    
    sys.exit(0 if overall_pass else 1)

if __name__ == "__main__":
    asyncio.run(main())
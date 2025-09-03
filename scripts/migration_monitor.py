#!/usr/bin/env python3
"""
Real-time Migration Monitoring Dashboard
Provides live statistics and progress tracking during migration
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
import curses

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient

class MigrationMonitor:
    """Real-time migration monitoring"""
    
    def __init__(self, checkpoint_file: Optional[str] = None):
        self.checkpoint_file = checkpoint_file
        self.checkpoint_data = None
        self.db_client = None
        self.start_time = None
        self.last_update = None
        self.refresh_interval = 1.0  # seconds
        
        # Initialize database if credentials available
        db_url = os.getenv('SUPABASE_URL')
        db_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if db_url and db_key:
            self.db_client = SupabaseClient(url=db_url, key=db_key)
    
    def find_latest_checkpoint(self) -> Optional[str]:
        """Find the most recent checkpoint file"""
        checkpoint_dir = Path("migration_checkpoints")
        if not checkpoint_dir.exists():
            return None
        
        checkpoints = list(checkpoint_dir.glob("*_checkpoint.json"))
        if not checkpoints:
            return None
        
        # Get the most recent checkpoint
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        return str(latest)
    
    def load_checkpoint(self) -> bool:
        """Load checkpoint data"""
        if not self.checkpoint_file:
            self.checkpoint_file = self.find_latest_checkpoint()
        
        if not self.checkpoint_file or not Path(self.checkpoint_file).exists():
            return False
        
        try:
            with open(self.checkpoint_file, 'r') as f:
                self.checkpoint_data = json.load(f)
            
            # Parse start time
            if 'started_at' in self.checkpoint_data:
                self.start_time = datetime.fromisoformat(self.checkpoint_data['started_at'])
            
            return True
        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            return False
    
    def get_database_stats(self) -> Dict:
        """Get current database statistics"""
        if not self.db_client:
            return {}
        
        try:
            stats = self.db_client.get_subscription_stats()
            
            # Get recent activity
            recent_activity = []
            users = self.db_client.get_whitelisted_users(limit=10)
            for user in users:
                activity = self.db_client.get_user_activity(
                    user.telegram_id, 
                    limit=1, 
                    action_filter='user_whitelisted'
                )
                if activity:
                    recent_activity.append({
                        'telegram_id': user.telegram_id,
                        'username': user.username,
                        'timestamp': activity[0].get('timestamp')
                    })
            
            return {
                'total_users': stats.get('total_users', 0),
                'whitelisted_users': stats.get('whitelisted_users', 0),
                'recent_activity': recent_activity
            }
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_progress(self) -> Dict:
        """Calculate migration progress"""
        if not self.checkpoint_data:
            return {}
        
        stats = self.checkpoint_data.get('statistics', {})
        total = self.checkpoint_data.get('total_users', 0)
        processed = stats.get('success_count', 0) + stats.get('failure_count', 0) + stats.get('skip_count', 0)
        
        if total == 0:
            return {}
        
        # Calculate timing
        elapsed = None
        eta = None
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            if processed > 0:
                rate = processed / elapsed.total_seconds()
                remaining = total - processed
                eta_seconds = remaining / rate if rate > 0 else 0
                eta = timedelta(seconds=int(eta_seconds))
        
        return {
            'total': total,
            'processed': processed,
            'success': stats.get('success_count', 0),
            'failed': stats.get('failure_count', 0),
            'skipped': stats.get('skip_count', 0),
            'retried': stats.get('retry_count', 0),
            'percentage': (processed / total * 100) if total > 0 else 0,
            'elapsed': str(elapsed).split('.')[0] if elapsed else 'N/A',
            'eta': str(eta).split('.')[0] if eta else 'N/A',
            'rate': f"{processed / elapsed.total_seconds():.1f}/s" if elapsed and elapsed.total_seconds() > 0 else 'N/A'
        }
    
    def get_failed_users(self) -> List[Dict]:
        """Get list of failed users"""
        if not self.checkpoint_data:
            return []
        
        return self.checkpoint_data.get('failed_users', [])[:10]  # Last 10
    
    def print_dashboard(self):
        """Print text-based dashboard"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print("MIGRATION MONITORING DASHBOARD")
        print("=" * 80)
        
        # Checkpoint info
        if self.checkpoint_data:
            print(f"\nMigration ID: {self.checkpoint_data.get('migration_id', 'Unknown')}")
            print(f"Status: {self.checkpoint_data.get('status', 'Unknown').upper()}")
            print(f"Started: {self.checkpoint_data.get('started_at', 'Unknown')}")
            print(f"Last Update: {self.checkpoint_data.get('last_updated', 'Unknown')}")
            
            # Configuration
            config = self.checkpoint_data.get('configuration', {})
            print(f"\nConfiguration:")
            print(f"  Batch Size: {config.get('batch_size', 'N/A')}")
            print(f"  Dry Run: {config.get('dry_run', False)}")
            print(f"  Source: {config.get('source', 'N/A')}")
            
            # Progress
            progress = self.calculate_progress()
            if progress:
                print(f"\nProgress:")
                print(f"  Total Users: {progress['total']}")
                print(f"  Processed: {progress['processed']} ({progress['percentage']:.1f}%)")
                print(f"  Success: {progress['success']}")
                print(f"  Failed: {progress['failed']}")
                print(f"  Skipped: {progress['skipped']}")
                print(f"  Processing Rate: {progress['rate']}")
                print(f"  Elapsed Time: {progress['elapsed']}")
                print(f"  ETA: {progress['eta']}")
                
                # Progress bar
                bar_width = 50
                filled = int(bar_width * progress['percentage'] / 100)
                bar = '█' * filled + '░' * (bar_width - filled)
                print(f"\n  [{bar}] {progress['percentage']:.1f}%")
            
            # Failed users
            failed = self.get_failed_users()
            if failed:
                print(f"\nFailed Users (last {len(failed)}):")
                for user in failed:
                    print(f"  - ID: {user['telegram_id']}, Error: {user.get('error', 'Unknown')}")
        else:
            print("\nNo active migration found.")
        
        # Database stats
        if self.db_client:
            db_stats = self.get_database_stats()
            if db_stats and 'error' not in db_stats:
                print(f"\nDatabase Statistics:")
                print(f"  Total Users: {db_stats.get('total_users', 0)}")
                print(f"  Whitelisted Users: {db_stats.get('whitelisted_users', 0)}")
                
                if db_stats.get('recent_activity'):
                    print(f"\nRecent Whitelisted (last {len(db_stats['recent_activity'])}):")
                    for activity in db_stats['recent_activity'][:5]:
                        username = activity.get('username', 'N/A')
                        print(f"  - {activity['telegram_id']} (@{username})")
        
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit")
        print("Refreshing every {} seconds...".format(self.refresh_interval))
    
    def run_curses_dashboard(self, stdscr):
        """Run interactive curses dashboard"""
        curses.curs_set(0)  # Hide cursor
        stdscr.nodelay(1)    # Non-blocking input
        stdscr.timeout(int(self.refresh_interval * 1000))
        
        while True:
            try:
                # Check for exit key
                key = stdscr.getch()
                if key == ord('q') or key == ord('Q'):
                    break
                
                # Reload checkpoint
                self.load_checkpoint()
                
                # Clear screen
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                
                # Title
                title = "MIGRATION MONITORING DASHBOARD"
                stdscr.attron(curses.A_BOLD)
                stdscr.addstr(0, (width - len(title)) // 2, title)
                stdscr.attroff(curses.A_BOLD)
                
                row = 2
                
                if self.checkpoint_data:
                    # Basic info
                    stdscr.addstr(row, 0, f"Migration ID: {self.checkpoint_data.get('migration_id', 'Unknown')}")
                    row += 1
                    
                    status = self.checkpoint_data.get('status', 'Unknown').upper()
                    if status == 'IN_PROGRESS':
                        stdscr.attron(curses.color_pair(1))  # Green
                    elif status == 'FAILED':
                        stdscr.attron(curses.color_pair(2))  # Red
                    stdscr.addstr(row, 0, f"Status: {status}")
                    stdscr.attroff(curses.color_pair(1))
                    stdscr.attroff(curses.color_pair(2))
                    row += 2
                    
                    # Progress
                    progress = self.calculate_progress()
                    if progress:
                        stdscr.addstr(row, 0, "Progress:")
                        row += 1
                        
                        # Stats
                        stats_lines = [
                            f"  Total: {progress['total']} | Processed: {progress['processed']} ({progress['percentage']:.1f}%)",
                            f"  Success: {progress['success']} | Failed: {progress['failed']} | Skipped: {progress['skipped']}",
                            f"  Rate: {progress['rate']} | Elapsed: {progress['elapsed']} | ETA: {progress['eta']}"
                        ]
                        
                        for line in stats_lines:
                            if row < height - 2:
                                stdscr.addstr(row, 0, line[:width-1])
                                row += 1
                        
                        # Progress bar
                        row += 1
                        if row < height - 2:
                            bar_width = min(50, width - 10)
                            filled = int(bar_width * progress['percentage'] / 100)
                            bar = '█' * filled + '░' * (bar_width - filled)
                            stdscr.addstr(row, 2, f"[{bar}] {progress['percentage']:.1f}%")
                            row += 2
                    
                    # Failed users
                    failed = self.get_failed_users()
                    if failed and row < height - 5:
                        stdscr.addstr(row, 0, f"Failed Users (last {len(failed)}):")
                        row += 1
                        for user in failed[:3]:  # Show only 3 in curses mode
                            if row < height - 2:
                                error_msg = f"  ID: {user['telegram_id']}, Error: {user.get('error', 'Unknown')}"
                                stdscr.addstr(row, 0, error_msg[:width-1])
                                row += 1
                else:
                    stdscr.addstr(row, 0, "No active migration found.")
                    row += 1
                    stdscr.addstr(row, 0, f"Checkpoint file: {self.checkpoint_file or 'Not found'}")
                
                # Footer
                footer = "Press 'q' to quit | Refreshing every {} seconds".format(self.refresh_interval)
                stdscr.addstr(height - 1, 0, footer[:width-1])
                
                stdscr.refresh()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                # Fall back to text mode on error
                print(f"Curses error: {e}")
                break
    
    async def run_async_monitor(self):
        """Run asynchronous monitoring loop"""
        while True:
            try:
                self.load_checkpoint()
                self.print_dashboard()
                await asyncio.sleep(self.refresh_interval)
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")
                break
    
    def run(self, mode='text'):
        """Run the monitor in specified mode"""
        if mode == 'curses':
            try:
                # Initialize colors
                curses.wrapper(self.run_curses_dashboard)
            except Exception as e:
                print(f"Curses mode failed: {e}")
                print("Falling back to text mode...")
                mode = 'text'
        
        if mode == 'text':
            try:
                asyncio.run(self.run_async_monitor())
            except KeyboardInterrupt:
                print("\nMonitoring stopped.")

def send_alert(message: str, webhook_url: Optional[str] = None):
    """Send alert notification (Discord/Slack webhook)"""
    if not webhook_url:
        webhook_url = os.getenv('ALERT_WEBHOOK_URL')
    
    if not webhook_url:
        return
    
    try:
        import requests
        
        # Detect webhook type
        if 'discord' in webhook_url:
            # Discord webhook
            payload = {'content': f"🚨 **Migration Alert**\n{message}"}
        elif 'slack' in webhook_url:
            # Slack webhook
            payload = {'text': f"🚨 *Migration Alert*\n{message}"}
        else:
            # Generic JSON
            payload = {'message': message}
        
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send alert: {e}")

def check_migration_health(checkpoint_file: str) -> Tuple[bool, str]:
    """Check migration health and return status"""
    try:
        with open(checkpoint_file, 'r') as f:
            data = json.load(f)
        
        status = data.get('status', 'unknown')
        stats = data.get('statistics', {})
        
        # Check failure rate
        total_processed = stats.get('success_count', 0) + stats.get('failure_count', 0)
        if total_processed > 0:
            failure_rate = stats.get('failure_count', 0) / total_processed * 100
            
            if failure_rate > 10:
                return False, f"High failure rate: {failure_rate:.1f}%"
        
        # Check if stuck
        last_update = data.get('last_updated')
        if last_update:
            last_update_time = datetime.fromisoformat(last_update)
            time_since_update = datetime.now() - last_update_time
            
            if time_since_update > timedelta(minutes=5) and status == 'in_progress':
                return False, f"Migration appears stuck (no update for {time_since_update})"
        
        # Check status
        if status == 'failed':
            return False, "Migration has failed status"
        
        return True, "Migration healthy"
        
    except Exception as e:
        return False, f"Cannot check health: {e}"

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Monitor migration progress')
    parser.add_argument('--checkpoint', help='Path to checkpoint file')
    parser.add_argument('--mode', choices=['text', 'curses'], default='text',
                       help='Display mode (text or curses)')
    parser.add_argument('--refresh', type=float, default=1.0,
                       help='Refresh interval in seconds')
    parser.add_argument('--check-health', action='store_true',
                       help='Check migration health and exit')
    parser.add_argument('--alert-webhook', help='Webhook URL for alerts')
    
    args = parser.parse_args()
    
    monitor = MigrationMonitor(checkpoint_file=args.checkpoint)
    monitor.refresh_interval = args.refresh
    
    if args.check_health:
        # Health check mode
        if not monitor.load_checkpoint():
            print("No checkpoint found")
            sys.exit(1)
        
        healthy, message = check_migration_health(monitor.checkpoint_file)
        print(f"Health Check: {'PASS' if healthy else 'FAIL'}")
        print(f"Message: {message}")
        
        if not healthy and args.alert_webhook:
            send_alert(message, args.alert_webhook)
        
        sys.exit(0 if healthy else 1)
    else:
        # Monitoring mode
        if not monitor.load_checkpoint():
            print("No active migration checkpoint found.")
            print("\nTo start monitoring, either:")
            print("1. Run a migration first")
            print("2. Specify a checkpoint file with --checkpoint")
            sys.exit(1)
        
        monitor.run(mode=args.mode)

if __name__ == "__main__":
    main()
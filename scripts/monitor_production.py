#!/usr/bin/env python3
"""
Production Monitoring Script for Telegram Subscription Bot
Provides health checks, status verification, and alert notifications
"""

import asyncio
import sys
import os
import json
import logging
import argparse
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.supabase_client import SupabaseClient

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitoring.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"

@dataclass
class HealthCheckResult:
    """Health check result structure"""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: float
    metadata: Dict = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        if self.metadata is None:
            self.metadata = {}

class ProductionMonitor:
    """Main monitoring class for production environment"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize monitor with configuration"""
        self.config = self._load_config(config_path)
        self.alerts_enabled = self.config.get('alerts_enabled', True)
        self.alert_threshold = self.config.get('alert_threshold', 3)
        self.failure_counts = {}
        self.last_alert_times = {}
        self.health_history = []
        
        # Initialize components
        self.bot = None
        self.db_client = None
        self.session = None
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Load configuration from file or environment"""
        config = {
            'bot_token': os.getenv('BOT_TOKEN'),
            'group_id': os.getenv('GROUP_ID'),
            'admin_user_id': os.getenv('ADMIN_USER_ID'),
            'supabase_url': os.getenv('SUPABASE_URL'),
            'supabase_key': os.getenv('SUPABASE_SERVICE_KEY'),
            'webhook_base_url': os.getenv('WEBHOOK_BASE_URL', ''),
            'webhook_port': int(os.getenv('WEBHOOK_PORT', '8080')),
            'admin_dashboard_port': int(os.getenv('ADMIN_DASHBOARD_PORT', '8081')),
            'airwallex_client_id': os.getenv('AIRWALLEX_CLIENT_ID'),
            'alert_webhook_url': os.getenv('ALERT_WEBHOOK_URL'),  # Slack/Discord webhook
            'alert_telegram_chat_id': os.getenv('ALERT_TELEGRAM_CHAT_ID'),
        }
        
        # Load from config file if provided
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                config.update(file_config)
        
        return config
    
    async def initialize(self):
        """Initialize monitoring components"""
        try:
            # Initialize bot
            if self.config.get('bot_token'):
                self.bot = Bot(token=self.config['bot_token'])
                logger.info("Bot client initialized")
            
            # Initialize database client
            if self.config.get('supabase_url') and self.config.get('supabase_key'):
                self.db_client = SupabaseClient(
                    self.config['supabase_url'],
                    self.config['supabase_key']
                )
                logger.info("Database client initialized")
            
            # Initialize HTTP session
            self.session = aiohttp.ClientSession()
            logger.info("HTTP session initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitor: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        if self.bot:
            await self.bot.session.close()
        if self.session:
            await self.session.close()
    
    async def check_bot_health(self) -> HealthCheckResult:
        """Check Telegram bot responsiveness"""
        start_time = time.time()
        
        try:
            if not self.bot:
                return HealthCheckResult(
                    component="telegram_bot",
                    status=HealthStatus.CRITICAL,
                    message="Bot not configured",
                    response_time_ms=0
                )
            
            # Get bot info
            bot_info = await self.bot.get_me()
            response_time = (time.time() - start_time) * 1000
            
            # Try to get webhook info
            webhook_info = await self.bot.get_webhook_info()
            
            metadata = {
                'bot_username': bot_info.username,
                'bot_id': bot_info.id,
                'webhook_url': webhook_info.url if webhook_info else None,
                'pending_updates': webhook_info.pending_update_count if webhook_info else 0
            }
            
            # Determine health status
            if response_time > 2000:
                status = HealthStatus.DEGRADED
                message = f"Bot responding slowly ({response_time:.0f}ms)"
            elif webhook_info and webhook_info.pending_update_count > 100:
                status = HealthStatus.DEGRADED
                message = f"High pending updates: {webhook_info.pending_update_count}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Bot @{bot_info.username} is responsive"
            
            return HealthCheckResult(
                component="telegram_bot",
                status=status,
                message=message,
                response_time_ms=response_time,
                metadata=metadata
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="telegram_bot",
                status=HealthStatus.CRITICAL,
                message=f"Bot check failed: {str(e)}",
                response_time_ms=response_time,
                metadata={'error': str(e)}
            )
    
    async def check_database_health(self) -> HealthCheckResult:
        """Check database connectivity and performance"""
        start_time = time.time()
        
        try:
            if not self.db_client:
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.CRITICAL,
                    message="Database not configured",
                    response_time_ms=0
                )
            
            # Test query
            test_query = await asyncio.wait_for(
                self._test_database_query(),
                timeout=5.0
            )
            response_time = (time.time() - start_time) * 1000
            
            if not test_query['success']:
                return HealthCheckResult(
                    component="database",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Database query failed: {test_query.get('error')}",
                    response_time_ms=response_time
                )
            
            # Get database statistics
            stats = test_query.get('stats', {})
            metadata = {
                'total_users': stats.get('users', 0),
                'active_subscriptions': stats.get('active_subs', 0),
                'tables_accessible': test_query.get('tables_checked', [])
            }
            
            # Determine health status
            if response_time > 1000:
                status = HealthStatus.DEGRADED
                message = f"Database responding slowly ({response_time:.0f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database operational ({stats.get('users', 0)} users)"
            
            return HealthCheckResult(
                component="database",
                status=status,
                message=message,
                response_time_ms=response_time,
                metadata=metadata
            )
            
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="database",
                status=HealthStatus.CRITICAL,
                message="Database query timeout (>5s)",
                response_time_ms=response_time
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="database",
                status=HealthStatus.CRITICAL,
                message=f"Database check failed: {str(e)}",
                response_time_ms=response_time,
                metadata={'error': str(e)}
            )
    
    async def _test_database_query(self) -> Dict:
        """Execute test database queries"""
        try:
            result = {'success': True, 'tables_checked': [], 'stats': {}}
            
            # Test users table
            users = self.db_client.client.table('users').select('id').limit(1).execute()
            result['tables_checked'].append('users')
            
            # Get user count
            user_count = self.db_client.client.table('users').select('id', count='exact').execute()
            result['stats']['users'] = user_count.count if hasattr(user_count, 'count') else 0
            
            # Test subscriptions table
            subs = self.db_client.client.table('subscriptions').select('id').limit(1).execute()
            result['tables_checked'].append('subscriptions')
            
            # Get active subscription count
            active_subs = self.db_client.client.table('subscriptions')\
                .select('id', count='exact')\
                .eq('status', 'active')\
                .execute()
            result['stats']['active_subs'] = active_subs.count if hasattr(active_subs, 'count') else 0
            
            # Test payments table
            payments = self.db_client.client.table('payments').select('id').limit(1).execute()
            result['tables_checked'].append('payments')
            
            return result
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def check_webhook_health(self) -> HealthCheckResult:
        """Check webhook endpoint availability"""
        if not self.config.get('webhook_base_url'):
            return HealthCheckResult(
                component="webhook",
                status=HealthStatus.DEGRADED,
                message="Webhook not configured",
                response_time_ms=0
            )
        
        start_time = time.time()
        webhook_url = f"{self.config['webhook_base_url']}/health"
        
        try:
            async with self.session.get(webhook_url, timeout=5) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    data = await response.json()
                    return HealthCheckResult(
                        component="webhook",
                        status=HealthStatus.HEALTHY,
                        message=f"Webhook endpoint responsive",
                        response_time_ms=response_time,
                        metadata=data
                    )
                else:
                    return HealthCheckResult(
                        component="webhook",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Webhook returned status {response.status}",
                        response_time_ms=response_time
                    )
                    
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="webhook",
                status=HealthStatus.CRITICAL,
                message="Webhook timeout (>5s)",
                response_time_ms=response_time
            )
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="webhook",
                status=HealthStatus.UNHEALTHY,
                message=f"Webhook check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_admin_dashboard(self) -> HealthCheckResult:
        """Check admin dashboard availability"""
        start_time = time.time()
        
        if not self.config.get('webhook_base_url'):
            dashboard_url = f"http://localhost:{self.config.get('admin_dashboard_port', 8081)}/"
        else:
            # In production, use the base URL
            dashboard_url = f"{self.config['webhook_base_url']}:{self.config.get('admin_dashboard_port', 8081)}/"
        
        try:
            async with self.session.get(dashboard_url, timeout=5) as response:
                response_time = (time.time() - start_time) * 1000
                
                if response.status == 200:
                    return HealthCheckResult(
                        component="admin_dashboard",
                        status=HealthStatus.HEALTHY,
                        message="Admin dashboard accessible",
                        response_time_ms=response_time
                    )
                else:
                    return HealthCheckResult(
                        component="admin_dashboard",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Dashboard returned status {response.status}",
                        response_time_ms=response_time
                    )
                    
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="admin_dashboard",
                status=HealthStatus.DEGRADED,
                message=f"Dashboard check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def check_payment_system(self) -> HealthCheckResult:
        """Check payment system availability"""
        start_time = time.time()
        
        try:
            # Check Airwallex API availability
            if self.config.get('airwallex_client_id'):
                airwallex_url = "https://api.airwallex.com/api/v1/ping"
                async with self.session.get(airwallex_url, timeout=5) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status in [200, 401]:  # 401 expected without auth
                        return HealthCheckResult(
                            component="payment_system",
                            status=HealthStatus.HEALTHY,
                            message="Payment API accessible",
                            response_time_ms=response_time
                        )
            
            # If no Airwallex, just check Stars is configured
            if self.bot:
                return HealthCheckResult(
                    component="payment_system",
                    status=HealthStatus.HEALTHY,
                    message="Stars payment ready",
                    response_time_ms=(time.time() - start_time) * 1000
                )
            
            return HealthCheckResult(
                component="payment_system",
                status=HealthStatus.DEGRADED,
                message="Payment system not fully configured",
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                component="payment_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Payment check failed: {str(e)}",
                response_time_ms=response_time
            )
    
    async def run_health_checks(self) -> List[HealthCheckResult]:
        """Run all health checks"""
        checks = [
            self.check_bot_health(),
            self.check_database_health(),
            self.check_webhook_health(),
            self.check_admin_dashboard(),
            self.check_payment_system()
        ]
        
        results = await asyncio.gather(*checks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                component_name = ['bot', 'database', 'webhook', 'admin', 'payment'][i]
                processed_results.append(HealthCheckResult(
                    component=component_name,
                    status=HealthStatus.CRITICAL,
                    message=f"Check failed with exception: {str(result)}",
                    response_time_ms=0
                ))
            else:
                processed_results.append(result)
        
        # Store in history
        self.health_history.append({
            'timestamp': datetime.utcnow(),
            'results': processed_results
        })
        
        # Keep only last 100 checks
        if len(self.health_history) > 100:
            self.health_history = self.health_history[-100:]
        
        return processed_results
    
    async def send_alert(self, message: str, severity: str = "WARNING"):
        """Send alert notification"""
        if not self.alerts_enabled:
            return
        
        alert_message = f"[{severity}] {datetime.utcnow().isoformat()} - {message}"
        
        # Send to Telegram if configured
        if self.bot and self.config.get('alert_telegram_chat_id'):
            try:
                await self.bot.send_message(
                    chat_id=self.config['alert_telegram_chat_id'],
                    text=f"🚨 *System Alert*\n\n{alert_message}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")
        
        # Send to webhook (Slack/Discord) if configured
        if self.config.get('alert_webhook_url'):
            try:
                payload = {
                    'text': alert_message,
                    'username': 'Production Monitor',
                    'icon_emoji': ':warning:' if severity == 'WARNING' else ':fire:'
                }
                async with self.session.post(
                    self.config['alert_webhook_url'],
                    json=payload
                ) as response:
                    if response.status != 200:
                        logger.error(f"Alert webhook returned {response.status}")
            except Exception as e:
                logger.error(f"Failed to send webhook alert: {e}")
        
        logger.warning(alert_message)
    
    async def process_health_results(self, results: List[HealthCheckResult]):
        """Process health check results and send alerts if needed"""
        critical_components = []
        unhealthy_components = []
        degraded_components = []
        
        for result in results:
            # Track failure counts
            if result.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                self.failure_counts[result.component] = self.failure_counts.get(result.component, 0) + 1
            else:
                self.failure_counts[result.component] = 0
            
            # Categorize by severity
            if result.status == HealthStatus.CRITICAL:
                critical_components.append(result)
            elif result.status == HealthStatus.UNHEALTHY:
                unhealthy_components.append(result)
            elif result.status == HealthStatus.DEGRADED:
                degraded_components.append(result)
        
        # Send alerts based on severity
        for component in critical_components:
            if self.failure_counts[component.component] >= self.alert_threshold:
                last_alert = self.last_alert_times.get(component.component, datetime.min)
                if datetime.utcnow() - last_alert > timedelta(minutes=15):
                    await self.send_alert(
                        f"CRITICAL: {component.component} - {component.message}",
                        severity="CRITICAL"
                    )
                    self.last_alert_times[component.component] = datetime.utcnow()
        
        for component in unhealthy_components:
            if self.failure_counts[component.component] >= self.alert_threshold * 2:
                last_alert = self.last_alert_times.get(component.component, datetime.min)
                if datetime.utcnow() - last_alert > timedelta(minutes=30):
                    await self.send_alert(
                        f"UNHEALTHY: {component.component} - {component.message}",
                        severity="WARNING"
                    )
                    self.last_alert_times[component.component] = datetime.utcnow()
    
    def generate_report(self, results: List[HealthCheckResult]) -> str:
        """Generate human-readable health report"""
        report = []
        report.append("=" * 60)
        report.append(f"Production Health Report - {datetime.utcnow().isoformat()}")
        report.append("=" * 60)
        
        overall_status = HealthStatus.HEALTHY
        total_response_time = 0
        
        for result in results:
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.DEGRADED: "⚠️",
                HealthStatus.UNHEALTHY: "❌",
                HealthStatus.CRITICAL: "🔥"
            }
            
            report.append(f"\n{status_emoji[result.status]} {result.component.upper()}")
            report.append(f"   Status: {result.status.value}")
            report.append(f"   Message: {result.message}")
            report.append(f"   Response Time: {result.response_time_ms:.0f}ms")
            
            if result.metadata:
                report.append(f"   Details: {json.dumps(result.metadata, indent=6)}")
            
            total_response_time += result.response_time_ms
            
            # Update overall status
            if result.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
            elif result.status == HealthStatus.UNHEALTHY and overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
        
        report.append("\n" + "=" * 60)
        report.append(f"Overall Status: {overall_status.value.upper()}")
        report.append(f"Total Response Time: {total_response_time:.0f}ms")
        report.append(f"Average Response Time: {total_response_time/len(results):.0f}ms")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    async def continuous_monitoring(self, interval_seconds: int = 60):
        """Run continuous monitoring loop"""
        logger.info(f"Starting continuous monitoring (interval: {interval_seconds}s)")
        
        while True:
            try:
                results = await self.run_health_checks()
                await self.process_health_results(results)
                
                # Log summary
                critical_count = sum(1 for r in results if r.status == HealthStatus.CRITICAL)
                unhealthy_count = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
                
                if critical_count > 0 or unhealthy_count > 0:
                    logger.warning(f"Health check: {critical_count} critical, {unhealthy_count} unhealthy")
                else:
                    logger.info("All systems operational")
                
                await asyncio.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(interval_seconds)

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Production monitoring for Telegram bot')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--check', choices=['all', 'bot', 'database', 'webhook', 'admin', 'payment'],
                       default='all', help='Specific component to check')
    parser.add_argument('--continuous', action='store_true', help='Run continuous monitoring')
    parser.add_argument('--interval', type=int, default=60, help='Monitoring interval in seconds')
    parser.add_argument('--quick-check', action='store_true', help='Run quick health check')
    parser.add_argument('--full-check', action='store_true', help='Run comprehensive health check')
    parser.add_argument('--no-alerts', action='store_true', help='Disable alert notifications')
    
    args = parser.parse_args()
    
    # Create monitor instance
    monitor = ProductionMonitor(config_path=args.config)
    
    if args.no_alerts:
        monitor.alerts_enabled = False
    
    try:
        await monitor.initialize()
        
        if args.continuous:
            await monitor.continuous_monitoring(args.interval)
        else:
            # Run specific or all checks
            if args.check == 'bot':
                results = [await monitor.check_bot_health()]
            elif args.check == 'database':
                results = [await monitor.check_database_health()]
            elif args.check == 'webhook':
                results = [await monitor.check_webhook_health()]
            elif args.check == 'admin':
                results = [await monitor.check_admin_dashboard()]
            elif args.check == 'payment':
                results = [await monitor.check_payment_system()]
            else:
                results = await monitor.run_health_checks()
            
            # Process and display results
            await monitor.process_health_results(results)
            report = monitor.generate_report(results)
            print(report)
            
            # Exit code based on health
            has_critical = any(r.status == HealthStatus.CRITICAL for r in results)
            has_unhealthy = any(r.status == HealthStatus.UNHEALTHY for r in results)
            
            if has_critical:
                sys.exit(2)
            elif has_unhealthy:
                sys.exit(1)
            else:
                sys.exit(0)
    
    finally:
        await monitor.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
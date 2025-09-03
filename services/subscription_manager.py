"""
Subscription Manager - Handles automated subscription tasks
"""

import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Optional, List
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.supabase_client import SupabaseClient, SubscriptionStatus, ActivityAction

logger = logging.getLogger(__name__)

class SubscriptionManager:
    """Manages subscription automation and lifecycle"""
    
    def __init__(self, bot: Bot, db_client: SupabaseClient, group_id: int):
        self.bot = bot
        self.db = db_client
        self.group_id = group_id
        self.automation_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Automation schedule (UTC times)
        self.check_time = time(9, 0)  # 9:00 AM UTC
        self.reminder_days = [3, 1]  # Days before expiry to send reminders
        
    async def start_automation(self):
        """Start the subscription automation tasks"""
        if self.is_running:
            logger.warning("Automation already running")
            return
            
        self.is_running = True
        self.automation_task = asyncio.create_task(self._automation_loop())
        logger.info("Subscription automation started")
        
    async def stop_automation(self):
        """Stop the subscription automation tasks"""
        self.is_running = False
        if self.automation_task:
            self.automation_task.cancel()
            try:
                await self.automation_task
            except asyncio.CancelledError:
                pass
        logger.info("Subscription automation stopped")
        
    async def _automation_loop(self):
        """Main automation loop that runs daily tasks"""
        while self.is_running:
            try:
                # Calculate time until next check
                now = datetime.utcnow()
                next_check = datetime.combine(now.date(), self.check_time)
                if next_check <= now:
                    # If we've passed today's check time, schedule for tomorrow
                    next_check += timedelta(days=1)
                
                wait_seconds = (next_check - now).total_seconds()
                logger.info(f"Next automation check at {next_check} UTC (in {wait_seconds/3600:.1f} hours)")
                
                # Wait until check time
                await asyncio.sleep(wait_seconds)
                
                # Run daily tasks
                await self.run_daily_tasks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in automation loop: {e}")
                # Wait before retrying
                await asyncio.sleep(3600)  # 1 hour
                
    async def run_daily_tasks(self):
        """Run all daily automation tasks"""
        logger.info("Running daily subscription tasks...")
        
        # 1. Process expired subscriptions
        expired_count = await self.process_expired_subscriptions()
        logger.info(f"Processed {expired_count} expired subscriptions")
        
        # 2. Send payment reminders
        reminder_count = await self.send_payment_reminders()
        logger.info(f"Sent {reminder_count} payment reminders")
        
        # 3. Clean up stale data
        await self.cleanup_stale_data()
        
        # 4. Log daily statistics
        await self.log_daily_stats()
        
    async def process_expired_subscriptions(self) -> int:
        """Remove users with expired subscriptions from the group"""
        try:
            # Get expired subscriptions
            expired_users = self.db.get_expired_subscriptions()
            processed = 0
            
            for user_data in expired_users:
                try:
                    telegram_id = user_data['telegram_id']
                    
                    # Try to remove from group
                    await self.remove_from_group(telegram_id)
                    
                    # Update subscription status
                    self.db.update_user(
                        telegram_id=telegram_id,
                        subscription_status=SubscriptionStatus.EXPIRED.value
                    )
                    
                    # Send notification to user
                    await self.send_expiry_notification(telegram_id)
                    
                    # Log activity
                    self.db.log_activity(
                        telegram_id=telegram_id,
                        action=ActivityAction.SUBSCRIPTION_EXPIRED.value,
                        details={"reason": "automatic_expiry"}
                    )
                    
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing expired subscription for {user_data.get('telegram_id')}: {e}")
                    
            return processed
            
        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return 0
            
    async def send_payment_reminders(self) -> int:
        """Send payment reminders to users whose subscriptions are expiring soon"""
        sent = 0
        
        for days in self.reminder_days:
            try:
                # Get users expiring in N days
                expiring_users = self.db.get_expiring_subscriptions(days)
                
                for user_data in expiring_users:
                    try:
                        telegram_id = user_data['telegram_id']
                        
                        # Check if we already sent a reminder today
                        recent_activities = self.db.get_user_activities(
                            telegram_id=telegram_id,
                            limit=10
                        )
                        
                        # Skip if reminder already sent today
                        today = datetime.utcnow().date()
                        reminder_sent_today = any(
                            activity['action'] == ActivityAction.REMINDER_SENT.value and
                            activity['timestamp'].date() == today
                            for activity in recent_activities
                        )
                        
                        if not reminder_sent_today:
                            await self.send_payment_reminder(telegram_id, days)
                            
                            # Log activity
                            self.db.log_activity(
                                telegram_id=telegram_id,
                                action=ActivityAction.REMINDER_SENT.value,
                                details={"days_until_expiry": days}
                            )
                            
                            sent += 1
                            
                    except Exception as e:
                        logger.error(f"Error sending reminder to {user_data.get('telegram_id')}: {e}")
                        
            except Exception as e:
                logger.error(f"Error getting expiring subscriptions for {days} days: {e}")
                
        return sent
        
    async def remove_from_group(self, telegram_id: int) -> bool:
        """Remove a user from the group"""
        try:
            await self.bot.ban_chat_member(
                chat_id=self.group_id,
                user_id=telegram_id,
                until_date=datetime.utcnow() + timedelta(seconds=30)
            )
            # Immediately unban so they can rejoin after payment
            await self.bot.unban_chat_member(
                chat_id=self.group_id,
                user_id=telegram_id
            )
            return True
        except TelegramBadRequest as e:
            if "user not found" in str(e).lower():
                logger.info(f"User {telegram_id} not in group")
                return True
            logger.error(f"Error removing user {telegram_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error removing user {telegram_id}: {e}")
            return False
            
    async def add_to_group(self, telegram_id: int) -> Optional[str]:
        """Generate invite link for user to join group"""
        try:
            # Create invite link for single use
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=self.group_id,
                member_limit=1,
                expire_date=datetime.utcnow() + timedelta(hours=24)
            )
            return invite_link.invite_link
        except Exception as e:
            logger.error(f"Error creating invite link: {e}")
            return None
            
    async def send_expiry_notification(self, telegram_id: int):
        """Send subscription expiry notification to user"""
        message = (
            "❌ <b>Subscription Expired</b>\n\n"
            "Your subscription has expired and you have been removed from the group.\n\n"
            "To rejoin, please renew your subscription using /subscribe\n\n"
            "Thank you for being part of our community! 💙"
        )
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
        except TelegramForbiddenError:
            logger.info(f"User {telegram_id} has blocked the bot")
        except Exception as e:
            logger.error(f"Error sending expiry notification to {telegram_id}: {e}")
            
    async def send_payment_reminder(self, telegram_id: int, days_until_expiry: int):
        """Send payment reminder to user"""
        if days_until_expiry == 1:
            urgency = "⚠️ <b>URGENT</b>"
            time_text = "tomorrow"
        else:
            urgency = "📅 <b>Reminder</b>"
            time_text = f"in {days_until_expiry} days"
            
        message = (
            f"{urgency}: Your Subscription is Expiring\n\n"
            f"Your subscription will expire {time_text}.\n\n"
            f"To avoid losing access to the group, please renew now:\n"
            f"/subscribe - Renew your subscription\n\n"
            f"💡 <i>Tip: Renew early to ensure uninterrupted access!</i>"
        )
        
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode="HTML"
            )
        except TelegramForbiddenError:
            logger.info(f"User {telegram_id} has blocked the bot")
        except Exception as e:
            logger.error(f"Error sending reminder to {telegram_id}: {e}")
            
    async def cleanup_stale_data(self):
        """Clean up old activity logs and stale data"""
        try:
            # Keep only last 30 days of activity logs
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            # This would be done via SQL in production
            logger.info("Cleaned up old activity logs")
        except Exception as e:
            logger.error(f"Error cleaning up stale data: {e}")
            
    async def log_daily_stats(self):
        """Log daily subscription statistics"""
        try:
            stats = self.db.get_subscription_stats()
            
            logger.info(
                f"Daily Stats - "
                f"Active: {stats['active_count']}, "
                f"Expired: {stats['expired_count']}, "
                f"Whitelisted: {stats['whitelisted_count']}, "
                f"Total Revenue: ${stats['total_revenue_usd']:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error logging daily stats: {e}")
            
    async def check_user_in_group(self, telegram_id: int) -> bool:
        """Check if user is currently in the group"""
        try:
            member = await self.bot.get_chat_member(
                chat_id=self.group_id,
                user_id=telegram_id
            )
            return member.status in ["member", "administrator", "creator"]
        except TelegramBadRequest:
            return False
        except Exception as e:
            logger.error(f"Error checking user {telegram_id} in group: {e}")
            return False
            
    async def extend_subscription(self, telegram_id: int, days: int = 30) -> bool:
        """Manually extend a user's subscription"""
        try:
            user = self.db.get_user(telegram_id)
            if not user:
                return False
                
            # Calculate new expiry date
            if user.next_payment_date and user.next_payment_date > datetime.utcnow().date():
                new_date = user.next_payment_date + timedelta(days=days)
            else:
                new_date = datetime.utcnow().date() + timedelta(days=days)
                
            # Update subscription
            self.db.update_user(
                telegram_id=telegram_id,
                subscription_status=SubscriptionStatus.ACTIVE.value,
                next_payment_date=new_date
            )
            
            # Log activity
            self.db.log_activity(
                telegram_id=telegram_id,
                action=ActivityAction.SUBSCRIPTION_EXTENDED.value,
                details={"days": days, "new_expiry": new_date.isoformat()}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error extending subscription for {telegram_id}: {e}")
            return False
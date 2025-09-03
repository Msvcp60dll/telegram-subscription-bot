"""
Supabase Client for Telegram Subscription Bot
Handles all database operations for user subscriptions and activity logging
"""

import os
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# ENUMS FOR TYPE SAFETY
# ============================================

class SubscriptionStatus(Enum):
    """Subscription status options"""
    ACTIVE = "active"
    EXPIRED = "expired"
    WHITELISTED = "whitelisted"

class PaymentMethod(Enum):
    """Payment method options"""
    CARD = "card"
    STARS = "stars"
    WHITELISTED = "whitelisted"

class ActivityAction(Enum):
    """Activity log action types"""
    SUBSCRIPTION_STARTED = "subscription_started"
    SUBSCRIPTION_RENEWED = "subscription_renewed"
    SUBSCRIPTION_EXPIRED = "subscription_expired"
    SUBSCRIPTION_CANCELLED = "subscription_cancelled"
    PAYMENT_SUCCESSFUL = "payment_successful"
    PAYMENT_FAILED = "payment_failed"
    USER_JOINED_GROUP = "user_joined_group"
    USER_REMOVED_FROM_GROUP = "user_removed_from_group"
    USER_WHITELISTED = "user_whitelisted"
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"

# ============================================
# DATA CLASSES
# ============================================

@dataclass
class User:
    """User data model"""
    telegram_id: int
    username: Optional[str] = None
    subscription_status: str = SubscriptionStatus.EXPIRED.value
    payment_method: Optional[str] = None
    next_payment_date: Optional[date] = None
    airwallex_payment_id: Optional[str] = None
    stars_transaction_id: Optional[str] = None
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        if self.subscription_status == SubscriptionStatus.WHITELISTED.value:
            return True
        if self.subscription_status == SubscriptionStatus.ACTIVE.value:
            if self.next_payment_date:
                return self.next_payment_date >= date.today()
        return False

    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until subscription expires"""
        if self.next_payment_date and self.subscription_status == SubscriptionStatus.ACTIVE.value:
            delta = self.next_payment_date - date.today()
            return delta.days
        return None

# ============================================
# SUPABASE CLIENT CLASS
# ============================================

class SupabaseClient:
    """
    Supabase client for managing Telegram bot subscriptions
    
    Usage:
        client = SupabaseClient(
            url="https://dijdhqrxqwbctywejydj.supabase.co",
            key="your-service-role-key"
        )
    """
    
    def __init__(self, url: str, key: str, is_service_role: bool = True):
        """
        Initialize Supabase client
        
        Args:
            url: Supabase project URL
            key: Supabase API key (use service role key for bot operations)
            is_service_role: Whether using service role key (bypasses RLS)
        """
        self.url = url
        self.key = key
        self.is_service_role = is_service_role
        
        # Create client with proper configuration
        options = ClientOptions(
            postgrest_client_timeout=10,
            storage_client_timeout=10,
        )
        
        self.client: Client = create_client(url, key, options)
        logger.info(f"Supabase client initialized for {url}")
    
    # ============================================
    # USER OPERATIONS
    # ============================================
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """
        Get user by Telegram ID
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            response = self.client.table('users') \
                .select('*') \
                .eq('telegram_id', telegram_id) \
                .single() \
                .execute()
            
            if response.data:
                return User(**response.data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {telegram_id}: {e}")
            return None
    
    def create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        subscription_status: str = SubscriptionStatus.EXPIRED.value
    ) -> Optional[User]:
        """
        Create a new user
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            subscription_status: Initial subscription status
            
        Returns:
            Created User object if successful, None otherwise
        """
        try:
            data = {
                'telegram_id': telegram_id,
                'username': username,
                'subscription_status': subscription_status
            }
            
            response = self.client.table('users') \
                .insert(data) \
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Created user {telegram_id}")
                return User(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error creating user {telegram_id}: {e}")
            return None
    
    def update_user(
        self,
        telegram_id: int,
        **kwargs
    ) -> Optional[User]:
        """
        Update user data
        
        Args:
            telegram_id: Telegram user ID
            **kwargs: Fields to update (username, subscription_status, payment_method, etc.)
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            # Filter out None values and invalid fields
            valid_fields = {
                'username', 'subscription_status', 'payment_method',
                'next_payment_date', 'airwallex_payment_id', 'stars_transaction_id'
            }
            data = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
            
            if not data:
                logger.warning(f"No valid fields to update for user {telegram_id}")
                return self.get_user(telegram_id)
            
            response = self.client.table('users') \
                .update(data) \
                .eq('telegram_id', telegram_id) \
                .execute()
            
            if response.data and len(response.data) > 0:
                logger.info(f"Updated user {telegram_id}: {data}")
                return User(**response.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error updating user {telegram_id}: {e}")
            return None
    
    def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None
    ) -> Optional[User]:
        """
        Get existing user or create new one
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            
        Returns:
            User object if successful, None otherwise
        """
        user = self.get_user(telegram_id)
        if user:
            # Update username if changed
            if username and username != user.username:
                return self.update_user(telegram_id, username=username)
            return user
        else:
            return self.create_user(telegram_id, username)
    
    # ============================================
    # SUBSCRIPTION OPERATIONS
    # ============================================
    
    def activate_subscription(
        self,
        telegram_id: int,
        payment_method: str,
        transaction_id: Optional[str] = None,
        extend_from_today: bool = False
    ) -> Tuple[bool, Optional[date], str]:
        """
        Activate or extend user subscription
        
        Args:
            telegram_id: Telegram user ID
            payment_method: Payment method used (card/stars/whitelisted)
            transaction_id: Payment transaction ID
            extend_from_today: If True, always extend from today; if False, extend from current expiry
            
        Returns:
            Tuple of (success, new_expiry_date, message)
        """
        try:
            # Use the database function for atomic operation
            response = self.client.rpc(
                'extend_subscription',
                {
                    'p_telegram_id': telegram_id,
                    'p_payment_method': payment_method,
                    'p_transaction_id': transaction_id
                }
            ).execute()
            
            if response.data and len(response.data) > 0:
                result = response.data[0]
                # Convert string date to date object if needed
                expiry_date = None
                if result.get('new_expiry_date'):
                    expiry_date = datetime.fromisoformat(result['new_expiry_date']).date()
                
                return (
                    result.get('success', False),
                    expiry_date,
                    result.get('message', 'Unknown error')
                )
            
            return False, None, "Failed to activate subscription"
            
        except Exception as e:
            logger.error(f"Error activating subscription for {telegram_id}: {e}")
            # Fallback to manual update if RPC fails
            return self._manual_activate_subscription(
                telegram_id, payment_method, transaction_id, extend_from_today
            )
    
    def _manual_activate_subscription(
        self,
        telegram_id: int,
        payment_method: str,
        transaction_id: Optional[str] = None,
        extend_from_today: bool = False
    ) -> Tuple[bool, Optional[date], str]:
        """
        Manually activate subscription (fallback if RPC fails)
        """
        try:
            user = self.get_user(telegram_id)
            if not user:
                # Create user if doesn't exist
                user = self.create_user(telegram_id)
                if not user:
                    return False, None, "Failed to create user"
            
            # Calculate new expiry date
            if extend_from_today or not user.next_payment_date or user.next_payment_date < date.today():
                new_expiry = date.today() + timedelta(days=30)
            else:
                new_expiry = user.next_payment_date + timedelta(days=30)
            
            # Prepare update data
            update_data = {
                'subscription_status': SubscriptionStatus.ACTIVE.value,
                'payment_method': payment_method,
                'next_payment_date': new_expiry.isoformat()
            }
            
            if payment_method == PaymentMethod.CARD.value and transaction_id:
                update_data['airwallex_payment_id'] = transaction_id
            elif payment_method == PaymentMethod.STARS.value and transaction_id:
                update_data['stars_transaction_id'] = transaction_id
            
            # Update user
            updated_user = self.update_user(telegram_id, **update_data)
            
            if updated_user:
                # Log the activity
                self.log_activity(
                    telegram_id,
                    ActivityAction.PAYMENT_SUCCESSFUL.value,
                    {
                        'payment_method': payment_method,
                        'transaction_id': transaction_id,
                        'new_expiry_date': new_expiry.isoformat()
                    }
                )
                return True, new_expiry, "Subscription activated successfully"
            
            return False, None, "Failed to update user subscription"
            
        except Exception as e:
            logger.error(f"Error in manual subscription activation: {e}")
            return False, None, str(e)
    
    def cancel_subscription(self, telegram_id: int) -> bool:
        """
        Cancel user subscription (set to expire at end of period)
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.update_user(
                telegram_id,
                subscription_status=SubscriptionStatus.EXPIRED.value
            )
            
            if user:
                self.log_activity(
                    telegram_id,
                    ActivityAction.SUBSCRIPTION_CANCELLED.value,
                    {'cancelled_at': datetime.now().isoformat()}
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling subscription for {telegram_id}: {e}")
            return False
    
    def whitelist_user(self, telegram_id: int, username: Optional[str] = None) -> bool:
        """
        Add user to whitelist (permanent free access)
        
        Args:
            telegram_id: Telegram user ID
            username: Telegram username
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First ensure user exists
            user = self.get_or_create_user(telegram_id, username)
            if not user:
                return False
            
            # Update to whitelisted status
            updated_user = self.update_user(
                telegram_id,
                subscription_status=SubscriptionStatus.WHITELISTED.value,
                payment_method=PaymentMethod.WHITELISTED.value,
                next_payment_date=None  # Whitelisted users don't have expiry
            )
            
            return updated_user is not None
            
        except Exception as e:
            logger.error(f"Error whitelisting user {telegram_id}: {e}")
            return False
    
    def bulk_whitelist_users(
        self,
        users_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Tuple[int, int, List[int]]:
        """
        Bulk whitelist multiple users efficiently
        
        Args:
            users_data: List of user dictionaries with telegram_id and optional username
            batch_size: Number of users to process in each batch
            
        Returns:
            Tuple of (success_count, failed_count, failed_user_ids)
        """
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        try:
            for i in range(0, len(users_data), batch_size):
                batch = users_data[i:i + batch_size]
                
                # Prepare batch data for upsert
                batch_records = []
                for user_data in batch:
                    batch_records.append({
                        'telegram_id': user_data['telegram_id'],
                        'username': user_data.get('username'),
                        'subscription_status': SubscriptionStatus.WHITELISTED.value,
                        'payment_method': PaymentMethod.WHITELISTED.value,
                        'next_payment_date': None
                    })
                
                try:
                    # Upsert batch (insert or update)
                    response = self.client.table('users') \
                        .upsert(batch_records) \
                        .execute()
                    
                    if response.data:
                        success_count += len(response.data)
                    else:
                        failed_count += len(batch)
                        failed_ids.extend([u['telegram_id'] for u in batch])
                        
                except Exception as batch_error:
                    logger.error(f"Batch upsert failed: {batch_error}")
                    failed_count += len(batch)
                    failed_ids.extend([u['telegram_id'] for u in batch])
            
            logger.info(f"Bulk whitelist completed: {success_count} success, {failed_count} failed")
            return success_count, failed_count, failed_ids
            
        except Exception as e:
            logger.error(f"Bulk whitelist operation failed: {e}")
            return success_count, failed_count, failed_ids
    
    def get_whitelisted_users(self, limit: Optional[int] = None) -> List[User]:
        """
        Get all whitelisted users
        
        Args:
            limit: Optional limit on number of users to return
            
        Returns:
            List of whitelisted User objects
        """
        try:
            query = self.client.table('users') \
                .select('*') \
                .eq('subscription_status', SubscriptionStatus.WHITELISTED.value)
            
            if limit:
                query = query.limit(limit)
            
            response = query.execute()
            
            return [User(**data) for data in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting whitelisted users: {e}")
            return []
    
    def remove_from_whitelist(self, telegram_id: int) -> bool:
        """
        Remove user from whitelist
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            updated_user = self.update_user(
                telegram_id,
                subscription_status=SubscriptionStatus.EXPIRED.value,
                payment_method=None,
                next_payment_date=None
            )
            
            if updated_user:
                self.log_activity(
                    telegram_id,
                    ActivityAction.USER_REMOVED_FROM_GROUP.value,
                    {'removed_from_whitelist': True}
                )
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing user {telegram_id} from whitelist: {e}")
            return False
    
    # ============================================
    # QUERY OPERATIONS
    # ============================================
    
    def get_active_users(self) -> List[User]:
        """Get all users with active subscriptions"""
        try:
            response = self.client.table('users') \
                .select('*') \
                .in_('subscription_status', [
                    SubscriptionStatus.ACTIVE.value,
                    SubscriptionStatus.WHITELISTED.value
                ]) \
                .execute()
            
            return [User(**data) for data in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_expiring_subscriptions(self, days: int = 3) -> List[User]:
        """
        Get users with subscriptions expiring within specified days
        
        Args:
            days: Number of days to check ahead
            
        Returns:
            List of User objects with expiring subscriptions
        """
        try:
            expiry_date = (date.today() + timedelta(days=days)).isoformat()
            today = date.today().isoformat()
            
            response = self.client.table('users') \
                .select('*') \
                .eq('subscription_status', SubscriptionStatus.ACTIVE.value) \
                .gte('next_payment_date', today) \
                .lte('next_payment_date', expiry_date) \
                .execute()
            
            return [User(**data) for data in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting expiring subscriptions: {e}")
            return []
    
    def get_expired_subscriptions(self) -> List[User]:
        """Get all users with expired subscriptions that need to be processed"""
        try:
            today = date.today().isoformat()
            
            response = self.client.table('users') \
                .select('*') \
                .eq('subscription_status', SubscriptionStatus.ACTIVE.value) \
                .lt('next_payment_date', today) \
                .execute()
            
            return [User(**data) for data in response.data] if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting expired subscriptions: {e}")
            return []
    
    def expire_overdue_subscriptions(self) -> Tuple[int, List[int]]:
        """
        Expire all overdue subscriptions
        
        Returns:
            Tuple of (count of expired subscriptions, list of affected telegram_ids)
        """
        try:
            response = self.client.rpc('expire_overdue_subscriptions').execute()
            
            if response.data and len(response.data) > 0:
                result = response.data[0]
                return (
                    result.get('expired_count', 0),
                    result.get('expired_users', [])
                )
            return 0, []
            
        except Exception as e:
            logger.error(f"Error expiring overdue subscriptions: {e}")
            # Fallback to manual expiration
            return self._manual_expire_subscriptions()
    
    def _manual_expire_subscriptions(self) -> Tuple[int, List[int]]:
        """Manually expire subscriptions (fallback)"""
        try:
            expired_users = self.get_expired_subscriptions()
            expired_ids = []
            
            for user in expired_users:
                if self.update_user(
                    user.telegram_id,
                    subscription_status=SubscriptionStatus.EXPIRED.value
                ):
                    expired_ids.append(user.telegram_id)
            
            return len(expired_ids), expired_ids
            
        except Exception as e:
            logger.error(f"Error in manual subscription expiration: {e}")
            return 0, []
    
    # ============================================
    # ACTIVITY LOGGING
    # ============================================
    
    def log_activity(
        self,
        telegram_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log user activity
        
        Args:
            telegram_id: Telegram user ID
            action: Action type (use ActivityAction enum values)
            details: Additional details about the action
            
        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                'telegram_id': telegram_id,
                'action': action,
                'details': details or {}
            }
            
            response = self.client.table('activity_log') \
                .insert(data) \
                .execute()
            
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Error logging activity for {telegram_id}: {e}")
            return False
    
    def get_user_activity(
        self,
        telegram_id: int,
        limit: int = 50,
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get activity log for a user
        
        Args:
            telegram_id: Telegram user ID
            limit: Maximum number of records to return
            action_filter: Optional filter by action type
            
        Returns:
            List of activity records
        """
        try:
            query = self.client.table('activity_log') \
                .select('*') \
                .eq('telegram_id', telegram_id)
            
            if action_filter:
                query = query.eq('action', action_filter)
            
            response = query \
                .order('timestamp', desc=True) \
                .limit(limit) \
                .execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting activity for {telegram_id}: {e}")
            return []
    
    # ============================================
    # STATISTICS AND REPORTING
    # ============================================
    
    def get_subscription_stats(self) -> Dict[str, int]:
        """Get subscription statistics"""
        try:
            # Get counts for each status
            active = len(self.get_active_users())
            
            response = self.client.table('users') \
                .select('subscription_status', count='exact') \
                .execute()
            
            stats = {
                'total_users': response.count if response.count else 0,
                'active_subscriptions': active,
                'expired_subscriptions': 0,
                'whitelisted_users': 0
            }
            
            # Count by status
            all_users = self.client.table('users').select('subscription_status').execute()
            if all_users.data:
                for user in all_users.data:
                    status = user['subscription_status']
                    if status == SubscriptionStatus.EXPIRED.value:
                        stats['expired_subscriptions'] += 1
                    elif status == SubscriptionStatus.WHITELISTED.value:
                        stats['whitelisted_users'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            return {
                'total_users': 0,
                'active_subscriptions': 0,
                'expired_subscriptions': 0,
                'whitelisted_users': 0
            }
    
    def get_payment_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get payment statistics for the last N days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with payment statistics
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            response = self.client.table('activity_log') \
                .select('*') \
                .eq('action', ActivityAction.PAYMENT_SUCCESSFUL.value) \
                .gte('timestamp', since_date) \
                .execute()
            
            if not response.data:
                return {
                    'total_payments': 0,
                    'card_payments': 0,
                    'stars_payments': 0,
                    'period_days': days
                }
            
            card_count = 0
            stars_count = 0
            
            for record in response.data:
                details = record.get('details', {})
                payment_method = details.get('payment_method')
                if payment_method == PaymentMethod.CARD.value:
                    card_count += 1
                elif payment_method == PaymentMethod.STARS.value:
                    stars_count += 1
            
            return {
                'total_payments': len(response.data),
                'card_payments': card_count,
                'stars_payments': stars_count,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Error getting payment stats: {e}")
            return {
                'total_payments': 0,
                'card_payments': 0,
                'stars_payments': 0,
                'period_days': days
            }


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================

def create_client_from_env() -> SupabaseClient:
    """
    Create Supabase client using environment variables
    
    Required environment variables:
        SUPABASE_URL: Your Supabase project URL
        SUPABASE_SERVICE_KEY: Your Supabase service role key (for bot operations)
    
    Returns:
        Configured SupabaseClient instance
    """
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not url or not key:
        raise ValueError(
            "Missing required environment variables: SUPABASE_URL and SUPABASE_SERVICE_KEY"
        )
    
    return SupabaseClient(url, key, is_service_role=True)


# ============================================
# EXAMPLE USAGE
# ============================================

if __name__ == "__main__":
    # Example usage (requires environment variables to be set)
    
    # Initialize client
    # Option 1: Direct initialization
    client = SupabaseClient(
        url="https://dijdhqrxqwbctywejydj.supabase.co",
        key="your-service-role-key-here"  # Replace with actual key
    )
    
    # Option 2: From environment variables
    # client = create_client_from_env()
    
    # Example: Create or get a user
    telegram_id = 123456789
    user = client.get_or_create_user(telegram_id, username="testuser")
    if user:
        print(f"User: {user.telegram_id}, Status: {user.subscription_status}")
    
    # Example: Activate subscription
    success, expiry_date, message = client.activate_subscription(
        telegram_id,
        PaymentMethod.CARD.value,
        transaction_id="test_transaction_123"
    )
    print(f"Activation result: {success}, Expires: {expiry_date}, Message: {message}")
    
    # Example: Check subscription status
    user = client.get_user(telegram_id)
    if user and user.is_active():
        print(f"User is active, expires in {user.days_until_expiry()} days")
    
    # Example: Get statistics
    stats = client.get_subscription_stats()
    print(f"Subscription stats: {stats}")
    
    # Example: Get expiring subscriptions
    expiring = client.get_expiring_subscriptions(days=7)
    print(f"Users expiring in 7 days: {len(expiring)}")
    
    # Example: Log custom activity
    client.log_activity(
        telegram_id,
        ActivityAction.USER_JOINED_GROUP.value,
        {'group_id': -1001234567890}
    )
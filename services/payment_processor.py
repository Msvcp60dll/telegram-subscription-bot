"""
Unified Payment Processor
Handles both Airwallex card payments and Telegram Stars payments
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from enum import Enum
import json

from .airwallex_payment import AirwallexPaymentService

logger = logging.getLogger(__name__)


class PaymentMethod(Enum):
    """Available payment methods"""
    CARD = "card"  # Airwallex
    STARS = "stars"  # Telegram Stars
    

class PaymentStatus(Enum):
    """Payment status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    REFUNDED = "refunded"


class PaymentProcessor:
    """Unified payment processor for dual payment system"""
    
    def __init__(self, bot=None, db_client=None, airwallex_client_id=None, 
                 airwallex_api_key=None, webhook_base_url=None):
        """
        Initialize payment processor
        
        Args:
            bot: Telegram bot instance for Stars payments
            db_client: Supabase database client
            airwallex_client_id: Airwallex client ID
            airwallex_api_key: Airwallex API key
            webhook_base_url: Base URL for webhooks
        """
        self.bot = bot
        self.db = db_client
        self.airwallex = None
        
        # Initialize Airwallex if credentials provided
        if airwallex_client_id and airwallex_api_key:
            self.airwallex = AirwallexPaymentService(
                client_id=airwallex_client_id,
                api_key=airwallex_api_key
            )
        
        self.webhook_base_url = webhook_base_url
        self.webhook_task = None
        
        # In-memory storage (replace with database in production)
        self.payment_sessions = {}
        self.payment_history = {}
        
        # Revenue tracking
        self.revenue_stats = {
            "card": {"count": 0, "total_usd": 0.0},
            "stars": {"count": 0, "total_stars": 0}
        }
        
        logger.info("Payment processor initialized")
    
    async def initialize(self):
        """Initialize payment services"""
        try:
            # Initialize Airwallex service
            self.airwallex = AirwallexPaymentService()
            await self.airwallex.initialize()
            logger.info("Airwallex service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Airwallex: {e}")
            self.airwallex = None
    
    async def close(self):
        """Cleanup payment services"""
        if self.airwallex:
            await self.airwallex.close()
    
    async def create_payment_session(
        self,
        user_id: int,
        plan_id: str,
        plan_details: Dict,
        user_info: Dict = None
    ) -> str:
        """
        Create a new payment session
        
        Args:
            user_id: Telegram user ID
            plan_id: Subscription plan ID
            plan_details: Plan information (name, price, duration)
            user_info: Optional user information (username, email, etc)
        
        Returns:
            str: Payment session ID
        """
        
        session_id = f"pay_{user_id}_{int(datetime.now().timestamp())}"
        
        self.payment_sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "plan_id": plan_id,
            "plan_details": plan_details,
            "user_info": user_info or {},
            "status": PaymentStatus.PENDING.value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "payment_method": None,
            "payment_link_id": None,
            "payment_intent_id": None,
            "transaction_id": None,
            "attempts": []
        }
        
        logger.info(f"Created payment session {session_id} for user {user_id}")
        return session_id
    
    async def process_card_payment(
        self,
        session_id: str,
        webhook_url: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Process card payment via Airwallex
        
        Returns:
            Tuple of (success: bool, result: dict)
            On success: result contains 'payment_url', 'payment_link_id'
            On failure: result contains 'error', may include 'fallback_available'
        """
        
        if session_id not in self.payment_sessions:
            return False, {"error": "Invalid payment session"}
        
        session = self.payment_sessions[session_id]
        
        # Check if Airwallex is available
        if not self.airwallex:
            logger.warning("Airwallex not available, suggesting Stars payment")
            return False, {
                "error": "Card payment service temporarily unavailable",
                "fallback_available": True,
                "fallback_method": PaymentMethod.STARS.value
            }
        
        try:
            # Update session status
            session["status"] = PaymentStatus.PROCESSING.value
            session["payment_method"] = PaymentMethod.CARD.value
            
            # Calculate amount in USD (assuming 1 Star = $0.02)
            stars_price = session["plan_details"].get("stars", 50)
            usd_amount = stars_price * 0.02
            
            # Create Airwallex payment link
            success, result = await self.airwallex.create_payment_link(
                amount=usd_amount,
                currency="USD",
                customer_email=session["user_info"].get("email"),
                customer_name=session["user_info"].get("name", f"User {session['user_id']}"),
                telegram_id=session["user_id"],
                telegram_username=session["user_info"].get("username"),
                plan_id=session["plan_id"],
                plan_name=session["plan_details"].get("name"),
                expires_in_hours=24,
                webhook_url=webhook_url
            )
            
            if success:
                # Store payment link details
                session["payment_link_id"] = result["id"]
                session["payment_url"] = result["url"]
                session["attempts"].append({
                    "method": PaymentMethod.CARD.value,
                    "timestamp": datetime.now(),
                    "status": "link_created"
                })
                
                logger.info(f"Created Airwallex payment link for session {session_id}")
                
                return True, {
                    "payment_url": result["url"],
                    "payment_link_id": result["id"],
                    "amount_usd": usd_amount,
                    "expires_at": result.get("expires_at")
                }
            else:
                # Airwallex failed, suggest fallback
                session["status"] = PaymentStatus.FAILED.value
                session["attempts"].append({
                    "method": PaymentMethod.CARD.value,
                    "timestamp": datetime.now(),
                    "status": "failed",
                    "error": result.get("error")
                })
                
                logger.error(f"Airwallex payment creation failed: {result.get('error')}")
                
                return False, {
                    "error": result.get("error", "Failed to create payment link"),
                    "fallback_available": True,
                    "fallback_method": PaymentMethod.STARS.value
                }
                
        except Exception as e:
            logger.error(f"Error processing card payment: {e}")
            session["status"] = PaymentStatus.FAILED.value
            
            return False, {
                "error": str(e),
                "fallback_available": True,
                "fallback_method": PaymentMethod.STARS.value
            }
    
    async def process_stars_payment(
        self,
        session_id: str,
        invoice_payload: str = None
    ) -> Tuple[bool, Dict]:
        """
        Process Telegram Stars payment
        
        Returns:
            Tuple of (success: bool, result: dict)
        """
        
        if session_id not in self.payment_sessions:
            return False, {"error": "Invalid payment session"}
        
        session = self.payment_sessions[session_id]
        
        try:
            # Update session
            session["status"] = PaymentStatus.PROCESSING.value
            session["payment_method"] = PaymentMethod.STARS.value
            session["invoice_payload"] = invoice_payload or session_id
            
            session["attempts"].append({
                "method": PaymentMethod.STARS.value,
                "timestamp": datetime.now(),
                "status": "invoice_created"
            })
            
            logger.info(f"Prepared Stars payment for session {session_id}")
            
            return True, {
                "invoice_payload": session["invoice_payload"],
                "stars_amount": session["plan_details"].get("stars", 50)
            }
            
        except Exception as e:
            logger.error(f"Error processing Stars payment: {e}")
            session["status"] = PaymentStatus.FAILED.value
            return False, {"error": str(e)}
    
    async def confirm_payment(
        self,
        session_id: str = None,
        payment_link_id: str = None,
        transaction_id: str = None,
        payment_method: PaymentMethod = None
    ) -> Tuple[bool, Dict]:
        """
        Confirm payment completion
        
        Returns:
            Tuple of (success: bool, result: dict with subscription details)
        """
        
        # Find session by session_id or payment_link_id
        session = None
        if session_id and session_id in self.payment_sessions:
            session = self.payment_sessions[session_id]
        elif payment_link_id:
            for sid, sess in self.payment_sessions.items():
                if sess.get("payment_link_id") == payment_link_id:
                    session = sess
                    session_id = sid
                    break
        
        if not session:
            return False, {"error": "Payment session not found"}
        
        try:
            # Verify payment based on method
            if payment_method == PaymentMethod.CARD:
                # Verify with Airwallex
                if self.airwallex and payment_link_id:
                    success, status_result = await self.airwallex.get_payment_link_status(payment_link_id)
                    if not success or status_result.get("status") != "PAID":
                        return False, {"error": "Payment not confirmed with provider"}
            
            # Update session
            session["status"] = PaymentStatus.COMPLETED.value
            session["transaction_id"] = transaction_id
            session["completed_at"] = datetime.now()
            
            # Calculate subscription details
            plan_details = session["plan_details"]
            subscription_expires = datetime.now() + timedelta(days=plan_details.get("days", 30))
            
            # Update revenue stats
            if payment_method == PaymentMethod.CARD:
                self.revenue_stats["card"]["count"] += 1
                self.revenue_stats["card"]["total_usd"] += plan_details.get("stars", 50) * 0.02
            elif payment_method == PaymentMethod.STARS:
                self.revenue_stats["stars"]["count"] += 1
                self.revenue_stats["stars"]["total_stars"] += plan_details.get("stars", 50)
            
            # Store in payment history
            self.payment_history[session_id] = {
                **session,
                "subscription_expires": subscription_expires
            }
            
            logger.info(f"Payment confirmed for session {session_id} via {payment_method.value}")
            
            return True, {
                "user_id": session["user_id"],
                "plan_id": session["plan_id"],
                "plan_name": plan_details.get("name"),
                "expires_at": subscription_expires,
                "transaction_id": transaction_id,
                "payment_method": payment_method.value
            }
            
        except Exception as e:
            logger.error(f"Error confirming payment: {e}")
            return False, {"error": str(e)}
    
    async def cancel_payment(self, session_id: str) -> bool:
        """Cancel a payment session"""
        
        if session_id not in self.payment_sessions:
            return False
        
        session = self.payment_sessions[session_id]
        
        # Cancel Airwallex payment link if exists
        if session.get("payment_link_id") and self.airwallex:
            await self.airwallex.cancel_payment_link(session["payment_link_id"])
        
        session["status"] = PaymentStatus.CANCELLED.value
        session["cancelled_at"] = datetime.now()
        
        logger.info(f"Payment session {session_id} cancelled")
        return True
    
    async def process_refund(
        self,
        transaction_id: str,
        user_id: int,
        payment_method: PaymentMethod,
        reason: str = None
    ) -> Tuple[bool, str]:
        """
        Process refund for a payment
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        
        try:
            if payment_method == PaymentMethod.STARS:
                # For Stars, the bot handler will process the refund
                logger.info(f"Refund initiated for Stars payment {transaction_id}")
                return True, "Stars refund will be processed by Telegram"
                
            elif payment_method == PaymentMethod.CARD:
                # For Airwallex, manual refund process or API call needed
                logger.info(f"Card refund requested for transaction {transaction_id}")
                return True, "Card refund request logged. Process manually via Airwallex dashboard."
            
            return False, "Unknown payment method"
            
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            return False, str(e)
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """Get payment session status"""
        return self.payment_sessions.get(session_id)
    
    def get_revenue_stats(self) -> Dict:
        """Get revenue statistics by payment method"""
        return {
            "card": {
                "transactions": self.revenue_stats["card"]["count"],
                "total_usd": self.revenue_stats["card"]["total_usd"],
                "average_usd": (
                    self.revenue_stats["card"]["total_usd"] / self.revenue_stats["card"]["count"]
                    if self.revenue_stats["card"]["count"] > 0 else 0
                )
            },
            "stars": {
                "transactions": self.revenue_stats["stars"]["count"],
                "total_stars": self.revenue_stats["stars"]["total_stars"],
                "average_stars": (
                    self.revenue_stats["stars"]["total_stars"] / self.revenue_stats["stars"]["count"]
                    if self.revenue_stats["stars"]["count"] > 0 else 0
                )
            },
            "total_transactions": (
                self.revenue_stats["card"]["count"] + self.revenue_stats["stars"]["count"]
            ),
            "card_percentage": (
                self.revenue_stats["card"]["count"] * 100 / 
                (self.revenue_stats["card"]["count"] + self.revenue_stats["stars"]["count"])
                if (self.revenue_stats["card"]["count"] + self.revenue_stats["stars"]["count"]) > 0 else 0
            )
        }
    
    async def cleanup_expired_sessions(self):
        """Clean up expired payment sessions"""
        
        now = datetime.now()
        expired_sessions = []
        
        for session_id, session in self.payment_sessions.items():
            if session.get("expires_at") and session["expires_at"] < now:
                if session["status"] in [PaymentStatus.PENDING.value, PaymentStatus.PROCESSING.value]:
                    session["status"] = PaymentStatus.EXPIRED.value
                    expired_sessions.append(session_id)
                    
                    # Cancel Airwallex payment link if exists
                    if session.get("payment_link_id") and self.airwallex:
                        await self.airwallex.cancel_payment_link(session["payment_link_id"])
        
        # Move expired sessions to history
        for session_id in expired_sessions:
            self.payment_history[session_id] = self.payment_sessions.pop(session_id)
            logger.info(f"Expired payment session {session_id}")
        
        return len(expired_sessions)
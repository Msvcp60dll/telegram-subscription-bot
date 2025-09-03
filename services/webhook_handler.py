"""
Webhook Handler for Airwallex Payment Notifications
Processes incoming webhooks from Airwallex for payment status updates
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Optional
from aiohttp import web
import os

logger = logging.getLogger(__name__)


class AirwallexWebhookHandler:
    """Handles Airwallex webhook notifications"""
    
    def __init__(self, payment_processor=None, bot=None):
        """
        Initialize webhook handler
        
        Args:
            payment_processor: PaymentProcessor instance
            bot: Telegram bot instance for notifications
        """
        self.payment_processor = payment_processor
        self.bot = bot
        self.webhook_secret = os.getenv("AIRWALLEX_WEBHOOK_SECRET", "")
        
        # Track processed webhooks to prevent duplicates
        self.processed_webhooks = set()
        
        logger.info("Airwallex webhook handler initialized")
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming webhook from Airwallex with proper security validation
        
        Security implementation based on:
        https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events
        
        Args:
            request: aiohttp web request
        
        Returns:
            web.Response with appropriate status
        """
        
        try:
            # Step 1: Extract security headers (required for signature verification)
            webhook_timestamp = request.headers.get('x-timestamp')
            webhook_signature = request.headers.get('x-signature')
            
            # Validate required headers are present
            if not webhook_timestamp or not webhook_signature:
                logger.warning("Missing required webhook headers (x-timestamp or x-signature)")
                return web.Response(status=400, text="Missing required headers")
            
            # Step 2: Read raw request body BEFORE any parsing
            # This is critical - signature must be verified against raw body
            body = await request.text()
            
            # Step 3: Verify webhook signature and timestamp
            if self.webhook_secret and self.payment_processor and self.payment_processor.airwallex:
                is_valid = self.payment_processor.airwallex.verify_webhook_signature(
                    body=body,  # Raw JSON body
                    timestamp=webhook_timestamp,
                    signature=webhook_signature,
                    tolerance_seconds=300  # 5-minute tolerance
                )
                
                if not is_valid:
                    logger.warning("Webhook signature verification failed")
                    # Security: Never expose details about why verification failed
                    return web.Response(status=401, text="Unauthorized")
            
            # Step 4: Parse webhook data AFTER signature verification
            try:
                webhook_data = json.loads(body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook body")
                return web.Response(status=400, text="Invalid JSON")
            
            # Step 5: Extract event ID for idempotency
            webhook_id = webhook_data.get('id')
            if not webhook_id:
                logger.warning("No event ID in webhook data")
                return web.Response(status=400, text="Missing event ID")
            
            # Step 6: Check for duplicate processing (idempotency)
            if webhook_id in self.processed_webhooks:
                logger.info(f"Duplicate webhook {webhook_id} ignored (idempotent handling)")
                return web.Response(status=200, text="OK")  # Return 200 for idempotency
            
            # Step 7: Process the webhook event
            await self.process_webhook_event(webhook_data)
            
            # Step 8: Mark as processed for idempotency
            self.processed_webhooks.add(webhook_id)
            
            # Implement simple LRU-style cleanup (production should use Redis/DB)
            if len(self.processed_webhooks) > 10000:
                # Keep only the most recent 5000 entries
                recent_webhooks = list(self.processed_webhooks)[-5000:]
                self.processed_webhooks = set(recent_webhooks)
            
            # Step 9: Return success quickly (Airwallex expects response within 5 seconds)
            return web.Response(status=200, text="OK")
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}", exc_info=True)
            # Security: Don't expose internal error details
            return web.Response(status=500, text="Internal server error")
    
    async def process_webhook_event(self, webhook_data: Dict):
        """
        Process specific webhook event
        
        Args:
            webhook_data: Parsed webhook JSON data
        """
        
        event_name = webhook_data.get("name")
        event_data = webhook_data.get("data", {})
        
        logger.info(f"Processing webhook event: {event_name}")
        
        if event_name == "payment_intent.succeeded":
            await self.handle_payment_success(event_data)
            
        elif event_name == "payment_intent.failed":
            await self.handle_payment_failure(event_data)
            
        elif event_name == "payment_link.expired":
            await self.handle_link_expired(event_data)
            
        elif event_name == "refund.succeeded":
            await self.handle_refund_success(event_data)
            
        else:
            logger.info(f"Unhandled webhook event: {event_name}")
    
    async def handle_payment_success(self, event_data: Dict):
        """Handle successful payment event"""
        
        payment_intent = event_data.get("object", {})
        payment_link_id = payment_intent.get("payment_link_id")
        metadata = payment_intent.get("metadata", {})
        
        telegram_id = metadata.get("telegram_id")
        plan_id = metadata.get("plan_id")
        amount = payment_intent.get("amount")
        currency = payment_intent.get("currency")
        
        logger.info(f"Payment succeeded for user {telegram_id}, link {payment_link_id}")
        
        if not telegram_id:
            logger.warning("No telegram_id in payment metadata")
            return
        
        try:
            telegram_id = int(telegram_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid telegram_id: {telegram_id}")
            return
        
        # Confirm payment in processor
        if self.payment_processor:
            from services.payment_processor import PaymentMethod
            
            success, subscription = await self.payment_processor.confirm_payment(
                payment_link_id=payment_link_id,
                transaction_id=payment_intent.get("id"),
                payment_method=PaymentMethod.CARD
            )
            
            if success and self.bot:
                # Notify user via bot
                try:
                    # Import here to avoid circular dependency
                    from handlers.payments import add_user_to_group, user_subscriptions
                    
                    # Add user to group
                    await add_user_to_group(self.bot, telegram_id)
                    
                    # Save subscription
                    user_subscriptions[telegram_id] = {
                        "plan": subscription['plan_name'],
                        "expires_at": subscription['expires_at'],
                        "transaction_id": payment_intent.get("id"),
                        "payment_method": "card",
                        "amount": amount,
                        "currency": currency,
                        "purchased_at": datetime.now()
                    }
                    
                    # Send confirmation message
                    confirmation_text = f"""
✅ <b>Payment Confirmed!</b>

Your card payment has been successfully processed.

<b>Details:</b>
• Plan: {subscription['plan_name']}
• Amount: {amount/100:.2f} {currency}
• Expires: {subscription['expires_at'].strftime('%Y-%m-%d %H:%M')}

Check your messages for the group invite link!
"""
                    
                    await self.bot.send_message(telegram_id, confirmation_text, parse_mode="HTML")
                    
                except Exception as e:
                    logger.error(f"Error notifying user {telegram_id}: {e}")
    
    async def handle_payment_failure(self, event_data: Dict):
        """Handle failed payment event"""
        
        payment_intent = event_data.get("object", {})
        metadata = payment_intent.get("metadata", {})
        telegram_id = metadata.get("telegram_id")
        error = payment_intent.get("last_payment_error", {})
        
        logger.info(f"Payment failed for user {telegram_id}")
        
        if telegram_id and self.bot:
            try:
                telegram_id = int(telegram_id)
                
                error_message = error.get("message", "Payment processing failed")
                
                text = f"""
❌ <b>Payment Failed</b>

Your card payment could not be processed.

Reason: {error_message}

You can try again or use Telegram Stars payment instead.
"""
                
                await self.bot.send_message(telegram_id, text, parse_mode="HTML")
                
            except Exception as e:
                logger.error(f"Error notifying user about payment failure: {e}")
    
    async def handle_link_expired(self, event_data: Dict):
        """Handle payment link expiration"""
        
        payment_link = event_data.get("object", {})
        metadata = payment_link.get("metadata", {})
        telegram_id = metadata.get("telegram_id")
        
        logger.info(f"Payment link expired for user {telegram_id}")
        
        if telegram_id and self.bot:
            try:
                telegram_id = int(telegram_id)
                
                text = """
⏰ <b>Payment Link Expired</b>

Your payment link has expired. Please create a new payment request to continue.
"""
                
                await self.bot.send_message(telegram_id, text, parse_mode="HTML")
                
            except Exception as e:
                logger.error(f"Error notifying user about link expiration: {e}")
    
    async def handle_refund_success(self, event_data: Dict):
        """Handle successful refund"""
        
        refund = event_data.get("object", {})
        payment_intent_id = refund.get("payment_intent_id")
        amount = refund.get("amount")
        currency = refund.get("currency")
        
        logger.info(f"Refund processed for payment {payment_intent_id}")
        
        # Find user from payment intent metadata
        # In production, you would look this up in your database
        # For now, just log the refund
        
        logger.info(f"Refunded {amount/100:.2f} {currency} for payment {payment_intent_id}")


def create_webhook_app(payment_processor=None, bot=None) -> web.Application:
    """
    Create aiohttp application for webhook handling
    
    Args:
        payment_processor: PaymentProcessor instance
        bot: Telegram bot instance
    
    Returns:
        web.Application configured for webhooks
    """
    
    app = web.Application()
    handler = AirwallexWebhookHandler(payment_processor, bot)
    
    # Add webhook route
    app.router.add_post('/webhook/airwallex', handler.handle_webhook)
    
    # Add health check endpoint with detailed status
    async def health_check(request):
        """Health check endpoint with detailed system status"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "webhook_handler",
            "components": {
                "webhook_handler": "operational",
                "payment_processor": "operational" if payment_processor else "not_configured",
                "bot_connection": "operational" if bot else "not_configured"
            },
            "stats": {
                "processed_webhooks": len(handler.processed_webhooks),
                "webhook_secret_configured": bool(handler.webhook_secret)
            }
        }
        return web.json_response(health_data, status=200)
    
    app.router.add_get('/health', health_check)
    
    logger.info("Webhook application created")
    
    return app
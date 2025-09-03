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
        Handle incoming webhook from Airwallex
        
        Args:
            request: aiohttp web request
        
        Returns:
            web.Response with appropriate status
        """
        
        try:
            # Get webhook headers
            webhook_id = request.headers.get('x-webhook-id')
            webhook_timestamp = request.headers.get('x-webhook-timestamp')
            webhook_signature = request.headers.get('x-webhook-signature')
            
            # Check for duplicate processing
            if webhook_id in self.processed_webhooks:
                logger.info(f"Duplicate webhook {webhook_id} ignored")
                return web.Response(status=200, text="Already processed")
            
            # Read request body
            body = await request.text()
            
            # Verify signature if secret is configured
            if self.webhook_secret and self.payment_processor and self.payment_processor.airwallex:
                is_valid = self.payment_processor.airwallex.verify_webhook_signature(
                    webhook_id=webhook_id,
                    timestamp=webhook_timestamp,
                    signature=webhook_signature
                )
                
                if not is_valid:
                    logger.warning(f"Invalid webhook signature for {webhook_id}")
                    return web.Response(status=401, text="Invalid signature")
            
            # Parse webhook data
            try:
                webhook_data = json.loads(body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook body")
                return web.Response(status=400, text="Invalid JSON")
            
            # Process the webhook
            await self.process_webhook_event(webhook_data)
            
            # Mark as processed
            self.processed_webhooks.add(webhook_id)
            
            # Clean old entries if set grows too large
            if len(self.processed_webhooks) > 1000:
                self.processed_webhooks.clear()
            
            return web.Response(status=200, text="OK")
            
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return web.Response(status=500, text="Internal error")
    
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
    
    # Add health check endpoint
    async def health_check(request):
        return web.Response(text="OK", status=200)
    
    app.router.add_get('/health', health_check)
    
    logger.info("Webhook application created")
    
    return app
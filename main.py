"""
Subscription Management Bot - Main Module
A Telegram bot for managing subscriptions with Stars payment integration
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
import asyncio

# Import handlers
from handlers.commands import router as commands_router
from handlers.payments import router as payments_router
from handlers.admin import router as admin_router
from handlers.migration import router as migration_router

# Import services
from services.payment_processor import PaymentProcessor
from services.webhook_handler import create_webhook_app
from database.supabase_client import SupabaseClient
from services.subscription_manager import SubscriptionManager
from admin_dashboard import create_admin_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration from environment or hardcoded (for development)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8263837787:AAGDc9HzLBcESW4wL3BhZ8ABnifu7wjCM6o")
GROUP_ID = int(os.getenv("GROUP_ID", "-1002384609773"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "306145881"))

# Airwallex configuration
AIRWALLEX_CLIENT_ID = os.getenv("AIRWALLEX_CLIENT_ID", "BxnIFV1TQkWbrpkEKaADwg")
AIRWALLEX_API_KEY = os.getenv("AIRWALLEX_API_KEY", "df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47")
AIRWALLEX_WEBHOOK_SECRET = os.getenv("AIRWALLEX_WEBHOOK_SECRET", "")
WEBHOOK_BASE_URL = os.getenv("WEBHOOK_BASE_URL", "")  # e.g., https://your-domain.com
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8080")))

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://dijdhqrxqwbctywejydj.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "sb_secret_10UN2tVL4bV5mLYVQ1z3Kg_x2s5yIr1")

# Export configuration for use in handlers
config = {
    "bot_token": BOT_TOKEN,
    "group_id": GROUP_ID,
    "admin_user_id": ADMIN_USER_ID,
    "subscription_plans": {
        "basic": {"stars": 50, "days": 7, "name": "Basic (7 days)"},
        "standard": {"stars": 100, "days": 30, "name": "Standard (30 days)"},
        "premium": {"stars": 500, "days": 180, "name": "Premium (6 months)"}
    }
}

# Initialize bot instance
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True
    )
)

# Initialize dispatcher with FSM storage
dp = Dispatcher(storage=MemoryStorage())

# Register routers
dp.include_router(commands_router)
dp.include_router(payments_router)
dp.include_router(admin_router)
dp.include_router(migration_router)

# Initialize services
# Initialize database client
db_client = SupabaseClient(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Initialize payment processor
payment_processor = PaymentProcessor(
    bot=bot,
    db_client=db_client,
    airwallex_client_id=AIRWALLEX_CLIENT_ID,
    airwallex_api_key=AIRWALLEX_API_KEY,
    webhook_base_url=WEBHOOK_BASE_URL
)

# Initialize subscription manager
subscription_manager = SubscriptionManager(bot, db_client, GROUP_ID)

# Webhook app for Airwallex (optional)
webhook_app = None
webhook_runner = None

# Admin dashboard app
admin_app = None
admin_runner = None

async def on_startup():
    """Actions to perform on bot startup"""
    global webhook_app, webhook_runner
    
    logger.info("Bot starting up...")
    
    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot: @{bot_info.username} (ID: {bot_info.id})")
    
    # Check group access
    try:
        group_info = await bot.get_chat(GROUP_ID)
        logger.info(f"Group configured: {group_info.title} (ID: {GROUP_ID})")
    except Exception as e:
        logger.error(f"Failed to access group {GROUP_ID}: {e}")
        logger.warning("Make sure the bot is added to the group as an administrator!")
    
    # Initialize payment processor
    try:
        if hasattr(payment_processor, 'initialize'):
            await payment_processor.initialize()
        from handlers.payments import set_payment_processor
        set_payment_processor(payment_processor)
        logger.info("Payment processor initialized and configured")
    except Exception as e:
        logger.error(f"Failed to initialize payment processor: {e}")
        logger.warning("Bot will run with limited payment functionality")
    
    # Start subscription automation
    try:
        await subscription_manager.start_automation()
        logger.info("Subscription automation started")
    except Exception as e:
        logger.error(f"Failed to start subscription automation: {e}")
        logger.warning("Subscription checks will not run automatically")
    
    # Start webhook server if URL is configured
    if WEBHOOK_BASE_URL:
        try:
            webhook_app = create_webhook_app(payment_processor, bot)
            webhook_runner = web.AppRunner(webhook_app)
            await webhook_runner.setup()
            site = web.TCPSite(webhook_runner, '0.0.0.0', WEBHOOK_PORT)
            await site.start()
            logger.info(f"Webhook server started on port {WEBHOOK_PORT}")
            logger.info(f"Webhook URL: {WEBHOOK_BASE_URL}/webhook/airwallex")
        except Exception as e:
            logger.error(f"Failed to start webhook server: {e}")
            logger.warning("Webhook notifications will not be available")
    else:
        logger.info("Webhook URL not configured, webhook server not started")
    
    # Start admin dashboard
    global admin_app, admin_runner
    try:
        admin_app = create_admin_app(db_client, bot)
        admin_runner = web.AppRunner(admin_app)
        await admin_runner.setup()
        admin_site = web.TCPSite(admin_runner, '0.0.0.0', 8081)  # Different port from webhook
        await admin_site.start()
        logger.info(f"Admin dashboard started on port 8081")
        logger.info(f"Access admin dashboard at: http://localhost:8081/")
    except Exception as e:
        logger.error(f"Failed to start admin dashboard: {e}")
        logger.warning("Admin dashboard will not be available")
    
    logger.info("Bot startup complete!")

async def on_shutdown():
    """Actions to perform on bot shutdown"""
    global webhook_runner, admin_runner
    
    logger.info("Bot shutting down...")
    
    # Stop subscription automation
    try:
        await subscription_manager.stop_automation()
        logger.info("Subscription automation stopped")
    except Exception as e:
        logger.error(f"Error stopping automation: {e}")
    
    # Close payment processor
    if hasattr(payment_processor, 'close'):
        await payment_processor.close()
        logger.info("Payment processor closed")
    
    # Stop webhook server
    if webhook_runner:
        await webhook_runner.cleanup()
        logger.info("Webhook server stopped")
    
    await bot.session.close()
    logger.info("Bot shutdown complete!")

async def main():
    """Main function to run the bot"""
    # Register startup and shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    try:
        logger.info("Starting bot polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Skip old messages
        )
    except Exception as e:
        logger.error(f"Bot polling failed: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
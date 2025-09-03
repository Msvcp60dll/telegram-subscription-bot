# Aiogram 3 Framework Reference

**Version**: 3.x  
**Last Updated**: 2025-09-03  
**Official Documentation**: https://docs.aiogram.dev/

## Table of Contents
1. [Basic Bot Setup](#basic-bot-setup)
2. [Command Handlers and Routers](#command-handlers-and-routers)
3. [Inline Keyboards and Callback Queries](#inline-keyboards-and-callback-queries)
4. [FSM (Finite State Machine)](#fsm-finite-state-machine)
5. [Telegram Stars Payment Integration](#telegram-stars-payment-integration)
6. [Webhook Setup](#webhook-setup)

## Basic Bot Setup

### Installation
```bash
pip install aiogram
```

### Basic Bot Initialization
```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Initialize bot with HTML parse mode
bot = Bot(
    token="YOUR_BOT_TOKEN",
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

# Create dispatcher
dp = Dispatcher()

# Main function to start polling
async def main():
    # Start polling
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

## Command Handlers and Routers

### Basic Command Handler
```python
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram import html

# Create router
router = Router()

# Handle /start command
@router.message(CommandStart())
async def command_start_handler(message: Message):
    await message.answer(f"Hello, {html.bold(message.from_user.full_name)}!")

# Handle /help command
@router.message(Command("help"))
async def command_help_handler(message: Message):
    help_text = """
    Available commands:
    /start - Start the bot
    /help - Show this help message
    /subscribe - View subscription options
    """
    await message.answer(help_text)

# Handle any other message
@router.message()
async def echo_handler(message: Message):
    await message.send_copy(chat_id=message.chat.id)
```

### Using Multiple Routers (Modular Structure)
```python
from aiogram import Router, Dispatcher

# Create main router
main_router = Router()

# Create sub-routers for different features
user_router = Router()
admin_router = Router()
payment_router = Router()

# Include routers in dispatcher
dp = Dispatcher()
dp.include_router(main_router)
dp.include_router(user_router)
dp.include_router(admin_router)
dp.include_router(payment_router)
```

## Inline Keyboards and Callback Queries

### Creating Inline Keyboards
```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Method 1: Direct creation
def get_subscription_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐ 50 Stars", callback_data="sub_50"),
                InlineKeyboardButton(text="⭐ 100 Stars", callback_data="sub_100")
            ],
            [
                InlineKeyboardButton(text="⭐ 500 Stars", callback_data="sub_500")
            ],
            [
                InlineKeyboardButton(text="Cancel", callback_data="cancel")
            ]
        ]
    )
    return keyboard

# Method 2: Using InlineKeyboardBuilder
def build_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    
    # Add buttons
    builder.button(text="⭐ 50 Stars - Basic", callback_data="plan_basic")
    builder.button(text="⭐ 100 Stars - Pro", callback_data="plan_pro")
    builder.button(text="⭐ 500 Stars - Premium", callback_data="plan_premium")
    builder.button(text="❌ Cancel", callback_data="cancel")
    
    # Adjust layout (2 buttons per row for first row, then 1 per row)
    builder.adjust(2, 1, 1)
    
    return builder.as_markup()
```

### Handling Callback Queries
```python
from aiogram import F
from aiogram.types import CallbackQuery

# Handle specific callback data
@router.callback_query(F.data == "sub_50")
async def process_subscription_50(callback: CallbackQuery):
    await callback.answer("Processing 50 Stars subscription...")
    await callback.message.edit_text(
        "You selected: 50 Stars subscription\nProcessing payment..."
    )

# Handle callback data with pattern
@router.callback_query(F.data.startswith("plan_"))
async def process_plan_selection(callback: CallbackQuery):
    plan = callback.data.split("_")[1]
    await callback.answer(f"Selected {plan} plan", show_alert=True)
    
    # Update message with selection
    await callback.message.edit_text(
        f"You selected the {plan.upper()} plan",
        reply_markup=get_confirmation_keyboard(plan)
    )

# Handle all callbacks (fallback)
@router.callback_query()
async def handle_any_callback(callback: CallbackQuery):
    await callback.answer("Unknown action")
```

### Advanced Callback Data with Factory
```python
from aiogram.filters.callback_data import CallbackData

# Define callback data factory
class SubscriptionCallback(CallbackData, prefix="sub"):
    action: str
    plan_id: int
    stars: int

# Create keyboard with factory
def get_plans_keyboard():
    builder = InlineKeyboardBuilder()
    
    plans = [
        {"id": 1, "stars": 50, "name": "Basic"},
        {"id": 2, "stars": 100, "name": "Pro"},
        {"id": 3, "stars": 500, "name": "Premium"}
    ]
    
    for plan in plans:
        builder.button(
            text=f"⭐ {plan['stars']} - {plan['name']}",
            callback_data=SubscriptionCallback(
                action="buy",
                plan_id=plan['id'],
                stars=plan['stars']
            )
        )
    
    return builder.as_markup()

# Handle factory callbacks
@router.callback_query(SubscriptionCallback.filter(F.action == "buy"))
async def process_subscription_purchase(
    callback: CallbackQuery,
    callback_data: SubscriptionCallback
):
    await callback.answer(f"Purchasing {callback_data.stars} stars...")
    # Process payment...
```

## FSM (Finite State Machine)

### Define States
```python
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Define form states
class SubscriptionForm(StatesGroup):
    choosing_plan = State()
    entering_email = State()
    confirming_payment = State()

class UserRegistration(StatesGroup):
    entering_name = State()
    entering_email = State()
    entering_phone = State()
```

### Using FSM in Handlers
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Start registration process
@router.message(Command("register"))
async def start_registration(message: Message, state: FSMContext):
    await state.set_state(UserRegistration.entering_name)
    await message.answer(
        "Let's start registration!\nPlease enter your full name:",
        reply_markup=ReplyKeyboardRemove()
    )

# Handle name input
@router.message(UserRegistration.entering_name)
async def process_name(message: Message, state: FSMContext):
    # Save name to state data
    await state.update_data(name=message.text)
    
    # Move to next state
    await state.set_state(UserRegistration.entering_email)
    await message.answer("Great! Now please enter your email:")

# Handle email input
@router.message(UserRegistration.entering_email)
async def process_email(message: Message, state: FSMContext):
    # Validate email
    if "@" not in message.text:
        await message.answer("Please enter a valid email address:")
        return
    
    await state.update_data(email=message.text)
    await state.set_state(UserRegistration.entering_phone)
    
    # Create keyboard for phone sharing
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Share Phone", request_contact=True)],
            [KeyboardButton(text="Skip")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "Please share your phone number or skip:",
        reply_markup=keyboard
    )

# Handle phone input
@router.message(UserRegistration.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    # Check if contact was shared
    if message.contact:
        phone = message.contact.phone_number
    elif message.text == "Skip":
        phone = None
    else:
        phone = message.text
    
    await state.update_data(phone=phone)
    
    # Get all data
    data = await state.get_data()
    
    # Clear state
    await state.clear()
    
    # Show summary
    summary = f"""
    Registration complete!
    
    Name: {data['name']}
    Email: {data['email']}
    Phone: {data.get('phone', 'Not provided')}
    """
    
    await message.answer(summary, reply_markup=ReplyKeyboardRemove())
```

### Cancel FSM Operation
```python
from aiogram.fsm.context import FSMContext

@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("Nothing to cancel")
        return
    
    await state.clear()
    await message.answer(
        "Operation cancelled",
        reply_markup=ReplyKeyboardRemove()
    )
```

## Telegram Stars Payment Integration

### Creating Stars Invoice
```python
from aiogram.types import LabeledPrice

@router.message(Command("subscribe"))
async def send_stars_invoice(message: Message):
    # Create invoice for Telegram Stars
    await message.answer_invoice(
        title="Premium Subscription",
        description="Get access to premium features for 30 days",
        prices=[
            LabeledPrice(label="Premium Access", amount=100)  # 100 Stars
        ],
        payload="premium_subscription_30d",
        currency="XTR",  # Required for Telegram Stars
        provider_token=""  # Empty for Telegram Stars
    )

# Multiple price items
@router.message(Command("buy_bundle"))
async def send_bundle_invoice(message: Message):
    await message.answer_invoice(
        title="Feature Bundle",
        description="Get multiple features at once",
        prices=[
            LabeledPrice(label="Feature A", amount=30),
            LabeledPrice(label="Feature B", amount=40),
            LabeledPrice(label="Bonus Content", amount=20),
            LabeledPrice(label="Discount", amount=-10)  # Negative for discount
        ],
        payload="feature_bundle",
        currency="XTR",
        provider_token=""
    )
```

### Handling Pre-Checkout Query
```python
from aiogram.types import PreCheckoutQuery

@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery):
    # Validate the payment
    payload = query.invoice_payload
    
    # Check if item is in stock or user is eligible
    if payload == "premium_subscription_30d":
        # Check user eligibility
        user_id = query.from_user.id
        
        # Example validation
        if await is_user_banned(user_id):
            await query.answer(
                ok=False,
                error_message="You are not eligible for this subscription"
            )
            return
        
        # Approve the payment
        await query.answer(ok=True)
    
    elif payload == "feature_bundle":
        # Check stock availability
        if await check_bundle_availability():
            await query.answer(ok=True)
        else:
            await query.answer(
                ok=False,
                error_message="Bundle is currently out of stock"
            )
    
    else:
        # Unknown payload
        await query.answer(
            ok=False,
            error_message="Invalid payment request"
        )
```

### Processing Successful Payment
```python
from aiogram.types import Message
from datetime import datetime, timedelta

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    payment = message.successful_payment
    
    # Extract payment details
    user_id = message.from_user.id
    payment_charge_id = payment.telegram_payment_charge_id
    amount = payment.total_amount
    currency = payment.currency
    payload = payment.invoice_payload
    
    # Process based on payload
    if payload == "premium_subscription_30d":
        # Activate subscription
        expires_at = datetime.now() + timedelta(days=30)
        
        # Save to database
        await activate_subscription(
            user_id=user_id,
            charge_id=payment_charge_id,
            expires_at=expires_at
        )
        
        await message.answer(
            "✅ Payment successful!\n"
            f"Your premium subscription is active until {expires_at.strftime('%Y-%m-%d')}"
        )
    
    elif payload == "feature_bundle":
        # Unlock features
        await unlock_bundle_features(user_id)
        
        await message.answer(
            "✅ Payment successful!\n"
            "All bundle features have been unlocked!"
        )
    
    # Optional: Send receipt or confirmation
    await send_payment_receipt(user_id, payment_charge_id, amount)
```

### Refunding Stars Payment
```python
@router.message(Command("refund"))
async def process_refund(message: Message, bot: Bot):
    # Get user's last payment
    user_id = message.from_user.id
    last_payment = await get_last_payment(user_id)
    
    if not last_payment:
        await message.answer("No recent payments found")
        return
    
    try:
        # Refund the payment
        await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=last_payment['charge_id']
        )
        
        # Update database
        await mark_payment_refunded(last_payment['id'])
        
        await message.answer("✅ Payment has been refunded successfully")
    
    except Exception as e:
        await message.answer(f"❌ Refund failed: {str(e)}")
```

## Webhook Setup

### Basic Webhook Configuration
```python
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Webhook settings
WEBHOOK_HOST = 'https://your-domain.com'
WEBHOOK_PATH = '/webhook'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Web app settings
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = 8080

async def on_startup(bot: Bot):
    # Set webhook
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True  # Skip old updates
    )

async def on_shutdown(bot: Bot):
    # Remove webhook
    await bot.delete_webhook()

def main():
    # Create bot and dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Register routers
    dp.include_router(router)
    
    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Create web application
    app = web.Application()
    
    # Create webhook handler
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    )
    
    # Register webhook handler
    webhook_handler.register(app, path=WEBHOOK_PATH)
    
    # Setup application
    setup_application(app, dp, bot=bot)
    
    # Start web server
    web.run_app(
        app,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )

if __name__ == '__main__':
    main()
```

### Advanced Webhook with SSL
```python
import ssl

# SSL context for self-signed certificate
def create_ssl_context():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain('path/to/cert.pem', 'path/to/private.key')
    return context

async def set_webhook_with_certificate(bot: Bot):
    # Read certificate
    with open('path/to/public.pem', 'rb') as cert_file:
        certificate = BufferedInputFile(
            cert_file.read(),
            filename='certificate'
        )
    
    # Set webhook with certificate
    await bot.set_webhook(
        url=WEBHOOK_URL,
        certificate=certificate,
        max_connections=40,
        drop_pending_updates=True,
        allowed_updates=['message', 'callback_query', 'pre_checkout_query']
    )

# Run with SSL
web.run_app(
    app,
    host=WEBAPP_HOST,
    port=WEBAPP_PORT,
    ssl_context=create_ssl_context()
)
```

### Webhook Info and Management
```python
@router.message(Command("webhook_info"))
async def get_webhook_info(message: Message, bot: Bot):
    info = await bot.get_webhook_info()
    
    info_text = f"""
    Webhook Info:
    URL: {info.url or 'Not set'}
    Pending updates: {info.pending_update_count}
    Max connections: {info.max_connections}
    Last error: {info.last_error_message or 'None'}
    """
    
    await message.answer(info_text)

@router.message(Command("reset_webhook"))
async def reset_webhook(message: Message, bot: Bot):
    # Delete current webhook
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Set new webhook
    await bot.set_webhook(
        url=WEBHOOK_URL,
        drop_pending_updates=True
    )
    
    await message.answer("Webhook has been reset")
```

## Best Practices

### Error Handling
```python
from aiogram.exceptions import TelegramBadRequest

@router.message()
async def safe_message_handler(message: Message):
    try:
        await message.answer("Processing...")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass  # Ignore if message wasn't changed
        elif "message to delete not found" in str(e):
            pass  # Message already deleted
        else:
            logger.error(f"Telegram error: {e}")
```

### Middleware for Logging
```python
from aiogram import BaseMiddleware
from typing import Any, Awaitable, Callable, Dict

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user = event.from_user
        logger.info(f"User {user.id} ({user.username}) sent: {event.text}")
        
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"Error handling message from {user.id}: {e}")
            raise

# Register middleware
dp.message.middleware(LoggingMiddleware())
```

### Rate Limiting
```python
from aiogram import BaseMiddleware
from cachetools import TTLCache

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: int = 5):
        self.cache = TTLCache(maxsize=10000, ttl=60)
        self.rate_limit = rate_limit
    
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        
        # Check rate limit
        if user_id in self.cache:
            if self.cache[user_id] >= self.rate_limit:
                await event.answer("Too many requests. Please wait...")
                return
            self.cache[user_id] += 1
        else:
            self.cache[user_id] = 1
        
        return await handler(event, data)
```

## Important Migration Notes (v2 to v3)

1. **Dispatcher changes**: No longer accepts Bot instance in initializer
2. **Handler decorators**: Removed `_handler` suffix (e.g., `@dp.message()` instead of `@dp.message_handler()`)
3. **Filters**: Use `F` for magic filters instead of lambda functions
4. **State filters**: Must be explicitly specified, not automatically added
5. **Keyboard builders**: Use `InlineKeyboardBuilder` instead of markup methods
6. **Async everywhere**: All handlers and bot methods are async

## Additional Resources

- Official Documentation: https://docs.aiogram.dev/
- GitHub Repository: https://github.com/aiogram/aiogram
- Examples: https://github.com/aiogram/aiogram/tree/dev-3.x/examples
- Community: https://t.me/aiogram_ru (Russian), https://t.me/aiogram (English)
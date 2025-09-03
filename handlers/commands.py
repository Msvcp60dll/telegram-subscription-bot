"""
Command Handlers Module
Handles basic bot commands like /start, /help, /status, /subscribe
"""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, html, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

# Create router for command handlers
router = Router(name="commands")

# Import config from main
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os

# Configuration
GROUP_ID = int(os.getenv("GROUP_ID", "-1002384609773"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "306145881"))

# In-memory storage for user subscriptions (replace with database in production)
# Format: {user_id: {"expires_at": datetime, "plan": str, "transaction_id": str}}
user_subscriptions = {}

# Whitelist for grandfathered users (replace with database in production)
whitelisted_users = set()

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="Subscribe", callback_data="menu_subscribe")
    builder.button(text="Check Status", callback_data="menu_status")
    builder.button(text="Help", callback_data="menu_help")
    builder.button(text="Support", url="https://t.me/username")  # Replace with support link
    
    builder.adjust(2, 2)  # 2 buttons per row
    return builder.as_markup()

def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Create subscription options keyboard"""
    builder = InlineKeyboardBuilder()
    
    # Add subscription plans
    for plan_id, plan_info in config["subscription_plans"].items():
        builder.button(
            text=f"{plan_info['stars']} Stars - {plan_info['name']}",
            callback_data=f"plan_{plan_id}"
        )
    
    # Add payment method selection
    builder.button(text="Pay with Card (Airwallex)", callback_data="pay_card")
    builder.button(text="Back to Menu", callback_data="back_main")
    
    builder.adjust(1)  # 1 button per row
    return builder.as_markup()

async def check_user_in_group(bot: Bot, user_id: int) -> bool:
    """Check if user is member of the group"""
    try:
        member = await bot.get_chat_member(GROUP_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Failed to check user {user_id} in group: {e}")
        return False

async def check_user_subscription(user_id: int) -> Optional[dict]:
    """Check if user has active subscription"""
    if user_id in whitelisted_users:
        return {"status": "whitelisted", "expires_at": None}
    
    if user_id in user_subscriptions:
        sub = user_subscriptions[user_id]
        if sub["expires_at"] > datetime.now():
            return sub
        else:
            # Subscription expired, remove from dict
            del user_subscriptions[user_id]
    
    return None

@router.message(CommandStart())
async def command_start_handler(message: Message, bot: Bot):
    """Handle /start command"""
    user = message.from_user
    logger.info(f"User {user.id} (@{user.username}) started bot")
    
    # Check if user is in group
    is_member = await check_user_in_group(bot, user.id)
    
    # Create personalized welcome message
    welcome_text = f"""
Welcome, {html.bold(user.full_name)}!

This bot manages access to our exclusive Telegram group.

"""
    
    if is_member:
        # Check subscription status
        subscription = await check_user_subscription(user.id)
        if subscription:
            if subscription.get("status") == "whitelisted":
                welcome_text += "You have lifetime access to the group!"
            else:
                expires = subscription["expires_at"].strftime("%Y-%m-%d %H:%M")
                welcome_text += f"Your subscription is active until: {html.code(expires)}"
        else:
            welcome_text += "You're in the group but don't have an active subscription.\nPlease subscribe to maintain access."
    else:
        welcome_text += """You're not currently in our group.
Subscribe now to get instant access to:
• Exclusive content
• Priority support
• Community discussions
• Premium features"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard()
    )

@router.message(Command("subscribe"))
async def command_subscribe_handler(message: Message):
    """Handle /subscribe command"""
    logger.info(f"User {message.from_user.id} requested subscription options")
    
    subscription_text = """
<b>Available Subscription Plans:</b>

<b>Basic</b> - 50 Stars
• 7 days access
• Perfect for trying out

<b>Standard</b> - 100 Stars
• 30 days access
• Most popular choice

<b>Premium</b> - 500 Stars
• 180 days access
• Best value!

Choose your preferred plan below:
"""
    
    await message.answer(
        subscription_text,
        reply_markup=get_subscription_keyboard()
    )

@router.message(Command("status"))
async def command_status_handler(message: Message, bot: Bot):
    """Handle /status command"""
    user_id = message.from_user.id
    logger.info(f"User {user_id} checking status")
    
    # Check group membership
    is_member = await check_user_in_group(bot, user_id)
    
    # Check subscription
    subscription = await check_user_subscription(user_id)
    
    status_text = f"<b>Your Status</b>\n\n"
    status_text += f"User ID: {html.code(str(user_id))}\n"
    status_text += f"Group Access: {'✅ Active' if is_member else '❌ Not a member'}\n"
    
    if subscription:
        if subscription.get("status") == "whitelisted":
            status_text += "Subscription: ✅ Lifetime access\n"
        else:
            expires = subscription["expires_at"].strftime("%Y-%m-%d %H:%M")
            days_left = (subscription["expires_at"] - datetime.now()).days
            status_text += f"Subscription: ✅ Active\n"
            status_text += f"Plan: {subscription.get('plan', 'Unknown')}\n"
            status_text += f"Expires: {html.code(expires)}\n"
            status_text += f"Days remaining: {days_left}\n"
    else:
        status_text += "Subscription: ❌ Not active\n"
    
    keyboard = InlineKeyboardBuilder()
    if not subscription:
        keyboard.button(text="Subscribe Now", callback_data="menu_subscribe")
    keyboard.button(text="Refresh Status", callback_data="refresh_status")
    keyboard.adjust(1)
    
    await message.answer(status_text, reply_markup=keyboard.as_markup())

@router.message(Command("help"))
async def command_help_handler(message: Message):
    """Handle /help command"""
    logger.info(f"User {message.from_user.id} requested help")
    
    help_text = """
<b>Available Commands:</b>

/start - Start the bot and see main menu
/subscribe - View subscription plans
/status - Check your subscription status
/help - Show this help message
/admin - Admin panel (admins only)

<b>How to Subscribe:</b>
1. Choose a subscription plan
2. Select payment method:
   • Telegram Stars (instant)
   • Card payment via Airwallex
3. Complete the payment
4. Get instant access to the group!

<b>Payment Methods:</b>
• <b>Telegram Stars</b> - Quick and easy payment within Telegram
• <b>Card Payment</b> - Secure payment via Airwallex

<b>Need Help?</b>
Contact our support: @username

<b>Frequently Asked Questions:</b>

Q: How do I get Telegram Stars?
A: You can purchase Stars directly in Telegram settings.

Q: Can I cancel my subscription?
A: Subscriptions are one-time purchases, not recurring.

Q: I paid but didn't get access?
A: Contact support with your payment details.
"""
    
    await message.answer(help_text, reply_markup=get_main_keyboard())

@router.message(Command("admin"))
async def command_admin_handler(message: Message):
    """Handle /admin command - only for administrators"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        await message.answer("❌ You don't have permission to use this command.")
        logger.warning(f"Unauthorized admin access attempt by user {user_id}")
        return
    
    logger.info(f"Admin {user_id} accessed admin panel")
    
    admin_text = """
<b>Admin Panel</b>

Welcome to the admin control panel.
Choose an action from the menu below:
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="View Statistics", callback_data="admin_stats")
    builder.button(text="Manage Users", callback_data="admin_users")
    builder.button(text="Add to Whitelist", callback_data="admin_whitelist_add")
    builder.button(text="Remove from Whitelist", callback_data="admin_whitelist_remove")
    builder.button(text="View Subscriptions", callback_data="admin_subs")
    builder.button(text="Send Broadcast", callback_data="admin_broadcast")
    builder.adjust(2)
    
    await message.answer(admin_text, reply_markup=builder.as_markup())

# Callback query handlers for menu navigation
@router.callback_query(lambda c: c.data == "menu_subscribe")
async def callback_menu_subscribe(callback: Message):
    """Handle subscribe menu callback"""
    await callback.answer()
    
    subscription_text = """
<b>Available Subscription Plans:</b>

<b>Basic</b> - 50 Stars
• 7 days access
• Perfect for trying out

<b>Standard</b> - 100 Stars
• 30 days access
• Most popular choice

<b>Premium</b> - 500 Stars
• 180 days access
• Best value!

Choose your preferred plan below:
"""
    
    try:
        await callback.message.edit_text(
            subscription_text,
            reply_markup=get_subscription_keyboard()
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

@router.callback_query(lambda c: c.data == "menu_status")
async def callback_menu_status(callback: Message, bot: Bot):
    """Handle status menu callback"""
    await callback.answer()
    user_id = callback.from_user.id
    
    # Check group membership
    is_member = await check_user_in_group(bot, user_id)
    
    # Check subscription
    subscription = await check_user_subscription(user_id)
    
    status_text = f"<b>Your Status</b>\n\n"
    status_text += f"User ID: {html.code(str(user_id))}\n"
    status_text += f"Group Access: {'✅ Active' if is_member else '❌ Not a member'}\n"
    
    if subscription:
        if subscription.get("status") == "whitelisted":
            status_text += "Subscription: ✅ Lifetime access\n"
        else:
            expires = subscription["expires_at"].strftime("%Y-%m-%d %H:%M")
            days_left = (subscription["expires_at"] - datetime.now()).days
            status_text += f"Subscription: ✅ Active\n"
            status_text += f"Plan: {subscription.get('plan', 'Unknown')}\n"
            status_text += f"Expires: {html.code(expires)}\n"
            status_text += f"Days remaining: {days_left}\n"
    else:
        status_text += "Subscription: ❌ Not active\n"
    
    keyboard = InlineKeyboardBuilder()
    if not subscription:
        keyboard.button(text="Subscribe Now", callback_data="menu_subscribe")
    keyboard.button(text="Back to Menu", callback_data="back_main")
    keyboard.adjust(1)
    
    try:
        await callback.message.edit_text(status_text, reply_markup=keyboard.as_markup())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

@router.callback_query(lambda c: c.data == "menu_help")
async def callback_menu_help(callback: Message):
    """Handle help menu callback"""
    await callback.answer()
    
    help_text = """
<b>Quick Help</b>

• To subscribe: Click "Subscribe" and choose a plan
• Payment methods: Stars or Card
• Check status: Click "Check Status"
• Contact support: @username

For detailed help, use /help command.
"""
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Back to Menu", callback_data="back_main")
    
    try:
        await callback.message.edit_text(help_text, reply_markup=keyboard.as_markup())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

@router.callback_query(lambda c: c.data == "back_main")
async def callback_back_main(callback: Message):
    """Handle back to main menu callback"""
    await callback.answer()
    
    user = callback.from_user
    welcome_text = f"""
Welcome back, {html.bold(user.full_name)}!

What would you like to do?
"""
    
    try:
        await callback.message.edit_text(
            welcome_text,
            reply_markup=get_main_keyboard()
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            logger.error(f"Failed to edit message: {e}")

@router.callback_query(lambda c: c.data == "refresh_status")
async def callback_refresh_status(callback: Message, bot: Bot):
    """Handle refresh status callback"""
    await callback.answer("Refreshing status...")
    
    # Reuse the status callback handler
    await callback_menu_status(callback, bot)
"""
Admin Handlers Module
Handles administrative functions like user management, statistics, and broadcasts
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from aiogram import Router, Bot, F, html
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

logger = logging.getLogger(__name__)

# Create router for admin handlers
router = Router(name="admin")

# Import config and shared data
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os

# Configuration
GROUP_ID = int(os.getenv("GROUP_ID", "-1002384609773"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "306145881"))
from handlers.commands import user_subscriptions, whitelisted_users
from handlers.payments import remove_user_from_group, add_user_to_group

# FSM States for admin actions
class AdminStates(StatesGroup):
    adding_whitelist = State()
    removing_whitelist = State()
    composing_broadcast = State()
    confirming_broadcast = State()
    managing_user = State()

# Admin check decorator/filter
def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == ADMIN_USER_ID

# Statistics tracking (in production, use database)
bot_stats = {
    "total_users": 0,
    "active_subscriptions": 0,
    "total_revenue": 0,
    "messages_sent": 0
}

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin panel keyboard"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Statistics", callback_data="admin_stats")
    builder.button(text="👥 Manage Users", callback_data="admin_users")
    builder.button(text="➕ Add to Whitelist", callback_data="admin_whitelist_add")
    builder.button(text="➖ Remove from Whitelist", callback_data="admin_whitelist_remove")
    builder.button(text="📋 View Subscriptions", callback_data="admin_subs")
    builder.button(text="📢 Send Broadcast", callback_data="admin_broadcast")
    builder.button(text="🔄 Refresh Stats", callback_data="admin_refresh")
    builder.button(text="❌ Close", callback_data="admin_close")
    builder.adjust(2)
    return builder.as_markup()

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Show bot statistics"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    # Calculate statistics
    active_subs = len([s for s in user_subscriptions.values() 
                       if s.get("expires_at", datetime.min) > datetime.now()])
    
    total_revenue = sum([s.get("amount", 0) for s in user_subscriptions.values()])
    
    stats_text = f"""
<b>📊 Bot Statistics</b>

<b>Users:</b>
• Active Subscriptions: {active_subs}
• Whitelisted Users: {len(whitelisted_users)}
• Total Users: {len(user_subscriptions) + len(whitelisted_users)}

<b>Revenue:</b>
• Total Stars Collected: {total_revenue}
• Average per User: {total_revenue / max(len(user_subscriptions), 1):.1f}

<b>Subscriptions by Plan:</b>
• Basic (7d): {len([s for s in user_subscriptions.values() if "Basic" in s.get("plan", "")])}
• Standard (30d): {len([s for s in user_subscriptions.values() if "Standard" in s.get("plan", "")])}
• Premium (180d): {len([s for s in user_subscriptions.values() if "Premium" in s.get("plan", "")])}

<b>System:</b>
• Bot Started: {datetime.now().strftime('%Y-%m-%d %H:%M')}
• Group ID: {html.code(str(GROUP_ID))}

Last updated: {datetime.now().strftime('%H:%M:%S')}
"""
    
    try:
        await callback.message.edit_text(stats_text, reply_markup=get_admin_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(stats_text, reply_markup=get_admin_keyboard())

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users_handler(callback: CallbackQuery, state: FSMContext):
    """Manage users"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.managing_user)
    
    text = """
<b>👥 User Management</b>

Send me a user ID to view their details and manage their subscription.

Example: <code>123456789</code>

Or choose an action below:
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="View All Subscriptions", callback_data="admin_subs")
    builder.button(text="View Whitelisted", callback_data="admin_whitelist_view")
    builder.button(text="Cancel", callback_data="admin_cancel")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.message(AdminStates.managing_user)
async def process_user_management(message: Message, state: FSMContext, bot: Bot):
    """Process user ID for management"""
    if not is_admin(message.from_user.id):
        return
    
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid user ID. Please send a number.")
        return
    
    # Get user info
    try:
        user_info = await bot.get_chat(target_user_id)
        user_name = user_info.full_name
        username = f"@{user_info.username}" if user_info.username else "No username"
    except:
        user_name = "Unknown"
        username = "Unknown"
    
    # Check subscription status
    is_whitelisted = target_user_id in whitelisted_users
    subscription = user_subscriptions.get(target_user_id)
    
    text = f"""
<b>User Information</b>

<b>ID:</b> {html.code(str(target_user_id))}
<b>Name:</b> {html.escape(user_name)}
<b>Username:</b> {username}

<b>Status:</b>
"""
    
    if is_whitelisted:
        text += "✅ Whitelisted (Lifetime access)\n"
    elif subscription:
        expires = subscription["expires_at"].strftime('%Y-%m-%d %H:%M')
        days_left = (subscription["expires_at"] - datetime.now()).days
        text += f"✅ Active Subscription\n"
        text += f"Plan: {subscription['plan']}\n"
        text += f"Expires: {expires}\n"
        text += f"Days left: {days_left}\n"
        if "transaction_id" in subscription:
            text += f"Transaction: {html.code(subscription['transaction_id'])}\n"
    else:
        text += "❌ No active subscription\n"
    
    text += "\nChoose an action:"
    
    builder = InlineKeyboardBuilder()
    
    if not is_whitelisted:
        builder.button(text="Add to Whitelist", callback_data=f"admin_wl_add_{target_user_id}")
    else:
        builder.button(text="Remove from Whitelist", callback_data=f"admin_wl_del_{target_user_id}")
    
    if subscription:
        builder.button(text="Extend Subscription", callback_data=f"admin_extend_{target_user_id}")
        builder.button(text="Cancel Subscription", callback_data=f"admin_cancel_sub_{target_user_id}")
        if "transaction_id" in subscription:
            builder.button(text="Refund Payment", callback_data=f"admin_refund_{target_user_id}")
    
    builder.button(text="Remove from Group", callback_data=f"admin_remove_{target_user_id}")
    builder.button(text="Send Invite Link", callback_data=f"admin_invite_{target_user_id}")
    builder.button(text="Back", callback_data="admin_users")
    builder.adjust(1)
    
    await state.clear()
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data == "admin_whitelist_add")
async def admin_whitelist_add_handler(callback: CallbackQuery, state: FSMContext):
    """Start adding user to whitelist"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.adding_whitelist)
    
    text = """
<b>➕ Add to Whitelist</b>

Send me the user ID to add to whitelist.
Whitelisted users have lifetime access without payment.

Example: <code>123456789</code>

Send /cancel to cancel.
"""
    
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

@router.message(AdminStates.adding_whitelist)
async def process_whitelist_add(message: Message, state: FSMContext, bot: Bot):
    """Process adding user to whitelist"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=get_admin_keyboard())
        return
    
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid user ID. Please send a number.")
        return
    
    # Add to whitelist
    whitelisted_users.add(target_user_id)
    
    # Try to add to group
    added = await add_user_to_group(bot, target_user_id)
    
    await state.clear()
    
    status = "✅ Added to group" if added else "⚠️ Could not add to group (send invite manually)"
    
    await message.answer(
        f"✅ User {target_user_id} added to whitelist!\n{status}",
        reply_markup=get_admin_keyboard()
    )
    
    logger.info(f"Admin {message.from_user.id} added user {target_user_id} to whitelist")

@router.callback_query(lambda c: c.data == "admin_whitelist_remove")
async def admin_whitelist_remove_handler(callback: CallbackQuery, state: FSMContext):
    """Start removing user from whitelist"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    if not whitelisted_users:
        await callback.message.answer("No users in whitelist.")
        return
    
    await state.set_state(AdminStates.removing_whitelist)
    
    text = f"""
<b>➖ Remove from Whitelist</b>

Current whitelisted users:
{chr(10).join([f'• {uid}' for uid in whitelisted_users])}

Send the user ID to remove from whitelist.

Send /cancel to cancel.
"""
    
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

@router.message(AdminStates.removing_whitelist)
async def process_whitelist_remove(message: Message, state: FSMContext, bot: Bot):
    """Process removing user from whitelist"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=get_admin_keyboard())
        return
    
    try:
        target_user_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Invalid user ID. Please send a number.")
        return
    
    if target_user_id not in whitelisted_users:
        await message.answer("❌ User not in whitelist.")
        return
    
    # Remove from whitelist
    whitelisted_users.discard(target_user_id)
    
    # Remove from group
    removed = await remove_user_from_group(bot, target_user_id)
    
    await state.clear()
    
    status = "✅ Removed from group" if removed else "⚠️ Could not remove from group"
    
    await message.answer(
        f"✅ User {target_user_id} removed from whitelist!\n{status}",
        reply_markup=get_admin_keyboard()
    )
    
    logger.info(f"Admin {message.from_user.id} removed user {target_user_id} from whitelist")

@router.callback_query(lambda c: c.data == "admin_subs")
async def admin_view_subscriptions(callback: CallbackQuery):
    """View all active subscriptions"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    if not user_subscriptions:
        text = "<b>📋 No active subscriptions</b>"
    else:
        text = "<b>📋 Active Subscriptions</b>\n\n"
        
        for uid, sub in list(user_subscriptions.items())[:20]:  # Limit to 20 for message length
            expires = sub["expires_at"].strftime('%Y-%m-%d')
            days_left = (sub["expires_at"] - datetime.now()).days
            
            if days_left < 0:
                status = "❌ Expired"
            elif days_left <= 3:
                status = "⚠️ Expiring soon"
            else:
                status = "✅ Active"
            
            text += f"• {uid}: {sub['plan']} - {expires} ({days_left}d) {status}\n"
        
        if len(user_subscriptions) > 20:
            text += f"\n... and {len(user_subscriptions) - 20} more"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Export CSV", callback_data="admin_export")
    builder.button(text="Back", callback_data="admin_back")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    """Start broadcast message composition"""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(AdminStates.composing_broadcast)
    
    text = """
<b>📢 Broadcast Message</b>

Send me the message you want to broadcast to all users with active subscriptions.

You can use HTML formatting:
• <code>&lt;b&gt;bold&lt;/b&gt;</code>
• <code>&lt;i&gt;italic&lt;/i&gt;</code>
• <code>&lt;code&gt;code&lt;/code&gt;</code>

Send /cancel to cancel.
"""
    
    try:
        await callback.message.edit_text(text)
    except TelegramBadRequest:
        await callback.message.answer(text)

@router.message(AdminStates.composing_broadcast)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Process broadcast message"""
    if not is_admin(message.from_user.id):
        return
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Broadcast cancelled.", reply_markup=get_admin_keyboard())
        return
    
    # Save message to state
    await state.update_data(broadcast_text=message.text or message.caption)
    await state.set_state(AdminStates.confirming_broadcast)
    
    # Show preview
    recipients = len(user_subscriptions) + len(whitelisted_users)
    
    preview_text = f"""
<b>📢 Broadcast Preview</b>

<b>Recipients:</b> {recipients} users

<b>Message:</b>
{message.text or message.caption}

Send this message to all users?
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Send", callback_data="admin_broadcast_send")
    builder.button(text="❌ Cancel", callback_data="admin_broadcast_cancel")
    builder.adjust(2)
    
    await message.answer(preview_text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data == "admin_broadcast_send")
async def send_broadcast(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Send broadcast to all users"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Sending broadcast...")
    
    data = await state.get_data()
    broadcast_text = data.get("broadcast_text")
    
    if not broadcast_text:
        await callback.message.edit_text("❌ No message to send.")
        await state.clear()
        return
    
    # Collect all user IDs
    all_users = set(user_subscriptions.keys()) | whitelisted_users
    
    sent = 0
    failed = 0
    
    # Update message
    await callback.message.edit_text(f"📤 Sending to {len(all_users)} users...")
    
    # Send to all users
    for user_id in all_users:
        try:
            await bot.send_message(user_id, broadcast_text)
            sent += 1
        except TelegramForbiddenError:
            # User blocked bot
            failed += 1
            logger.info(f"User {user_id} has blocked the bot")
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user_id}: {e}")
        
        # Update progress every 10 users
        if (sent + failed) % 10 == 0:
            try:
                await callback.message.edit_text(
                    f"📤 Progress: {sent + failed}/{len(all_users)}\n"
                    f"✅ Sent: {sent}\n❌ Failed: {failed}"
                )
            except:
                pass
    
    await state.clear()
    
    # Final report
    report = f"""
<b>📢 Broadcast Complete</b>

✅ Successfully sent: {sent}
❌ Failed: {failed}
📊 Total: {len(all_users)}
🎯 Success rate: {(sent/len(all_users)*100):.1f}%
"""
    
    await callback.message.edit_text(report, reply_markup=get_admin_keyboard())
    logger.info(f"Broadcast completed: {sent} sent, {failed} failed")

@router.callback_query(lambda c: c.data == "admin_broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Broadcast cancelled")
    await state.clear()
    
    await callback.message.edit_text(
        "Broadcast cancelled.",
        reply_markup=get_admin_keyboard()
    )

# Callback handlers for user management actions
@router.callback_query(lambda c: c.data and c.data.startswith("admin_wl_add_"))
async def callback_whitelist_add_user(callback: CallbackQuery, bot: Bot):
    """Add specific user to whitelist"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    target_user_id = int(callback.data.split("_")[3])
    
    whitelisted_users.add(target_user_id)
    added = await add_user_to_group(bot, target_user_id)
    
    status = "and added to group" if added else "but could not add to group"
    
    await callback.answer(f"✅ User whitelisted {status}", show_alert=True)
    
    # Refresh the user info
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(lambda c: c.data and c.data.startswith("admin_remove_"))
async def callback_remove_from_group(callback: CallbackQuery, bot: Bot):
    """Remove user from group"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    target_user_id = int(callback.data.split("_")[2])
    
    removed = await remove_user_from_group(bot, target_user_id)
    
    if removed:
        await callback.answer("✅ User removed from group", show_alert=True)
    else:
        await callback.answer("❌ Failed to remove user", show_alert=True)

@router.callback_query(lambda c: c.data and c.data.startswith("admin_invite_"))
async def callback_send_invite(callback: CallbackQuery, bot: Bot):
    """Send invite link to user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    target_user_id = int(callback.data.split("_")[2])
    
    added = await add_user_to_group(bot, target_user_id)
    
    if added:
        await callback.answer("✅ Invite link sent to user", show_alert=True)
    else:
        await callback.answer("❌ Failed to send invite", show_alert=True)

@router.callback_query(lambda c: c.data == "admin_back")
async def admin_back_handler(callback: CallbackQuery):
    """Go back to admin menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    
    text = """
<b>Admin Panel</b>

Welcome to the admin control panel.
Choose an action from the menu below:
"""
    
    try:
        await callback.message.edit_text(text, reply_markup=get_admin_keyboard())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=get_admin_keyboard())

@router.callback_query(lambda c: c.data == "admin_close")
async def admin_close_handler(callback: CallbackQuery):
    """Close admin panel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.delete()

@router.callback_query(lambda c: c.data == "admin_cancel")
async def admin_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current admin action"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Unauthorized", show_alert=True)
        return
    
    await callback.answer("Action cancelled")
    await state.clear()
    
    await callback.message.edit_text(
        "Action cancelled.",
        reply_markup=get_admin_keyboard()
    )
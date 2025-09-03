"""
Payment Handlers Module
Handles payment flows including Stars payments and Airwallex integration
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
import hashlib
import secrets
import os

from aiogram import Router, Bot, F, html
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, 
    PreCheckoutQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

logger = logging.getLogger(__name__)

# Create router for payment handlers
router = Router(name="payments")

# Import config and shared data
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os

# Configuration
GROUP_ID = int(os.getenv("GROUP_ID", "-1002384609773"))
from handlers.commands import user_subscriptions
from services.payment_processor import PaymentProcessor, PaymentMethod, PaymentStatus

# Initialize payment processor (will be set from main.py)
payment_processor: Optional[PaymentProcessor] = None

def set_payment_processor(processor: PaymentProcessor):
    """Set the payment processor instance"""
    global payment_processor
    payment_processor = processor
    logger.info("Payment processor configured in payment handlers")

# FSM States for payment flow
class PaymentStates(StatesGroup):
    selecting_plan = State()
    selecting_method = State()
    processing_payment = State()
    awaiting_confirmation = State()

# Temporary storage for pending payments (managed by PaymentProcessor)
pending_payments = {}  # Keep for backward compatibility

def generate_payment_id(user_id: int) -> str:
    """Generate unique payment ID"""
    timestamp = datetime.now().timestamp()
    random_part = secrets.token_hex(4)
    return f"{user_id}_{int(timestamp)}_{random_part}"

async def add_user_to_group(bot: Bot, user_id: int) -> bool:
    """Add user to the group after successful payment"""
    try:
        # Generate invite link
        invite_link = await bot.create_chat_invite_link(
            GROUP_ID,
            member_limit=1,  # Single use
            expire_date=datetime.now() + timedelta(minutes=30)
        )
        
        # Send invite link to user
        await bot.send_message(
            user_id,
            f"✅ Payment successful! Here's your exclusive invite link:\n{invite_link.invite_link}\n\n"
            "This link expires in 30 minutes and can only be used once."
        )
        
        logger.info(f"Created invite link for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create invite link for user {user_id}: {e}")
        
        # Alternative: Try to approve join request if bot has permission
        try:
            await bot.approve_chat_join_request(GROUP_ID, user_id)
            logger.info(f"Approved join request for user {user_id}")
            return True
        except:
            pass
    
    return False

async def remove_user_from_group(bot: Bot, user_id: int) -> bool:
    """Remove user from group when subscription expires"""
    try:
        await bot.ban_chat_member(GROUP_ID, user_id)
        await bot.unban_chat_member(GROUP_ID, user_id)  # Unban so they can rejoin later
        logger.info(f"Removed user {user_id} from group")
        return True
    except Exception as e:
        logger.error(f"Failed to remove user {user_id} from group: {e}")
        return False

# Callback handlers for subscription plans
@router.callback_query(lambda c: c.data and c.data.startswith("plan_"))
async def process_plan_selection(callback: CallbackQuery, state: FSMContext):
    """Handle plan selection"""
    await callback.answer()
    
    plan_id = callback.data.split("_")[1]
    
    if plan_id not in config["subscription_plans"]:
        await callback.message.answer("❌ Invalid plan selected")
        return
    
    plan = config["subscription_plans"][plan_id]
    user_id = callback.from_user.id
    
    # Save plan selection to state
    await state.update_data(
        plan_id=plan_id,
        plan_stars=plan["stars"],
        plan_days=plan["days"],
        plan_name=plan["name"]
    )
    await state.set_state(PaymentStates.selecting_method)
    
    # Show payment method selection
    text = f"""
<b>Selected Plan:</b> {plan['name']}
<b>Price:</b> {plan['stars']} Stars
<b>Duration:</b> {plan['days']} days

Select your payment method:
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"Pay {plan['stars']} Stars", callback_data=f"pay_stars_{plan_id}")
    builder.button(text="Pay with Card (Airwallex)", callback_data=f"pay_card_{plan_id}")
    builder.button(text="Cancel", callback_data="cancel_payment")
    builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data and c.data.startswith("pay_stars_"))
async def process_stars_payment(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Process Telegram Stars payment"""
    await callback.answer()
    
    plan_id = callback.data.split("_")[2]
    plan = config["subscription_plans"][plan_id]
    user_id = callback.from_user.id
    
    # Create payment session if payment processor is available
    session_id = None
    if payment_processor:
        session_id = await payment_processor.create_payment_session(
            user_id=user_id,
            plan_id=plan_id,
            plan_details=plan,
            user_info={
                "username": callback.from_user.username,
                "name": callback.from_user.full_name
            }
        )
        
        # Process Stars payment
        success, result = await payment_processor.process_stars_payment(session_id)
        payment_id = result.get('invoice_payload', session_id) if success else generate_payment_id(user_id)
    else:
        # Fallback to old system
        payment_id = generate_payment_id(user_id)
    
    # Store payment info for backward compatibility
    pending_payments[payment_id] = {
        "user_id": user_id,
        "plan_id": plan_id,
        "plan": plan,
        "created_at": datetime.now(),
        "session_id": session_id  # Link to payment processor session
    }
    
    await state.set_state(PaymentStates.processing_payment)
    
    # Send invoice for Stars payment
    try:
        await bot.send_invoice(
            chat_id=user_id,
            title=f"Subscription: {plan['name']}",
            description=f"Get {plan['days']} days of premium access to our exclusive group",
            prices=[
                LabeledPrice(label=plan['name'], amount=plan['stars'])
            ],
            payload=payment_id,  # Use payment_id as payload for tracking
            currency="XTR",  # Telegram Stars currency
            provider_token="",  # Empty for Stars
            start_parameter=f"sub_{plan_id}",
            photo_url="https://telegram.org/img/t_logo.png",  # Optional: Add your logo
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            protect_content=True
        )
        
        await callback.message.edit_text(
            "Invoice sent! Please check your messages and complete the payment."
        )
        
    except Exception as e:
        logger.error(f"Failed to send invoice to user {user_id}: {e}")
        await callback.message.edit_text(
            "❌ Failed to create invoice. Please try again or contact support."
        )
        await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("pay_card_"))
async def process_card_payment(callback: CallbackQuery, state: FSMContext):
    """Process card payment via Airwallex"""
    await callback.answer()
    
    plan_id = callback.data.split("_")[2]
    plan = config["subscription_plans"][plan_id]
    user_id = callback.from_user.id
    
    # Check if payment processor is available
    if not payment_processor:
        await callback.message.answer("❌ Payment service not available. Please try Stars payment.")
        return
    
    # Create payment session
    session_id = await payment_processor.create_payment_session(
        user_id=user_id,
        plan_id=plan_id,
        plan_details=plan,
        user_info={
            "username": callback.from_user.username,
            "name": callback.from_user.full_name
        }
    )
    
    # Get webhook URL if configured
    webhook_base = os.getenv("WEBHOOK_BASE_URL")
    webhook_url = f"{webhook_base}/webhook/airwallex" if webhook_base else None
    
    # Process card payment
    success, result = await payment_processor.process_card_payment(
        session_id=session_id,
        webhook_url=webhook_url
    )
    
    if success:
        # Payment link created successfully
        text = f"""
💳 <b>Card Payment</b>

Plan: {plan['name']}
Price: ${result.get('amount_usd', plan['stars'] * 0.02):.2f} USD
Duration: {plan['days']} days

Click the button below to complete your payment securely via Airwallex.

⏱ This payment link expires in 24 hours.
"""
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔒 Pay Now", url=result['payment_url'])
        builder.button(text="✅ I've Paid", callback_data=f"confirm_card_{session_id}")
        builder.button(text="⭐ Use Stars Instead", callback_data=f"pay_stars_{plan_id}")
        builder.button(text="❌ Cancel", callback_data="cancel_payment")
        builder.adjust(1)
        
        await state.set_state(PaymentStates.awaiting_confirmation)
        await state.update_data(session_id=session_id, plan_id=plan_id)
        
    else:
        # Failed to create payment link, offer fallback
        error_msg = result.get('error', 'Unknown error')
        
        text = f"""
⚠️ <b>Card Payment Temporarily Unavailable</b>

We couldn't create a payment link right now.
Error: {error_msg}

You can try using Telegram Stars payment instead, which works instantly!
"""
        
        builder = InlineKeyboardBuilder()
        builder.button(text="⭐ Pay with Stars", callback_data=f"pay_stars_{plan_id}")
        builder.button(text="🔄 Retry Card Payment", callback_data=f"pay_card_{plan_id}")
        builder.button(text="❌ Cancel", callback_data="cancel_payment")
        builder.adjust(1)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.pre_checkout_query()
async def process_pre_checkout_query(query: PreCheckoutQuery):
    """Handle pre-checkout query for Stars payment"""
    payment_id = query.invoice_payload
    
    # Validate payment
    if payment_id not in pending_payments:
        logger.error(f"Unknown payment ID in pre-checkout: {payment_id}")
        await query.answer(
            ok=False,
            error_message="Payment session expired. Please try again."
        )
        return
    
    payment_info = pending_payments[payment_id]
    
    # Check if payment is not too old (15 minutes timeout)
    if (datetime.now() - payment_info["created_at"]).seconds > 900:
        await query.answer(
            ok=False,
            error_message="Payment session expired. Please start over."
        )
        del pending_payments[payment_id]
        return
    
    # Validate user
    if payment_info["user_id"] != query.from_user.id:
        logger.warning(f"User mismatch in pre-checkout: expected {payment_info['user_id']}, got {query.from_user.id}")
        await query.answer(
            ok=False,
            error_message="Invalid payment request."
        )
        return
    
    # Approve the payment
    await query.answer(ok=True)
    logger.info(f"Pre-checkout approved for user {query.from_user.id}, payment {payment_id}")

@router.message(F.successful_payment)
async def process_successful_payment(message: Message, bot: Bot):
    """Handle successful Stars payment"""
    payment = message.successful_payment
    payment_id = payment.invoice_payload
    user_id = message.from_user.id
    
    logger.info(f"Successful payment from user {user_id}: {payment_id}")
    
    # Get payment info
    if payment_id not in pending_payments:
        logger.error(f"Unknown payment ID in successful payment: {payment_id}")
        await message.answer("❌ Payment processing error. Please contact support.")
        return
    
    payment_info = pending_payments[payment_id]
    plan = payment_info["plan"]
    
    # Confirm payment with processor if available
    if payment_processor and payment_info.get('session_id'):
        confirm_success, subscription = await payment_processor.confirm_payment(
            session_id=payment_info['session_id'],
            transaction_id=payment.telegram_payment_charge_id,
            payment_method=PaymentMethod.STARS
        )
        
        if confirm_success:
            expires_at = subscription['expires_at']
        else:
            expires_at = datetime.now() + timedelta(days=plan["days"])
    else:
        # Fallback calculation
        expires_at = datetime.now() + timedelta(days=plan["days"])
    
    # Save subscription
    user_subscriptions[user_id] = {
        "plan": plan["name"],
        "expires_at": expires_at,
        "transaction_id": payment.telegram_payment_charge_id,
        "amount": payment.total_amount,
        "currency": payment.currency,
        "payment_method": "stars",
        "purchased_at": datetime.now()
    }
    
    # Clean up pending payment
    del pending_payments[payment_id]
    
    # Add user to group
    added_to_group = await add_user_to_group(bot, user_id)
    
    # Send confirmation message
    confirmation_text = f"""
✅ <b>Payment Successful!</b>

Thank you for your purchase!

<b>Details:</b>
• Plan: {plan['name']}
• Duration: {plan['days']} days
• Expires: {expires_at.strftime('%Y-%m-%d %H:%M')}
• Transaction ID: {html.code(payment.telegram_payment_charge_id)}

"""
    
    if added_to_group:
        confirmation_text += "You should have received an invite link to join the group. Check your messages above!"
    else:
        confirmation_text += "Please contact support if you haven't received the group invite link."
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Check Status", callback_data="menu_status")
    builder.button(text="Main Menu", callback_data="back_main")
    builder.adjust(2)
    
    await message.answer(confirmation_text, reply_markup=builder.as_markup())
    
    # Log the successful transaction
    logger.info(f"User {user_id} purchased {plan['name']} plan for {payment.total_amount} {payment.currency}")

@router.callback_query(lambda c: c.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery, state: FSMContext):
    """Handle payment cancellation"""
    await callback.answer("Payment cancelled")
    await state.clear()
    
    text = "Payment cancelled. You can start over anytime."
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Try Again", callback_data="menu_subscribe")
    builder.button(text="Main Menu", callback_data="back_main")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(lambda c: c.data and c.data.startswith("confirm_card_"))
async def confirm_card_payment(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Handle card payment confirmation"""
    await callback.answer("Checking payment status...", show_alert=False)
    
    session_id = callback.data.split("confirm_card_")[1]
    
    if not payment_processor:
        await callback.message.answer("❌ Payment service not available.")
        return
    
    # Get payment session
    session = payment_processor.get_session_status(session_id)
    
    if not session:
        await callback.message.answer("❌ Payment session expired. Please start over.")
        await state.clear()
        return
    
    # Check payment status with Airwallex
    if session.get('payment_link_id'):
        success, status = await payment_processor.airwallex.get_payment_link_status(
            session['payment_link_id']
        )
        
        if success and status.get('status') == 'PAID':
            # Payment confirmed!
            confirm_success, subscription = await payment_processor.confirm_payment(
                session_id=session_id,
                payment_link_id=session['payment_link_id'],
                payment_method=PaymentMethod.CARD
            )
            
            if confirm_success:
                # Add user to group
                added_to_group = await add_user_to_group(bot, session['user_id'])
                
                # Save subscription
                user_subscriptions[session['user_id']] = {
                    "plan": subscription['plan_name'],
                    "expires_at": subscription['expires_at'],
                    "transaction_id": subscription.get('transaction_id'),
                    "payment_method": "card",
                    "purchased_at": datetime.now()
                }
                
                text = f"""
✅ <b>Payment Successful!</b>

Thank you for your purchase!

<b>Details:</b>
• Plan: {subscription['plan_name']}
• Expires: {subscription['expires_at'].strftime('%Y-%m-%d %H:%M')}
• Payment Method: Card (Airwallex)

You should receive a group invite link shortly!
"""
                
                builder = InlineKeyboardBuilder()
                builder.button(text="📊 Check Status", callback_data="menu_status")
                builder.button(text="🏠 Main Menu", callback_data="back_main")
                builder.adjust(2)
                
                await state.clear()
                
            else:
                text = "❌ Failed to confirm payment. Please contact support."
                builder = InlineKeyboardBuilder()
                builder.button(text="Contact Support", url="https://t.me/username")
                builder.adjust(1)
        
        else:
            # Payment not yet confirmed
            text = """
⏳ <b>Payment Not Yet Confirmed</b>

Your payment is still being processed. This usually takes just a few moments.

Please complete the payment on the Airwallex page if you haven't already.

If you've completed the payment, please wait a moment and try again.
"""
            
            builder = InlineKeyboardBuilder()
            builder.button(text="🔄 Check Again", callback_data=f"confirm_card_{session_id}")
            builder.button(text="🔗 Open Payment Page", url=session.get('payment_url', '#'))
            builder.button(text="❌ Cancel", callback_data="cancel_payment")
            builder.adjust(1)
    
    else:
        text = "❌ Invalid payment session. Please start over."
        builder = InlineKeyboardBuilder()
        builder.button(text="Start Over", callback_data="menu_subscribe")
        builder.adjust(1)
        await state.clear()
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=builder.as_markup())

# Refund handler (admin only)
async def process_refund(bot: Bot, user_id: int, transaction_id: str) -> bool:
    """Process Stars refund"""
    try:
        await bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=transaction_id
        )
        
        # Remove subscription
        if user_id in user_subscriptions:
            del user_subscriptions[user_id]
        
        # Remove from group
        await remove_user_from_group(bot, user_id)
        
        logger.info(f"Refunded payment {transaction_id} for user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to refund payment {transaction_id}: {e}")
        return False
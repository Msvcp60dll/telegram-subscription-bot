# Dual Payment System Documentation

## Overview

This Telegram bot implements a dual payment system with:
- **Primary**: Airwallex card payments (via Payment Links API)
- **Fallback**: Telegram Stars native payments

## Features

### 1. Airwallex Integration
- Secure authentication with bearer tokens
- Payment link generation with $10 USD pricing
- Customer metadata tracking (telegram_id, username)
- 24-hour payment link expiry
- Webhook support for real-time payment notifications
- Automatic retry with exponential backoff
- Payment status verification

### 2. Telegram Stars Integration
- Native Telegram payment flow
- Instant payment confirmation
- Built-in refund support
- No external dependencies

### 3. Unified Payment Processor
- Single interface for both payment methods
- Automatic fallback to Stars if Airwallex fails
- Payment session management
- Revenue tracking by payment method
- Subscription activation after payment

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
┌──────▼──────┐
│  Telegram   │
│    Bot      │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│  Payment Processor      │
│  (Unified Interface)    │
└──┬──────────────────┬───┘
   │                  │
┌──▼──────────┐  ┌───▼──────────┐
│  Airwallex  │  │   Telegram   │
│   Service   │  │    Stars     │
└─────────────┘  └──────────────┘
```

## File Structure

```
/TGbot/
├── services/
│   ├── __init__.py
│   ├── airwallex_payment.py     # Airwallex API integration
│   ├── payment_processor.py     # Unified payment interface
│   └── webhook_handler.py       # Webhook processing
├── handlers/
│   ├── payments.py              # Payment flow handlers
│   ├── commands.py              # Bot commands
│   └── admin.py                 # Admin functions
├── main.py                      # Bot entry point
├── test_payment.py              # Integration tests
├── .env                         # Environment variables
└── requirements.txt             # Dependencies
```

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your credentials:

```env
# Bot Configuration
BOT_TOKEN=your_bot_token
GROUP_ID=your_group_id
ADMIN_USER_ID=your_admin_id

# Airwallex Configuration
AIRWALLEX_CLIENT_ID=your_client_id
AIRWALLEX_API_KEY=your_api_key
AIRWALLEX_BASE_URL=https://api.airwallex.com

# Optional: Webhook Configuration
WEBHOOK_BASE_URL=https://your-domain.com
WEBHOOK_PORT=8080
AIRWALLEX_WEBHOOK_SECRET=your_webhook_secret
```

### 3. Test the Integration
```bash
python test_payment.py
```

This will verify:
- Airwallex authentication
- Payment link creation
- Payment processor functionality
- Webhook signature verification

### 4. Run the Bot
```bash
python main.py
```

## Payment Flow

### Card Payment (Airwallex)
1. User selects subscription plan
2. User chooses "Pay with Card"
3. Bot creates Airwallex payment link
4. User completes payment on Airwallex page
5. Webhook notification received (if configured)
6. User clicks "I've Paid" to verify
7. Bot confirms payment status
8. Subscription activated

### Stars Payment (Telegram)
1. User selects subscription plan
2. User chooses "Pay with Stars"
3. Bot sends Telegram invoice
4. User completes payment in Telegram
5. Bot receives payment confirmation
6. Subscription activated

## Webhook Configuration

For production, configure webhooks to receive real-time payment notifications:

1. Set up a public URL for your bot (e.g., using ngrok for testing)
2. Configure `WEBHOOK_BASE_URL` in `.env`
3. The webhook endpoint will be: `https://your-domain.com/webhook/airwallex`
4. Add webhook URL when creating payment links

## Error Handling

The system implements robust error handling:

- **Network failures**: Automatic retry with exponential backoff
- **Authentication errors**: Token refresh on expiry
- **Payment failures**: Automatic fallback to Stars payment
- **Duplicate payments**: Session-based deduplication
- **Expired links**: Automatic cleanup and user notification

## Revenue Tracking

The payment processor tracks:
- Total transactions per payment method
- Revenue in USD (cards) and Stars
- Average transaction value
- Payment method distribution percentage

Access stats via:
```python
stats = payment_processor.get_revenue_stats()
```

## Security Considerations

1. **API Keys**: Store in environment variables, never commit to version control
2. **Webhook Verification**: Always verify webhook signatures in production
3. **Session Management**: Use unique session IDs to prevent replay attacks
4. **PCI Compliance**: Card data is handled by Airwallex, never stored locally
5. **Rate Limiting**: Implement rate limits to prevent abuse

## Testing Checklist

- [ ] Airwallex authentication works
- [ ] Payment links are created successfully
- [ ] Card payment flow completes
- [ ] Stars payment flow completes
- [ ] Fallback from card to Stars works
- [ ] Payment confirmations are received
- [ ] Subscriptions are activated correctly
- [ ] Group invites are sent after payment
- [ ] Revenue tracking is accurate
- [ ] Error messages are user-friendly

## Production Deployment

1. Use a production database instead of in-memory storage
2. Set up proper webhook URLs with HTTPS
3. Configure webhook secrets for signature verification
4. Implement proper logging and monitoring
5. Set up backup payment processing
6. Configure rate limiting and DDoS protection
7. Regular backup of payment data
8. Implement payment reconciliation

## Support

For issues with:
- **Airwallex API**: Check [Airwallex Docs](https://www.airwallex.com/docs)
- **Telegram Payments**: See [Telegram Bot Payments](https://core.telegram.org/bots/payments)
- **Bot Issues**: Check logs in `bot.log`

## License

This implementation is for the specific Telegram subscription bot. Modify as needed for your use case.
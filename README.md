# Telegram Subscription Management Bot

A powerful Telegram bot for managing paid subscriptions using Telegram Stars payment system.

## Features

- **Subscription Management**: Multiple subscription tiers (Basic, Standard, Premium)
- **Payment Integration**: Telegram Stars payments with pre-checkout validation
- **User Management**: Automatic group access management
- **Admin Panel**: Complete admin controls for user and subscription management
- **Whitelist System**: Lifetime access for special users
- **FSM States**: Multi-step processes for payments and admin actions
- **Broadcast System**: Send messages to all subscribers

## Quick Start

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Bot**
- Copy `.env.example` to `.env`
- Update with your bot token and settings

3. **Run the Bot**
```bash
python main.py
```

## Bot Commands

### User Commands
- `/start` - Start the bot and see main menu
- `/subscribe` - View subscription plans
- `/status` - Check subscription status
- `/help` - Show help message

### Admin Commands
- `/admin` - Access admin panel (admin only)

## Project Structure

```
TGbot/
├── main.py                 # Main bot file
├── handlers/              # Handler modules
│   ├── __init__.py
│   ├── commands.py        # Command handlers
│   ├── payments.py        # Payment flow handlers
│   └── admin.py           # Admin commands
├── docs/
│   └── aiogram_reference.md  # Aiogram 3 reference
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables example
└── README.md             # This file
```

## Configuration

### Required Environment Variables
- `BOT_TOKEN`: Your Telegram bot token
- `GROUP_ID`: Target group ID for subscription access
- `ADMIN_USER_ID`: Admin user ID for administrative functions

## Payment Flow

1. User selects subscription plan
2. Bot creates Telegram Stars invoice
3. User completes payment in Telegram
4. Bot validates pre-checkout query
5. On successful payment:
   - User subscription is activated
   - Invite link to group is sent
   - Confirmation message displayed

## Admin Features

- View statistics and revenue
- Manage user subscriptions
- Add/remove whitelist users
- Send broadcast messages
- View all active subscriptions
- Process refunds

## Security Notes

- Bot token is stored in environment variables
- Admin functions are restricted by user ID
- Payment validation in pre-checkout handler
- Automatic subscription expiry management

## Development

The bot uses aiogram 3.x framework with:
- Router-based handler organization
- FSM for multi-step processes
- Inline keyboards for better UX
- Comprehensive error handling
- Detailed logging

## Support

For issues or questions, contact the admin through Telegram.
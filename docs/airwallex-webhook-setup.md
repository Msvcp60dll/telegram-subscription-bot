# Airwallex Webhook Configuration Guide

## Prerequisites

Before configuring webhooks, ensure you have:
1. An active Airwallex account
2. API credentials (Client ID and API Key)
3. Access to the Airwallex webapp dashboard
4. Your webhook endpoint URL ready

## Step-by-Step Configuration

### 1. Access Webhook Settings

1. Log in to [Airwallex webapp](https://www.airwallex.com)
2. Navigate to **Developer** → **Webhooks**
3. Click on the **Summary** tab

### 2. Create New Webhook Endpoint

1. Click **"Add Webhook"** button
2. Fill in the webhook configuration:

#### Webhook Configuration Fields

| Field | Value | Notes |
|-------|-------|-------|
| **Notification URL** | Development: `http://localhost:8080/webhook/airwallex`<br>Production: `https://[RAILWAY_URL]/webhook/airwallex` | Must be HTTPS in production |
| **Description** | `Telegram Bot Subscription Webhooks` | Optional but recommended |
| **Status** | `Active` | Enable immediately |

### 3. Subscribe to Required Events

Select the following events for the Telegram subscription bot:

#### Payment Events
- [x] `payment_intent.succeeded` - Triggered when payment is successful
- [x] `payment_intent.failed` - Triggered when payment fails
- [x] `payment_link.paid` - Triggered when payment link is paid
- [x] `refund.succeeded` - Triggered when refund is processed

#### Optional Events (Recommended)
- [ ] `payment_link.expired` - Triggered when payment link expires
- [ ] `payment_intent.requires_capture` - For manual capture flows
- [ ] `dispute.created` - For chargeback notifications

### 4. Retrieve Webhook Secret

After creating the webhook:

1. Click on the webhook endpoint you just created
2. Find the **"Webhook Secret"** section
3. Click **"Show Secret"** to reveal your webhook signing secret
4. **IMPORTANT**: Copy this secret immediately and store it securely

```bash
# Add to your .env file
AIRWALLEX_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxx
```

### 5. Configure Environment Variables

Update your environment configuration with:

```bash
# Airwallex API Credentials
AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47

# Webhook Configuration
AIRWALLEX_WEBHOOK_SECRET=<your-webhook-secret-from-dashboard>

# Environment-specific URLs
# Development
WEBHOOK_BASE_URL=http://localhost:8080

# Production (Railway)
# WEBHOOK_BASE_URL=https://your-app.railway.app
```

### 6. Test Webhook Configuration

#### Using Airwallex Dashboard

1. Go to **Developer** → **Webhooks**
2. Click on your webhook endpoint
3. Select an event type (e.g., `payment_intent.succeeded`)
4. Click **"Test event"** button
5. Verify the test webhook is received at your endpoint

#### Test Event Headers

Test webhooks include a special header:
- `client-secret-key`: Contains the test webhook secret

### 7. Verify Production Setup

#### IP Allowlisting (Optional but Recommended)

Configure your firewall to allow webhooks only from Airwallex IPs:

```
35.240.218.67
35.185.179.53
35.247.36.10
35.189.7.223
35.201.25.117
35.244.120.212
35.198.20.173
35.197.184.222
35.244.65.184
```

#### Railway.app Configuration

For Railway deployment:

1. Set environment variables in Railway dashboard:
   ```
   AIRWALLEX_CLIENT_ID=BxnIFV1TQkWbrpkEKaADwg
   AIRWALLEX_API_KEY=df76d4f3a76c20ef97e1d9271bb7638bd5f235b773bb63a98d06c768b31b891a69cf06d99ef79e3f72ba1d76ad78ac47
   AIRWALLEX_WEBHOOK_SECRET=<your-secret>
   ```

2. Get your Railway app URL:
   ```
   https://your-app-name.railway.app
   ```

3. Update webhook URL in Airwallex dashboard:
   ```
   https://your-app-name.railway.app/webhook/airwallex
   ```

### 8. Monitor Webhook Activity

#### In Airwallex Dashboard

1. Navigate to **Developer** → **Webhooks** → **Events**
2. View recent webhook deliveries
3. Check for any failed deliveries
4. Review response times and status codes

#### Webhook Delivery Status

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ Success (200) | Webhook processed successfully | None |
| ⚠️ Client Error (4xx) | Invalid request or authentication | Check webhook secret and headers |
| ❌ Server Error (5xx) | Your server had an error | Check application logs |
| 🔄 Pending | Webhook queued for retry | Will retry for 3 days |

### 9. Troubleshooting

#### Common Issues and Solutions

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| 401 Unauthorized | Invalid webhook secret | Verify `AIRWALLEX_WEBHOOK_SECRET` matches dashboard |
| 400 Bad Request | Missing headers or malformed JSON | Check webhook handler logs |
| Webhooks not received | URL incorrect or service down | Verify endpoint URL and service status |
| Duplicate webhooks | Retry due to timeout | Implement idempotency using event ID |

#### Debug Checklist

- [ ] Webhook endpoint is publicly accessible
- [ ] HTTPS is configured (for production)
- [ ] Webhook secret is correctly set
- [ ] Required events are subscribed
- [ ] Signature verification is implemented
- [ ] Idempotency handling is in place
- [ ] Response time is < 5 seconds

### 10. Best Practices

1. **Always use HTTPS in production**
   - Railway.app provides automatic HTTPS

2. **Respond quickly**
   - Return 200 OK immediately
   - Process webhooks asynchronously if needed

3. **Implement idempotency**
   - Store and check event IDs
   - Handle retries gracefully

4. **Monitor webhook health**
   - Set up alerts for failed webhooks
   - Monitor processing time
   - Track success/failure rates

5. **Secure your endpoint**
   - Verify signatures for every webhook
   - Validate timestamps
   - Use IP allowlisting when possible

6. **Test thoroughly**
   - Test all subscribed events
   - Verify error handling
   - Test retry scenarios

## Webhook Payload Examples

### payment_intent.succeeded
```json
{
  "id": "evt_hkdmr7lr22",
  "name": "payment_intent.succeeded",
  "account_id": "your_account_id",
  "data": {
    "object": {
      "id": "int_hkdmr7lr22qe6bar0ds",
      "amount": 1000,
      "currency": "USD",
      "status": "SUCCEEDED",
      "payment_link_id": "plink_xxx",
      "metadata": {
        "telegram_id": "123456789",
        "plan_id": "monthly",
        "plan_name": "Monthly Subscription"
      }
    }
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

### payment_intent.failed
```json
{
  "id": "evt_failed123",
  "name": "payment_intent.failed",
  "account_id": "your_account_id",
  "data": {
    "object": {
      "id": "int_failed123",
      "amount": 1000,
      "currency": "USD",
      "status": "FAILED",
      "last_payment_error": {
        "message": "Card declined"
      },
      "metadata": {
        "telegram_id": "123456789"
      }
    }
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

## Support

For webhook-related issues:
1. Check [Airwallex Documentation](https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events)
2. Review webhook logs in Airwallex dashboard
3. Contact Airwallex support for API-related issues
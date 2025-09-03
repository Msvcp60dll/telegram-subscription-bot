# Airwallex Webhook Security Documentation

## Official Specification Reference
This documentation is based on the official Airwallex webhook implementation guide:
- https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events

## Webhook Signature Verification Algorithm

### HMAC-SHA256 Signature Verification

Airwallex uses **HMAC-SHA256** for webhook signature verification. Each webhook request includes security headers that must be validated before processing.

### Security Headers

| Header | Description |
|--------|------------|
| `x-timestamp` | Unix timestamp when the webhook was sent |
| `x-signature` | HMAC-SHA256 hex digest of the payload |

### Signature Verification Process

1. **Extract Headers**
   - Extract `x-timestamp` from request headers
   - Extract `x-signature` from request headers

2. **Prepare the Digest String**
   - Concatenate: `x-timestamp` (as string) + raw JSON payload (request body as string)
   - **CRITICAL**: Use the raw, unmodified JSON body before any parsing or transformation

3. **Compute HMAC**
   - Algorithm: HMAC-SHA256
   - Key: Your webhook endpoint secret from Airwallex dashboard
   - Message: The concatenated string from step 2

4. **Compare Signatures**
   - Use timing-safe comparison (e.g., `hmac.compare_digest` in Python)
   - Compare computed signature with `x-signature` header

5. **Validate Timestamp**
   - Calculate difference between current timestamp and received timestamp
   - Reject if difference exceeds tolerance (recommended: 5 minutes)

### Python Implementation (Correct)

```python
import hmac
import hashlib
import time

def verify_webhook_signature(
    body: str,  # Raw JSON body as string
    signature: str,  # x-signature header
    timestamp: str,  # x-timestamp header
    secret: str,  # Your webhook secret
    tolerance_seconds: int = 300  # 5 minutes
) -> bool:
    # Step 1: Validate timestamp to prevent replay attacks
    try:
        webhook_timestamp = int(timestamp)
        current_timestamp = int(time.time())
        
        if abs(current_timestamp - webhook_timestamp) > tolerance_seconds:
            return False
    except (ValueError, TypeError):
        return False
    
    # Step 2: Prepare the payload for signature
    payload = f"{timestamp}{body}"  # Concatenate timestamp + raw body
    
    # Step 3: Compute expected signature
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Step 4: Timing-safe comparison
    return hmac.compare_digest(signature, expected_signature)
```

## Security Best Practices

### 1. HTTPS Requirement
- **MANDATORY**: Always use HTTPS URLs for webhook endpoints
- Never use HTTP in production environments
- Ensure proper TLS/SSL certificate configuration

### 2. Idempotency Handling
- Use the `id` field in webhook events to prevent duplicate processing
- Store processed webhook IDs with expiration (recommended: 7 days)
- Return 200 OK for already-processed webhooks

### 3. Retry Logic
- Airwallex retries webhooks for **3 days** if no 200 status is received
- Implement idempotent handlers to safely handle retries
- Respond quickly (< 5 seconds) and process asynchronously if needed

### 4. IP Allowlisting (Production)
Restrict incoming webhook requests to Airwallex IP addresses:

**Production IPs:**
- 35.240.218.67
- 35.185.179.53
- 35.247.36.10
- 35.189.7.223
- 35.201.25.117
- 35.244.120.212
- 35.198.20.173
- 35.197.184.222
- 35.244.65.184

### 5. Request Validation Checklist
- [ ] HTTPS endpoint configured
- [ ] x-signature header present
- [ ] x-timestamp header present
- [ ] Timestamp within tolerance window (5 minutes)
- [ ] Signature verification passes
- [ ] Request body is valid JSON
- [ ] Event ID not previously processed

### 6. Error Handling
- Never expose webhook secret in error messages
- Log security failures for monitoring
- Return appropriate HTTP status codes:
  - 200: Successfully processed
  - 401: Invalid signature
  - 400: Malformed request
  - 500: Internal processing error

### 7. Testing Webhooks
For test environments:
- Test webhook signatures use the secret from `client-secret-key` header
- Always validate test webhooks the same as production

## Common Security Vulnerabilities to Avoid

1. **Timing Attacks**
   - Always use `hmac.compare_digest()` for signature comparison
   - Never use simple string equality (`==`)

2. **Replay Attacks**
   - Always validate timestamp freshness
   - Reject webhooks older than 5 minutes

3. **JSON Parsing Issues**
   - Verify signature BEFORE parsing JSON
   - Use raw body string for signature verification

4. **Secret Exposure**
   - Never log webhook secrets
   - Store secrets in environment variables
   - Rotate secrets periodically

5. **Concurrent Processing**
   - Implement proper locking for idempotency checks
   - Handle race conditions in duplicate detection

## Monitoring and Alerting

### Key Metrics to Track
- Invalid signature attempts
- Timestamp validation failures
- Duplicate webhook attempts
- Processing latency
- Error rates by event type

### Security Events to Log
- Failed signature verifications (without exposing secrets)
- Replay attack attempts (old timestamps)
- Requests from non-allowlisted IPs
- Malformed webhook payloads
- Rate limit violations

## References
- [Airwallex Webhook Documentation](https://www.airwallex.com/docs/developer-tools__listen-for-webhook-events)
- [Airwallex Webhook Testing](https://www.airwallex.com/docs/developer-tools__test-webhook-event-payloads)
- [HMAC RFC 2104](https://www.ietf.org/rfc/rfc2104.txt)
# Airwallex Webhook Security Audit Checklist

## Pre-Deployment Security Audit

This checklist must be completed before deploying webhook handlers to production.

### 🔐 Authentication & Authorization

#### Signature Verification
- [ ] **HMAC-SHA256 signature verification implemented**
  - File: `services/airwallex_payment.py:265-299`
  - Verification: Uses official algorithm from Airwallex docs
  - Test: `python tests/test_webhook_security.py`

- [ ] **Webhook secret stored securely**
  - Stored in environment variable: `AIRWALLEX_WEBHOOK_SECRET`
  - Never hardcoded in source code
  - Different secrets for dev/staging/production

- [ ] **Timing-safe comparison used**
  - Using `hmac.compare_digest()` for signature comparison
  - Prevents timing attacks
  - Verified in: `services/airwallex_payment.py:292`

#### Headers Validation
- [ ] **Required headers checked**
  - `x-timestamp` header present
  - `x-signature` header present
  - Return 400 for missing headers
  - Implementation: `services/webhook_handler.py:48-52`

### 🕐 Replay Attack Prevention

- [ ] **Timestamp validation implemented**
  - Maximum age: 5 minutes (300 seconds)
  - Rejects webhooks with old timestamps
  - Implementation: `services/airwallex_payment.py:281-290`

- [ ] **Timestamp format validation**
  - Validates timestamp is valid integer
  - Handles invalid timestamp gracefully
  - Returns 401 for invalid timestamps

### 🔄 Idempotency

- [ ] **Event ID tracking**
  - Stores processed webhook IDs
  - Implementation: `services/webhook_handler.py:84-88`
  - Returns 200 for duplicate webhooks

- [ ] **Persistent storage for production**
  - [ ] Redis or database for event ID storage (production)
  - [ ] Expiration policy implemented (7 days recommended)
  - [ ] Current: In-memory set (development only)

### 🌐 Network Security

#### HTTPS Configuration
- [ ] **HTTPS enforced in production**
  - Railway.app provides automatic HTTPS
  - Never use HTTP in production
  - Webhook URL uses HTTPS: `https://[RAILWAY_URL]/webhook/airwallex`

#### IP Allowlisting (Recommended)
- [ ] **Firewall rules configured**
  - Production IPs allowlisted:
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

### 📝 Input Validation

- [ ] **JSON parsing security**
  - Signature verified BEFORE parsing JSON
  - Handles malformed JSON gracefully
  - Returns 400 for invalid JSON
  - Implementation: `services/webhook_handler.py:74-78`

- [ ] **Payload size limits**
  - [ ] Maximum request body size configured
  - [ ] Recommended: 1MB limit for webhook payloads

### ⚡ Performance & Reliability

- [ ] **Response time optimization**
  - Returns 200 OK within 5 seconds
  - Asynchronous processing for heavy operations
  - Implementation: Uses async handlers

- [ ] **Error handling**
  - All exceptions caught and logged
  - Returns appropriate status codes
  - Never exposes internal errors to client
  - Implementation: `services/webhook_handler.py:92-94`

- [ ] **Retry handling**
  - Idempotent processing ensures safe retries
  - Handles Airwallex 3-day retry window
  - Returns 200 for successful processing

### 🔍 Logging & Monitoring

#### Security Logging
- [ ] **Failed signature attempts logged**
  - Logs include timestamp and IP (not signatures)
  - Implementation: `services/webhook_handler.py:70`

- [ ] **Replay attacks logged**
  - Old timestamp attempts logged
  - Implementation: `services/airwallex_payment.py:287-290`

- [ ] **Duplicate webhook attempts logged**
  - Idempotency violations tracked
  - Implementation: `services/webhook_handler.py:55`

#### Sensitive Data Protection
- [ ] **No secrets in logs**
  - Webhook secret never logged
  - Signatures not logged
  - API keys not exposed

- [ ] **PII handling**
  - Customer data logged minimally
  - Telegram IDs handled appropriately
  - Payment details secured

### 🚨 Incident Response

- [ ] **Monitoring alerts configured**
  - [ ] Alert on repeated signature failures
  - [ ] Alert on high error rates
  - [ ] Alert on unusual traffic patterns

- [ ] **Secret rotation plan**
  - [ ] Process documented for rotating webhook secret
  - [ ] Zero-downtime rotation strategy
  - [ ] Regular rotation schedule (quarterly recommended)

### 🧪 Testing

#### Automated Tests
- [ ] **Security test suite passes**
  ```bash
  python tests/test_webhook_security.py
  ```
  - All 9 security tests pass
  - Signature verification tested
  - Replay attack prevention tested
  - Idempotency tested

#### Manual Testing
- [ ] **Airwallex dashboard testing**
  - Test events sent successfully
  - Webhook receives and processes correctly
  - Proper status codes returned

- [ ] **Production-like testing**
  - [ ] HTTPS endpoint tested
  - [ ] High volume testing performed
  - [ ] Concurrent webhook handling tested

### 📋 Compliance & Documentation

- [ ] **Security documentation complete**
  - `docs/webhook-security.md` - Security implementation details
  - `docs/airwallex-webhook-setup.md` - Configuration guide
  - `docs/webhook-security-audit.md` - This checklist

- [ ] **Code reviews conducted**
  - Security-focused review completed
  - No hardcoded secrets found
  - Error handling reviewed

### 🚀 Production Readiness

#### Environment Configuration
- [ ] **Production environment variables set**
  ```bash
  AIRWALLEX_CLIENT_ID=<production_client_id>
  AIRWALLEX_API_KEY=<production_api_key>
  AIRWALLEX_WEBHOOK_SECRET=<production_webhook_secret>
  ```

- [ ] **Railway deployment configured**
  - Environment variables set in Railway
  - HTTPS URL configured
  - Health check endpoint working

#### Final Checklist
- [ ] **All critical items above checked**
- [ ] **Security test suite passes 100%**
- [ ] **No known vulnerabilities**
- [ ] **Monitoring configured**
- [ ] **Incident response plan ready**
- [ ] **Documentation complete**

## Security Audit Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Security Reviewer | | | |
| Product Owner | | | |

## Post-Deployment Monitoring

### First 24 Hours
- [ ] Monitor webhook success rate
- [ ] Check for signature failures
- [ ] Verify idempotency working
- [ ] Review error logs

### First Week
- [ ] Analyze webhook patterns
- [ ] Review security logs
- [ ] Check response times
- [ ] Validate retry handling

### Monthly Review
- [ ] Security metrics review
- [ ] Failed authentication attempts
- [ ] Performance optimization
- [ ] Secret rotation schedule

## Emergency Contacts

- **Airwallex Support**: [support.airwallex.com](https://support.airwallex.com)
- **Security Incidents**: Create incident ticket immediately
- **On-call Engineer**: [Define contact]

## Appendix: Quick Commands

### Test Webhook Security
```bash
# Run security test suite
python tests/test_webhook_security.py

# Test specific webhook
curl -X POST http://localhost:8080/webhook/airwallex \
  -H "Content-Type: application/json" \
  -H "x-timestamp: $(date +%s)" \
  -H "x-signature: test_signature" \
  -d '{"id":"test_event","name":"payment_intent.succeeded"}'
```

### Monitor Webhooks
```bash
# View webhook logs
tail -f logs/webhook.log | grep -E "(signature|security|error)"

# Check webhook endpoint health
curl http://localhost:8080/health
```

### Rotate Webhook Secret
1. Generate new secret in Airwallex dashboard
2. Update environment variable
3. Deploy with zero downtime
4. Verify new webhooks working
5. Remove old secret

---

**Last Updated**: 2025-01-03
**Next Review**: Quarterly or after any security incident
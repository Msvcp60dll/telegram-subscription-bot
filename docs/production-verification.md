# Production Verification Checklist

## Pre-Deployment Checks

### Environment Variables
- [ ] BOT_TOKEN is set correctly
- [ ] GROUP_ID matches production group
- [ ] ADMIN_USER_ID is correct
- [ ] SUPABASE_URL points to production database
- [ ] SUPABASE_SERVICE_KEY has proper permissions
- [ ] AIRWALLEX_CLIENT_ID is production key
- [ ] AIRWALLEX_API_KEY is production key
- [ ] AIRWALLEX_WEBHOOK_SECRET is configured
- [ ] WEBHOOK_BASE_URL matches Railway deployment URL
- [ ] WEBHOOK_PORT is configured (default: 8080)

### Database Setup
- [ ] All tables created (users, subscriptions, payments, transactions)
- [ ] Indexes are in place for performance
- [ ] RLS policies are configured correctly
- [ ] Service role key has necessary permissions
- [ ] Database backup is configured

### Railway Configuration
- [ ] Environment variables imported from .env
- [ ] PORT variable set for webhook server
- [ ] Health check endpoint configured
- [ ] Deployment region selected appropriately
- [ ] Resource limits configured
- [ ] Custom domain configured (if applicable)

## Post-Deployment Validation

### 1. Basic Bot Functionality

#### Bot Startup Verification
```bash
# Check Railway logs for startup messages
railway logs --tail 50

# Expected output:
# - "Bot starting up..."
# - "Bot: @YourBotName (ID: XXXXXX)"
# - "Group configured: GroupName (ID: -XXXXXX)"
# - "Payment processor initialized and configured"
# - "Subscription automation started"
# - "Webhook server started on port 8080"
# - "Admin dashboard started on port 8081"
# - "Bot startup complete!"
```

#### Command Testing Sequence
1. **Test /start command**
   - Send `/start` to bot in private chat
   - Verify welcome message appears
   - Check for subscription options

2. **Test /status command**
   - Send `/status` in private chat
   - Verify subscription status displays correctly
   - Check expiration date formatting

3. **Test /help command**
   - Send `/help` in private chat
   - Verify all commands are listed
   - Check command descriptions are accurate

### 2. Database Connectivity Tests

#### Manual Database Check
```bash
# Run the monitoring script
python scripts/monitor_production.py --check database

# Or use the test script
python scripts/test_supabase_connection.py
```

#### Expected Results:
- [ ] Connection established successfully
- [ ] Tables are accessible
- [ ] Can read user data
- [ ] Can write test record
- [ ] Can delete test record

### 3. Payment Flow Verification

#### Stars Payment Test
1. **Initiate Payment**
   - Send `/subscribe` command
   - Select "Basic (7 days)" plan
   - Click "Pay 50 ⭐" button
   - Verify Stars payment interface opens

2. **Complete Payment**
   - Complete Stars payment (test mode if available)
   - Verify success message
   - Check database for payment record
   - Verify subscription is activated
   - Confirm group access is granted

#### Airwallex Payment Test (if enabled)
1. **Generate Payment Link**
   - Use `/pay` command
   - Select subscription plan
   - Verify payment link is generated
   - Check link is accessible

2. **Webhook Processing**
   - Complete test payment
   - Monitor webhook endpoint logs
   - Verify payment status update
   - Check subscription activation

### 4. Admin Operations Verification

#### Admin Commands
1. **Test /admin command**
   - Send as admin user
   - Verify admin panel appears
   - Check all buttons are functional

2. **Statistics Check**
   - Click "📊 Statistics" button
   - Verify user count is accurate
   - Check active subscriptions count
   - Verify revenue calculations

3. **User Management**
   - Test "👥 Manage Users" function
   - Search for a test user
   - Verify user details display
   - Test subscription extension

#### Admin Dashboard
1. **Access Dashboard**
   ```bash
   curl https://your-railway-url.railway.app:8081/
   ```
   - Verify dashboard loads
   - Check authentication works
   - Test navigation menu

2. **Dashboard Features**
   - View real-time statistics
   - Check user list pagination
   - Test search functionality
   - Verify export features

### 5. Automation and Scheduling

#### Daily Automation Check
1. **Verify Scheduler Running**
   ```bash
   # Check logs for automation
   railway logs | grep "automation"
   ```

2. **Test Manual Trigger**
   - Use admin command to trigger check
   - Verify expired subscriptions are processed
   - Check removal notifications sent
   - Confirm database updates

### 6. Error Handling and Recovery

#### Simulated Failures
1. **Database Disconnection**
   - Monitor error logs
   - Verify graceful error handling
   - Check retry mechanism

2. **Payment Failure**
   - Test with invalid payment
   - Verify error message to user
   - Check error logging

3. **Group Access Issues**
   - Test with bot removed from group
   - Verify error notifications
   - Check fallback behavior

## Performance Validation

### Load Testing
```bash
# Run load tests
python scripts/production_tests.py --test load

# Expected metrics:
# - Response time < 2 seconds
# - No memory leaks
# - CPU usage < 70%
# - Concurrent users: 100+
```

### Monitoring Metrics
- [ ] Average response time
- [ ] Error rate < 1%
- [ ] Database query time < 100ms
- [ ] Webhook processing time < 500ms
- [ ] Memory usage stable

## Security Verification

### Access Control
- [ ] Bot token not exposed in logs
- [ ] API keys properly secured
- [ ] Admin commands restricted
- [ ] Group management permissions verified

### Data Protection
- [ ] No sensitive data in logs
- [ ] Payment information encrypted
- [ ] User data properly isolated
- [ ] Backup encryption enabled

## Rollback Preparation

### Before Going Live
- [ ] Previous version tagged in Git
- [ ] Database backup completed
- [ ] Configuration backup saved
- [ ] Rollback script tested
- [ ] Team notified of deployment

### Rollback Triggers
- Critical errors in logs
- Payment processing failures
- Database connection issues
- Bot unresponsive to commands
- Memory/CPU usage excessive

## Sign-off Checklist

### Technical Validation
- [ ] All automated tests passing
- [ ] Manual test scenarios completed
- [ ] Performance benchmarks met
- [ ] Security scan completed
- [ ] Monitoring alerts configured

### Business Validation
- [ ] Payment flow tested end-to-end
- [ ] Admin functions verified
- [ ] User experience validated
- [ ] Documentation updated
- [ ] Support team briefed

### Final Approval
- [ ] Technical Lead approval
- [ ] Product Owner approval
- [ ] Deployment window confirmed
- [ ] Rollback plan reviewed
- [ ] Go-live decision made

---

## Quick Verification Commands

```bash
# Check bot status
curl https://your-railway-url/health

# Test database connection
python scripts/monitor_production.py --quick-check

# Verify payment system
python scripts/production_tests.py --test payments

# Check all systems
python scripts/monitor_production.py --full-check
```

## Emergency Contacts

- **Technical Lead**: [Contact Info]
- **DevOps Team**: [Contact Info]
- **Database Admin**: [Contact Info]
- **Payment Support**: [Contact Info]
- **On-call Engineer**: [Contact Info]
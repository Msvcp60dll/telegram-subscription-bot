# Incident Response Plan

## Quick Reference

**Critical Issues Hotline**: [Your emergency contact]
**Status Page**: [Your status page URL]
**War Room**: [Slack/Discord channel]

## Incident Severity Levels

### SEV-1: Critical (Production Down)
- Bot completely unresponsive
- Payment processing completely failed
- Database completely inaccessible
- Data loss or corruption
- Security breach

**Response Time**: Immediate (within 15 minutes)
**Notification**: All stakeholders, on-call engineer

### SEV-2: Major (Degraded Service)
- Bot responding slowly (>5s delays)
- Intermittent payment failures (>10%)
- Database performance issues
- Admin dashboard inaccessible
- Subscription automation failing

**Response Time**: Within 30 minutes
**Notification**: Technical team, product owner

### SEV-3: Minor (Limited Impact)
- Non-critical features failing
- Slow response for specific commands
- Minor UI issues
- Non-critical automation delays

**Response Time**: Within 2 hours
**Notification**: Technical team

## Common Failure Scenarios

### 1. Bot Unresponsive

**Symptoms:**
- Commands not working
- Bot appears offline
- No response to /start

**Immediate Actions:**
```bash
# Check bot status
python scripts/monitor_production.py --check bot

# Check Railway logs
railway logs --tail 100

# Restart bot service
railway restart
```

**Troubleshooting Steps:**
1. Verify bot token is valid
2. Check Telegram API status
3. Verify network connectivity
4. Check for rate limiting
5. Review recent deployments

**Resolution:**
- Restart bot process
- Regenerate bot token if compromised
- Scale up resources if needed
- Implement rate limiting if being flooded

### 2. Database Connection Failure

**Symptoms:**
- "Database error" messages
- Unable to save/retrieve user data
- Subscription checks failing

**Immediate Actions:**
```bash
# Test database connection
python scripts/monitor_production.py --check database

# Check Supabase status
curl https://status.supabase.com/api/v2/status.json

# Test direct connection
python scripts/test_supabase_connection.py
```

**Troubleshooting Steps:**
1. Verify Supabase service key
2. Check Supabase service status
3. Verify network connectivity
4. Check connection pool exhaustion
5. Review database logs

**Resolution:**
- Restart database connections
- Update service key if expired
- Increase connection pool size
- Implement connection retry logic
- Contact Supabase support if needed

### 3. Payment Processing Failure

**Symptoms:**
- Users unable to complete payments
- Payment callbacks not received
- Subscription not activated after payment

**Immediate Actions:**
```bash
# Check payment system
python scripts/monitor_production.py --check payment

# Review payment logs
grep "payment" logs/telegram_subscription_bot_payments.log | tail -50

# Test webhook endpoint
curl https://your-railway-url/health
```

**Troubleshooting Steps:**
1. Verify payment provider API status
2. Check webhook configuration
3. Verify API keys are valid
4. Review recent payment logs
5. Check for webhook timeouts

**Resolution:**
- Update payment API keys
- Fix webhook URL configuration
- Implement payment retry mechanism
- Process pending payments manually
- Contact payment provider support

### 4. Group Management Issues

**Symptoms:**
- Users not added to group after payment
- Unable to remove expired users
- Group invite link issues

**Immediate Actions:**
```bash
# Check bot group permissions
python scripts/production_tests.py --test admin

# Verify group ID
echo $GROUP_ID
```

**Troubleshooting Steps:**
1. Verify bot has admin rights in group
2. Check group ID is correct
3. Verify invite link permissions
4. Check for Telegram API limits
5. Review group settings

**Resolution:**
- Re-add bot as group admin
- Update group ID in configuration
- Generate new invite link
- Implement batch processing for large operations
- Manual user management if needed

### 5. High Memory/CPU Usage

**Symptoms:**
- Bot responding slowly
- Railway resource alerts
- Intermittent timeouts

**Immediate Actions:**
```bash
# Check Railway metrics
railway logs --tail 50 | grep -i "memory\|cpu"

# Monitor resource usage
python scripts/monitor_production.py --continuous --interval 10
```

**Troubleshooting Steps:**
1. Identify memory leaks
2. Check for infinite loops
3. Review recent code changes
4. Analyze database query performance
5. Check for excessive logging

**Resolution:**
- Restart service to free memory
- Optimize database queries
- Implement caching
- Scale up Railway resources
- Fix memory leaks in code

### 6. Webhook Failures

**Symptoms:**
- Payment notifications not received
- Webhook endpoint returning errors
- SSL certificate issues

**Immediate Actions:**
```bash
# Test webhook endpoint
curl -X POST https://your-railway-url/webhook/airwallex \
  -H "Content-Type: application/json" \
  -d '{"test": true}'

# Check webhook logs
railway logs | grep webhook
```

**Troubleshooting Steps:**
1. Verify webhook URL configuration
2. Check SSL certificate validity
3. Verify webhook secret
4. Test network connectivity
5. Review webhook handler code

**Resolution:**
- Update webhook URL in payment provider
- Fix SSL certificate issues
- Update webhook secret
- Implement webhook retry logic
- Add webhook validation logging

## Rollback Procedures

### Quick Rollback (Railway)

```bash
# List recent deployments
railway deployments list

# Rollback to previous deployment
railway deployments rollback [deployment-id]

# Verify rollback
railway status
```

### Database Rollback

```bash
# Create backup before any changes
python scripts/backup_database.py

# Restore from backup
python scripts/restore_database.py --backup-file [filename]
```

### Configuration Rollback

```bash
# Revert environment variables
railway variables set BOT_TOKEN=[old-token]
railway variables set SUPABASE_SERVICE_KEY=[old-key]

# Restart service
railway restart
```

## Emergency Procedures

### Complete Service Restart

```bash
# 1. Stop the service
railway down

# 2. Clear any locks/temp files
rm -f *.lock temp/*

# 3. Restart service
railway up

# 4. Verify service is running
python scripts/monitor_production.py --full-check
```

### Emergency Maintenance Mode

```python
# Set in main.py temporarily
MAINTENANCE_MODE = True
MAINTENANCE_MESSAGE = "Bot is under maintenance. Please try again in 30 minutes."

# Deploy
railway up
```

### Data Recovery

```bash
# Export critical data
python scripts/export_critical_data.py

# Verify data integrity
python scripts/verify_data_integrity.py

# Import to new instance if needed
python scripts/import_data.py --file backup.json
```

## Monitoring and Alerting

### Set Up Continuous Monitoring

```bash
# Start monitoring daemon
nohup python scripts/monitor_production.py --continuous --interval 60 &

# Set up alert webhook
export ALERT_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export ALERT_TELEGRAM_CHAT_ID="-1001234567890"
```

### Key Metrics to Monitor

1. **Response Time**: < 2 seconds
2. **Error Rate**: < 1%
3. **Database Query Time**: < 100ms
4. **Memory Usage**: < 80% of limit
5. **Active Users**: Track anomalies
6. **Payment Success Rate**: > 95%

## Communication Templates

### Initial Response (SEV-1)

```
🔴 INCIDENT: [Brief description]
Severity: SEV-1
Status: Investigating
Impact: [Number] users affected
ETA: Updates every 15 minutes

Actions taken:
- [Action 1]
- [Action 2]

Next update: [Time]
```

### Status Update

```
📊 UPDATE: [Incident title]
Time: [Current time]
Duration: [Time since start]
Status: [Investigating/Identified/Monitoring/Resolved]

Current situation:
- [Update 1]
- [Update 2]

Next steps:
- [Step 1]
- [Step 2]

Next update: [Time]
```

### Resolution Notice

```
✅ RESOLVED: [Incident title]
Duration: [Total time]
Root cause: [Brief explanation]
Fix applied: [What was done]

Impact summary:
- [Impact 1]
- [Impact 2]

Follow-up actions:
- [Action 1]
- [Action 2]

Post-mortem: [Date/time]
```

## Post-Incident Review

### Required for SEV-1 and SEV-2 Incidents

1. **Timeline**
   - When was issue detected?
   - When was team notified?
   - When was issue resolved?

2. **Root Cause Analysis**
   - What caused the issue?
   - Why wasn't it caught earlier?
   - What monitoring gap existed?

3. **Impact Assessment**
   - How many users affected?
   - Revenue impact?
   - Reputation impact?

4. **Lessons Learned**
   - What went well?
   - What could be improved?
   - Action items for prevention

5. **Action Items**
   - Code fixes needed
   - Monitoring improvements
   - Process updates
   - Documentation updates

## Contact Escalation Matrix

### Level 1: On-Call Engineer
- **Response Time**: 15 minutes
- **Contact**: [Phone/Slack/Email]
- **Backup**: [Backup contact]

### Level 2: Technical Lead
- **Escalate After**: 30 minutes
- **Contact**: [Phone/Slack/Email]
- **For**: SEV-1 incidents, architectural decisions

### Level 3: Product Owner
- **Escalate After**: 1 hour
- **Contact**: [Phone/Slack/Email]
- **For**: Business impact decisions, customer communication

### Level 4: Executive Team
- **Escalate After**: 2 hours
- **Contact**: [Phone/Email]
- **For**: Critical business decisions, PR issues

## External Contacts

### Supabase Support
- **Email**: support@supabase.io
- **Dashboard**: https://app.supabase.io/support
- **Status**: https://status.supabase.com

### Railway Support
- **Dashboard**: https://railway.app/support
- **Discord**: [Railway Discord]
- **Status**: https://status.railway.app

### Telegram Support
- **Bot Support**: @BotSupport
- **API Status**: https://core.telegram.org/api/obtaining_api_id

### Airwallex Support
- **Email**: support@airwallex.com
- **Phone**: [Regional phone number]
- **Status**: https://status.airwallex.com

## Preventive Measures

### Daily Checks
```bash
# Run every morning
python scripts/monitor_production.py --full-check
python scripts/production_tests.py --all
```

### Weekly Reviews
- Review error logs
- Check performance trends
- Update dependencies
- Review user feedback

### Monthly Tasks
- Full system backup
- Security audit
- Performance optimization
- Documentation update

## Emergency Commands Reference

```bash
# Quick health check
curl https://your-railway-url/health

# Force restart
railway restart --force

# Check recent errors
railway logs --tail 100 | grep ERROR

# Database connection test
python -c "from database.supabase_client import SupabaseClient; print('OK')"

# Send test notification
python -c "from scripts.monitor_production import ProductionMonitor; 
          import asyncio; 
          m = ProductionMonitor(); 
          asyncio.run(m.send_alert('Test alert', 'INFO'))"

# Export user data
python -c "from scripts.production_tests import ProductionTestSuite;
          import asyncio;
          suite = ProductionTestSuite();
          asyncio.run(suite.initialize());
          # Export logic here"
```

---

**Remember**: Stay calm, communicate clearly, document everything, and learn from every incident.
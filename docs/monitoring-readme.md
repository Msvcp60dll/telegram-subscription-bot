# Production Monitoring and Verification System

## Overview

This comprehensive monitoring and verification system ensures your Telegram subscription bot runs reliably in production. It includes health checks, performance monitoring, error tracking, and incident response procedures.

## Components

### 1. Monitoring Script (`scripts/monitor_production.py`)

Real-time health monitoring for all system components.

**Features:**
- Bot responsiveness checking
- Database connectivity testing
- Payment system validation
- Webhook endpoint monitoring
- Admin dashboard verification
- Automated alerting
- Performance metrics collection

**Usage:**
```bash
# Quick health check
python scripts/monitor_production.py

# Check specific component
python scripts/monitor_production.py --check database

# Continuous monitoring
python scripts/monitor_production.py --continuous --interval 60

# Full system check
python scripts/monitor_production.py --full-check
```

### 2. Production Test Suite (`scripts/production_tests.py`)

Comprehensive end-to-end testing of all critical paths.

**Test Coverage:**
- Bot command functionality
- Database CRUD operations
- Subscription lifecycle
- Payment processing flow
- Admin operations
- Error recovery mechanisms
- Load performance testing
- Webhook endpoint validation

**Usage:**
```bash
# Run all tests
python scripts/production_tests.py --all

# Run specific test
python scripts/production_tests.py --test payment

# Load testing
python scripts/production_tests.py --test load

# Save report
python scripts/production_tests.py --all --report test_results.txt
```

### 3. Logging Configuration (`scripts/setup_logging.py`)

Production-grade logging with structured output and rotation.

**Features:**
- Structured JSON logging
- Separate logs for errors, payments, audit
- Performance metrics logging
- Log rotation and retention
- Alert threshold configuration

**Usage:**
```bash
# Setup local logging
python scripts/setup_logging.py --environment local

# Setup Railway logging
python scripts/setup_logging.py --environment railway

# Test logging configuration
python scripts/setup_logging.py --test
```

### 4. Deployment Verification (`scripts/verify_deployment.py`)

Quick verification immediately after deployment.

**Checks:**
- Environment variables
- Bot connection
- Database accessibility
- Webhook health
- Admin dashboard

**Usage:**
```bash
# Run immediately after deployment
python scripts/verify_deployment.py
```

## Deployment Workflow

### Pre-Deployment

1. **Run local tests:**
```bash
python scripts/production_tests.py --all
```

2. **Setup logging:**
```bash
python scripts/setup_logging.py --environment railway
```

3. **Review checklist:**
```bash
cat docs/production-verification.md
```

### Post-Deployment

1. **Quick verification:**
```bash
python scripts/verify_deployment.py
```

2. **Monitor logs:**
```bash
railway logs --tail 50
```

3. **Run health checks:**
```bash
python scripts/monitor_production.py --full-check
```

4. **Test critical paths:**
```bash
python scripts/production_tests.py --test payment
python scripts/production_tests.py --test subscription
```

5. **Start monitoring:**
```bash
nohup python scripts/monitor_production.py --continuous &
```

## Alert Configuration

### Telegram Alerts

Set up Telegram alerts for critical issues:

```bash
export ALERT_TELEGRAM_CHAT_ID="-1001234567890"
```

### Webhook Alerts (Slack/Discord)

Configure webhook URL for team notifications:

```bash
export ALERT_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## Performance Benchmarks

Expected performance metrics:

| Metric | Target | Critical |
|--------|--------|----------|
| Bot Response Time | < 1s | > 3s |
| Database Query | < 100ms | > 500ms |
| Webhook Processing | < 500ms | > 2s |
| Payment Confirmation | < 3s | > 10s |
| Error Rate | < 1% | > 5% |
| Memory Usage | < 256MB | > 512MB |
| CPU Usage | < 50% | > 80% |

## Monitoring Dashboard

### Local Dashboard

View real-time metrics:

```bash
# Start monitoring with web interface
python scripts/monitor_production.py --dashboard
```

Access at: http://localhost:8082

### Railway Metrics

View in Railway dashboard:
1. Go to your Railway project
2. Click on the service
3. View "Metrics" tab

## Troubleshooting

### Common Issues

1. **Bot not responding:**
```bash
python scripts/monitor_production.py --check bot
railway restart
```

2. **Database errors:**
```bash
python scripts/test_supabase_connection.py
python scripts/monitor_production.py --check database
```

3. **Payment failures:**
```bash
grep ERROR logs/*payments.log | tail -20
python scripts/production_tests.py --test payment
```

4. **High memory usage:**
```bash
railway logs | grep -i memory
railway restart --force
```

### Emergency Procedures

1. **Complete system restart:**
```bash
railway restart --force
python scripts/verify_deployment.py
```

2. **Rollback deployment:**
```bash
railway deployments list
railway deployments rollback [deployment-id]
```

3. **Enable maintenance mode:**
```bash
# Set environment variable
railway variables set MAINTENANCE_MODE=true
railway restart
```

## Log Files

### Local Environment

Logs are stored in the `logs/` directory:

- `telegram_subscription_bot.log` - All application logs
- `telegram_subscription_bot_errors.log` - Error logs only
- `telegram_subscription_bot_payments.log` - Payment transactions
- `telegram_subscription_bot_audit.log` - Security audit trail
- `telegram_subscription_bot_performance.log` - Performance metrics

### Railway Environment

View logs using:
```bash
# Recent logs
railway logs --tail 100

# Follow logs
railway logs --follow

# Search logs
railway logs | grep ERROR
railway logs | grep payment
```

## Incident Response

For detailed incident response procedures, see: `docs/incident-response.md`

### Quick Actions

1. **Check system health:**
```bash
curl https://your-railway-url/health
```

2. **View error rate:**
```bash
railway logs | grep ERROR | wc -l
```

3. **Check active users:**
```bash
python scripts/monitor_production.py --check database
```

## Best Practices

1. **Regular Monitoring:**
   - Run health checks every hour
   - Review error logs daily
   - Check performance metrics weekly

2. **Proactive Maintenance:**
   - Update dependencies monthly
   - Review and optimize slow queries
   - Clean up old logs and data

3. **Documentation:**
   - Document all incidents
   - Update runbooks after issues
   - Keep contact list current

4. **Testing:**
   - Test disaster recovery quarterly
   - Run load tests before major events
   - Verify backups regularly

## Support

### Internal Support

- **On-Call Engineer**: Check rotation schedule
- **Tech Lead**: For architectural decisions
- **Product Owner**: For business decisions

### External Support

- **Supabase**: support@supabase.io
- **Railway**: https://railway.app/support
- **Telegram**: @BotSupport
- **Airwallex**: support@airwallex.com

## Updates and Maintenance

### Weekly Tasks
- Review error logs
- Check performance trends
- Update documentation

### Monthly Tasks
- Security audit
- Dependency updates
- Performance optimization
- Backup verification

### Quarterly Tasks
- Disaster recovery test
- Load testing
- Security assessment
- Documentation review

---

**Remember**: A well-monitored system is a reliable system. Stay proactive, not reactive!
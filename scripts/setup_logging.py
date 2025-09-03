#!/usr/bin/env python3
"""
Production Logging Setup for Telegram Subscription Bot
Configures structured logging, error tracking, and performance metrics
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
import traceback

# Try to import optional monitoring libraries
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    print("Warning: structlog not available. Using standard logging.")

class ProductionLogConfig:
    """Production logging configuration manager"""
    
    def __init__(self, app_name: str = "telegram_subscription_bot"):
        self.app_name = app_name
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # Log file paths
        self.app_log_file = self.log_dir / f"{app_name}.log"
        self.error_log_file = self.log_dir / f"{app_name}_errors.log"
        self.payment_log_file = self.log_dir / f"{app_name}_payments.log"
        self.audit_log_file = self.log_dir / f"{app_name}_audit.log"
        self.performance_log_file = self.log_dir / f"{app_name}_performance.log"
        
        # Alert thresholds
        self.alert_thresholds = {
            'error_rate_per_minute': 10,
            'response_time_ms': 2000,
            'database_query_ms': 500,
            'memory_usage_mb': 512,
            'cpu_usage_percent': 80
        }
    
    def setup_production_logging(self):
        """Configure production logging with all handlers"""
        
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)  # Capture all levels
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler (INFO and above)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = self._get_console_formatter()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Main application log (all levels)
        app_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10
        )
        app_handler.setLevel(logging.DEBUG)
        app_handler.setFormatter(self._get_json_formatter())
        root_logger.addHandler(app_handler)
        
        # Error log (ERROR and CRITICAL only)
        error_handler = logging.handlers.RotatingFileHandler(
            self.error_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=20  # Keep more error logs
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(self._get_detailed_formatter())
        root_logger.addHandler(error_handler)
        
        # Configure specialized loggers
        self._setup_payment_logger()
        self._setup_audit_logger()
        self._setup_performance_logger()
        
        # Configure third-party loggers
        self._configure_third_party_loggers()
        
        print(f"Production logging configured. Logs directory: {self.log_dir.absolute()}")
        
        return root_logger
    
    def _get_console_formatter(self) -> logging.Formatter:
        """Get formatter for console output"""
        return logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _get_json_formatter(self) -> logging.Formatter:
        """Get JSON formatter for structured logging"""
        if STRUCTLOG_AVAILABLE:
            return JsonFormatter()
        else:
            # Fallback to standard formatter
            return logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
            )
    
    def _get_detailed_formatter(self) -> logging.Formatter:
        """Get detailed formatter for error logs"""
        return DetailedFormatter()
    
    def _setup_payment_logger(self):
        """Setup specialized payment logger"""
        payment_logger = logging.getLogger('payments')
        payment_logger.setLevel(logging.DEBUG)
        payment_logger.propagate = False  # Don't propagate to root
        
        # Payment log handler
        payment_handler = logging.handlers.RotatingFileHandler(
            self.payment_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=30  # Keep payment logs longer
        )
        payment_handler.setFormatter(self._get_json_formatter())
        payment_logger.addHandler(payment_handler)
        
        # Also log payments to main app log
        app_handler = logging.handlers.RotatingFileHandler(
            self.app_log_file,
            maxBytes=10*1024*1024,
            backupCount=10
        )
        app_handler.setFormatter(self._get_json_formatter())
        payment_logger.addHandler(app_handler)
    
    def _setup_audit_logger(self):
        """Setup audit logger for security events"""
        audit_logger = logging.getLogger('audit')
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
        
        # Audit log handler (never rotate, append only)
        audit_handler = logging.FileHandler(self.audit_log_file)
        audit_handler.setFormatter(AuditFormatter())
        audit_logger.addHandler(audit_handler)
    
    def _setup_performance_logger(self):
        """Setup performance metrics logger"""
        perf_logger = logging.getLogger('performance')
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False
        
        # Performance log handler
        perf_handler = logging.handlers.RotatingFileHandler(
            self.performance_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=7  # Keep a week of performance logs
        )
        perf_handler.setFormatter(self._get_json_formatter())
        perf_logger.addHandler(perf_handler)
    
    def _configure_third_party_loggers(self):
        """Configure logging levels for third-party libraries"""
        # Reduce noise from chatty libraries
        logging.getLogger('aiogram').setLevel(logging.WARNING)
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        
        # Keep important ones at INFO
        logging.getLogger('supabase').setLevel(logging.INFO)
        logging.getLogger('database').setLevel(logging.INFO)
        logging.getLogger('services').setLevel(logging.INFO)
        logging.getLogger('handlers').setLevel(logging.INFO)

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process_id': os.getpid(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                          'levelname', 'levelno', 'lineno', 'module', 'msecs',
                          'pathname', 'process', 'processName', 'relativeCreated',
                          'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info']:
                log_obj[key] = value
        
        return json.dumps(log_obj)

class DetailedFormatter(logging.Formatter):
    """Detailed formatter for error logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Base format
        result = super().format(record)
        
        # Add detailed context
        details = []
        details.append(f"Timestamp: {datetime.utcnow().isoformat()}")
        details.append(f"Logger: {record.name}")
        details.append(f"Module: {record.module}")
        details.append(f"Function: {record.funcName}")
        details.append(f"Line: {record.lineno}")
        details.append(f"Process ID: {os.getpid()}")
        
        # Add exception details
        if record.exc_info:
            details.append("\nException Details:")
            details.append(f"Type: {record.exc_info[0].__name__}")
            details.append(f"Message: {str(record.exc_info[1])}")
            details.append("Traceback:")
            details.extend(traceback.format_exception(*record.exc_info))
        
        # Add message
        details.append(f"\nMessage: {record.getMessage()}")
        
        return "\n".join(details) + "\n" + "="*60 + "\n"

class AuditFormatter(logging.Formatter):
    """Special formatter for audit logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': getattr(record, 'event_type', 'UNKNOWN'),
            'user_id': getattr(record, 'user_id', None),
            'admin_id': getattr(record, 'admin_id', None),
            'action': record.getMessage(),
            'ip_address': getattr(record, 'ip_address', None),
            'user_agent': getattr(record, 'user_agent', None),
            'result': getattr(record, 'result', 'SUCCESS'),
            'metadata': getattr(record, 'metadata', {})
        }
        return json.dumps(audit_entry)

class ErrorTracker:
    """Track and analyze errors for alerting"""
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.error_counts = {}
        self.error_times = []
        
    def track_error(self, error_type: str, error_message: str):
        """Track an error occurrence"""
        current_time = datetime.utcnow()
        
        # Clean old entries
        cutoff_time = current_time.timestamp() - self.window_seconds
        self.error_times = [t for t in self.error_times if t > cutoff_time]
        
        # Track new error
        self.error_times.append(current_time.timestamp())
        error_key = f"{error_type}:{error_message[:50]}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        return len(self.error_times)  # Return error rate
    
    def get_error_rate(self) -> float:
        """Get current error rate per minute"""
        current_time = datetime.utcnow().timestamp()
        cutoff_time = current_time - 60
        recent_errors = [t for t in self.error_times if t > cutoff_time]
        return len(recent_errors)
    
    def get_top_errors(self, limit: int = 5) -> list:
        """Get most common errors"""
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_errors[:limit]

class PerformanceMonitor:
    """Monitor performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger('performance')
    
    def record_metric(self, metric_name: str, value: float, unit: str = "ms"):
        """Record a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        
        self.metrics[metric_name].append({
            'value': value,
            'unit': unit,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only last 1000 entries per metric
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name] = self.metrics[metric_name][-1000:]
        
        # Log the metric
        self.logger.info(f"Performance metric", extra={
            'metric_name': metric_name,
            'value': value,
            'unit': unit
        })
    
    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for a metric"""
        if metric_name not in self.metrics or not self.metrics[metric_name]:
            return {}
        
        values = [m['value'] for m in self.metrics[metric_name]]
        return {
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'count': len(values),
            'latest': values[-1]
        }

# Singleton instances
error_tracker = ErrorTracker()
performance_monitor = PerformanceMonitor()

def log_payment_event(user_id: int, amount: float, currency: str, 
                      status: str, payment_method: str, metadata: Dict = None):
    """Log payment-related events"""
    payment_logger = logging.getLogger('payments')
    payment_logger.info("Payment event", extra={
        'user_id': user_id,
        'amount': amount,
        'currency': currency,
        'status': status,
        'payment_method': payment_method,
        'metadata': metadata or {}
    })

def log_audit_event(event_type: str, user_id: Optional[int] = None,
                   admin_id: Optional[int] = None, action: str = "",
                   result: str = "SUCCESS", metadata: Dict = None):
    """Log audit events for security tracking"""
    audit_logger = logging.getLogger('audit')
    audit_logger.info(action, extra={
        'event_type': event_type,
        'user_id': user_id,
        'admin_id': admin_id,
        'result': result,
        'metadata': metadata or {}
    })

def log_performance_metric(metric_name: str, value: float, unit: str = "ms"):
    """Log performance metrics"""
    performance_monitor.record_metric(metric_name, value, unit)

def configure_logging_for_railway():
    """Special configuration for Railway deployment"""
    # Railway uses stdout for logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Single stdout handler with JSON formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)
    
    # Configure third-party loggers
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    return root_logger

def main():
    """Setup logging configuration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup production logging')
    parser.add_argument('--environment', choices=['local', 'railway', 'production'],
                       default='local', help='Deployment environment')
    parser.add_argument('--test', action='store_true', help='Test logging configuration')
    
    args = parser.parse_args()
    
    if args.environment == 'railway':
        logger = configure_logging_for_railway()
        print("Configured logging for Railway deployment")
    else:
        config = ProductionLogConfig()
        logger = config.setup_production_logging()
        print(f"Configured logging for {args.environment} environment")
    
    if args.test:
        # Test different log levels
        logger.debug("Debug message - detailed information")
        logger.info("Info message - general information")
        logger.warning("Warning message - something to pay attention to")
        
        # Test error with traceback
        try:
            raise ValueError("Test error for logging")
        except ValueError as e:
            logger.error("Error message with traceback", exc_info=True)
        
        # Test payment logging
        log_payment_event(
            user_id=123456,
            amount=50.0,
            currency="STARS",
            status="completed",
            payment_method="telegram_stars",
            metadata={'plan': 'basic', 'duration_days': 7}
        )
        
        # Test audit logging
        log_audit_event(
            event_type="ADMIN_ACTION",
            admin_id=306145881,
            action="Extended user subscription",
            result="SUCCESS",
            metadata={'user_id': 123456, 'days_added': 30}
        )
        
        # Test performance logging
        log_performance_metric("api_response_time", 125.5, "ms")
        log_performance_metric("database_query", 45.2, "ms")
        
        print("\nLogging test complete. Check log files in 'logs/' directory")
        
        # Show current metrics
        print("\nPerformance metrics:")
        for metric in ['api_response_time', 'database_query']:
            stats = performance_monitor.get_metric_stats(metric)
            if stats:
                print(f"  {metric}: {stats}")

if __name__ == "__main__":
    main()